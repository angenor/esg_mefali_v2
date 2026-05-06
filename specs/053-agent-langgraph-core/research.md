# Phase 0 — Research : F53 Agent LangGraph Core

**Branch** : `053-agent-langgraph-core`
**Date** : 2026-05-06

Toutes les ambiguïtés du spec ont été résolues lors du `/speckit-clarify` (cf. section Clarifications de [spec.md](./spec.md) et [.cc-runtime/logs/clarify-53.log](../../.cc-runtime/logs/clarify-53.log)). Cette recherche documente les choix techniques précis (versions de pin, patterns idiomatic, intégration avec l'existant).

## Décisions clés

### D1 — Versions de pin LangGraph stack

**Decision** : pin strict aux versions ci-dessous dans `backend/pyproject.toml` :

```toml
langgraph = "^0.2.74"            # API astream_events(version='v2') stable
langchain-core = "^0.3.21"        # required by langgraph 0.2.x
langchain-openai = "^0.2.14"      # ChatOpenAI streaming, tools, async
langgraph-checkpoint-postgres = "^2.0.10"  # PostgresSaver async + setup()
```

**Rationale** :

- `astream_events(version='v2')` est officiellement marqué stable depuis langgraph 0.2.50+. La pin sur 0.2.74 garantit le support des features critiques.
- `langchain-core 0.3.x` est la branche compatible avec `langgraph 0.2.x` ; éviter le saut vers 0.4.x qui introduit des breaking changes message format.
- `langchain-openai 0.2.x` exposes `ChatOpenAI` qui supporte `LLM_BASE_URL` (OpenRouter, Together, etc.) et `tool_choice = "auto" | "any" | {"type": "function", "function": {"name": "..."}}` (forçage tool).
- `langgraph-checkpoint-postgres 2.0.x` est la lib officielle pour le `PostgresSaver` async (`AsyncPostgresSaver`) avec `.setup()` qui crée les tables LangGraph nécessaires automatiquement (cohabitation avec Alembic confirmée par la doc officielle).

**Alternatives considered** :

- `langchain` (full meta-package) — rejeté : trop large, on ne veut que `langchain-core` + `langchain-openai`.
- `langgraph 0.3+` — rejeté : pas encore en GA, breaking changes en cours.
- `RedisSaver` ou `MemorySaver` (à la place de `PostgresSaver`) — rejetés : la stack MVP impose Postgres comme seul service stateful (pas de Redis avant Phase post-MVP).

### D2 — Pattern LangGraph idiomatic pour ce graph

**Decision** : utiliser `StateGraph[AgentState]` typé Pydantic v2 (`TypedDict` rejeté car notre AgentState est complexe et bénéficie de la validation runtime). Les nœuds retournent un `dict[str, Any]` (patch d'état) que LangGraph fusionne via `add_messages` (pour `messages: list[BaseMessage]`) et clobber simple pour les autres champs.

**Rationale** :

- `Pydantic` AgentState assure `extra='forbid'` et la validation au runtime — aligné avec invariant P9.
- `add_messages` est le reducer idiomatic de LangGraph pour empiler les messages sans écraser. Pour les autres champs (intent, tool_calls, retry_count), un set simple suffit.
- Les nœuds restent **purs** au sens fonctionnel : ils prennent l'état complet en lecture, retournent un patch en écriture, sans side-effect en dehors de `dispatch_tool` (qui est nominal pour cette catégorie).
- `astream_events(version='v2')` permet d'observer chaque transition de nœud + les chunks LLM intermédiaires.

**Alternatives considered** :

- `TypedDict` AgentState — rejeté : pas de validation runtime, contradiction avec invariant P9 strict mode.
- `MessageGraph` (sub-class de StateGraph spécifique aux conversations) — rejeté : trop limitatif, on a besoin de fields hors `messages` (intent, dispatch_results, retry_count, tracing).
- Sub-graphs par skill — out of scope MVP (cf. spec).

### D3 — Schéma SQL `agent_run` et `agent_run_step`

**Decision** : tables RLS-protégées, append-only, indexées par `account_id+thread_id+started_at` pour le debug rapide.

```sql
CREATE TYPE agent_run_status AS ENUM ('ok', 'error', 'timeout', 'cancelled');
CREATE TYPE agent_step_status AS ENUM ('ok', 'error', 'timeout', 'cancelled', 'skipped');

CREATE TABLE agent_run (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL REFERENCES accounts(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    thread_id       VARCHAR(128) NOT NULL,            -- composite "{account_id}:{conv_uuid}"
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ NULL,
    status          agent_run_status NOT NULL DEFAULT 'ok',
    total_latency_ms INT NULL,
    total_tokens_in  INT NULL,
    total_tokens_out INT NULL,
    retry_count     INT NOT NULL DEFAULT 0,
    final_node      VARCHAR(64) NULL,
    error_summary   TEXT NULL,
    -- pas de updated_at : append-only
    CONSTRAINT agent_run_thread_id_format
        CHECK (thread_id ~ '^[0-9a-f-]{36}:[0-9a-f-]{36}$')
);
CREATE INDEX idx_agent_run_account_thread ON agent_run(account_id, thread_id, started_at DESC);
CREATE INDEX idx_agent_run_status_started ON agent_run(status, started_at DESC) WHERE status != 'ok';

CREATE TABLE agent_run_step (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES agent_run(id) ON DELETE RESTRICT,
    account_id      UUID NOT NULL REFERENCES accounts(id),  -- duplique le account_id du run pour RLS
    node_name       VARCHAR(64) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms      INT NULL,
    tokens_in       INT NULL,
    tokens_out      INT NULL,
    tool_calls_count INT NOT NULL DEFAULT 0,
    status          agent_step_status NOT NULL DEFAULT 'ok',
    error           TEXT NULL
);
CREATE INDEX idx_agent_run_step_run ON agent_run_step(run_id, started_at);
CREATE INDEX idx_agent_run_step_account_node ON agent_run_step(account_id, node_name, started_at DESC);

-- RLS policies
ALTER TABLE agent_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_run_step ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_run_account_isolation ON agent_run
    USING (account_id = current_setting('app.current_account_id')::uuid);
CREATE POLICY agent_run_step_account_isolation ON agent_run_step
    USING (account_id = current_setting('app.current_account_id')::uuid);

-- Append-only (revoke UPDATE/DELETE pour applicative role)
REVOKE UPDATE, DELETE ON agent_run FROM app_user;
REVOKE UPDATE, DELETE ON agent_run_step FROM app_user;
```

**Rationale** :

- `account_id` dupliqué sur `agent_run_step` pour permettre RLS direct sans join.
- Index ciblés debug : par account/thread (timeline), par status (alerting), par node (perf node-by-node).
- Append-only via `REVOKE UPDATE, DELETE` — invariant P3.
- Format `thread_id` enforced via CHECK constraint pour garantir la structure composite (Q2 clarification).
- ENUMs type-safe (pas d'oubli de valeurs).

**Alternatives considered** :

- Une seule table avec `parent_run_id NULL pour les runs et NOT NULL pour les steps` — rejeté : viole 3NF, complique la requête.
- JSONB pour les métriques — rejeté : moins indexable, plus difficile pour aggregations SQL.

### D4 — Format SSE events (compat F13 + extension F55)

**Decision** : étendre le protocole SSE existant de F13 sans casser la compat. Format event line : `event: <type>\ndata: <json>\n\n`.

| Event type | Quand | Payload |
|------------|-------|---------|
| `token` | F13 existant — chaque chunk de texte LLM | `{"text": "..."}` |
| `tool_invoke` | F53 nouveau — un tool `ask_*`/`show_*` à executer côté front | `{"tool_name": "ask_qcu", "tool_call_id": "...", "arguments": {...}}` |
| `mutation` | F53 nouveau — une mutation DB a réussi | `{"entity": "projet", "action": "create", "id": "...", "snapshot": {...}}` |
| `validation_retry` | F53 nouveau — retry pédagogique pour debug | `{"retry_count": 1, "tool_name": "...", "error_summary": "..."}` |
| `error` | F13 existant + extension F53 | `{"code": "validation_failed_after_retries", "message": "..."}` |
| `done` | F13 existant — fin du tour | `{"final_text": "...", "agent_run_id": "..."}` |

**Rationale** :

- Le frontend F41 consomme déjà `token`, `error`, `done`. Les 3 nouveaux events (`tool_invoke`, `mutation`, `validation_retry`) sont additifs : un client F41 pré-F55 les ignorera silencieusement (forward compat).
- F55 finira la cohérence et ajoutera le mapping vers les composants UI (bottom sheet, viz, audit panel).
- Le payload `done` inclut maintenant `agent_run_id` pour permettre au front de réclamer la trace en cas de debug.

**Alternatives considered** :

- WebSocket (au lieu de SSE) — rejeté : SSE déjà en place côté F13, pas de besoin bidirectionnel pour ce flow.
- gRPC streaming — rejeté : trop lourd, pas de besoin polyglotte.

### D5 — Stratégie de mock LLM pour les tests

**Decision** : créer une fixture `fakellm` (dans `backend/tests/conftest.py`) qui retourne une `BaseLanguageModel` mockée capable de :

1. Retourner une séquence prédéfinie de `AIMessageChunk` (texte) ou `AIMessage` avec `tool_calls`.
2. Configurable par test : « réponse 1 = tool call X invalide, réponse 2 = tool call X valide, réponse 3 = texte final ».
3. Supporter `astream_events(version='v2')` (yield des events conformes).
4. Compter le nombre d'appels (utile pour valider les retries).

**Rationale** :

- Tests reproductibles (NFR-002 idempotence).
- Pas d'appel réseau dans les tests CI.
- Permet de tester précisément les chemins retry / fallback / dispatch.

**Alternatives considered** :

- VCR cassettes (record/replay HTTP) — rejeté : fragile, dépend du modèle distant, casse à chaque update API.
- LM Studio local — rejeté : non-déterministe, lourd pour CI.

### D6 — Rollback raw mode : implémentation

**Decision** : dans `chat/api.py:post_message`, le branchement est :

```python
async def post_message(...):
    if settings.LLM_AGENT_MODE == "langgraph":
        return StreamingResponse(
            run_agent(user_message=..., thread_id=..., account_id=..., user_id=..., context_json=...),
            media_type="text/event-stream",
        )
    else:  # raw
        return StreamingResponse(stream_assistant(...), media_type="text/event-stream")
```

`stream_assistant()` (F13) reste **strictement inchangé** — F53 ne touche pas son code. Le bascule est donc instantané (pas de redémarrage, juste env var au prochain tour).

**Rationale** :

- Rollback opérationnel zéro-downtime.
- Tests CI peuvent exécuter les deux modes (cf. SC-008).
- Aucune dette ajoutée à `llm_stream.py`.

**Alternatives considered** :

- Suppression directe de `stream_assistant` — rejeté : pas de rollback possible si bug en prod.
- Feature flag dynamique (DB) — out of scope MVP.

### D7 — Boot startup hook

**Decision** : dans `backend/app/main.py`, ajouter au lifespan FastAPI :

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing setup ...
    if settings.LLM_AGENT_MODE == "langgraph":
        from app.agent import compile_agent_graph
        app.state.agent_graph = await compile_agent_graph()
        # Sets up langgraph_* tables via PostgresSaver.setup()
    yield
    # cleanup
```

Le `compile_agent_graph()` :
1. Initialise le `AsyncPostgresSaver` avec `DB_URL`.
2. Appelle `await checkpointer.setup()` (idempotent).
3. Construit le `StateGraph[AgentState]`, attache les nœuds, compile.
4. Retourne `CompiledGraph`.

Si la compile échoue, le backend refuse de démarrer (`fail-fast`).

**Rationale** :

- Compile une seule fois (NFR-001 latence < 500 ms en runtime, le compile coûteux ne se fait qu'au boot).
- `setup()` LangGraph est idempotent → safe redémarrage.
- Fail-fast garantit que `/health/agent` ne retournera jamais un faux positif.

**Alternatives considered** :

- Lazy compile au premier message — rejeté : 1ère requête trop lente, race condition concurrente possible.
- Build pré-compilé sur disque — rejeté : pas de bénéfice (le compile prend < 2 s).

### D8 — Annulation propre

**Decision** : utiliser `asyncio.CancelledError` natif. Le runner enveloppe l'`astream_events` dans `try/except asyncio.CancelledError` :

```python
async def run_agent(...) -> AsyncIterator[SseEvent]:
    run_id = await tracing.start_run(...)
    try:
        async for event in graph.astream_events(...):
            yield map_to_sse(event)
    except asyncio.CancelledError:
        await tracing.mark_run_cancelled(run_id)
        # rollback in-flight tx (déjà géré par session.rollback() côté DB)
        # ne pas persister de message assistant tronqué
        raise
    else:
        await tracing.complete_run(run_id, status='ok')
```

**Rationale** :

- Cohérent avec FastAPI `StreamingResponse` (qui propage la cancellation client → asyncio).
- Pas besoin de polling explicit du `request.is_disconnected()`.
- `asyncio.shield()` n'est PAS utilisé ici — on veut justement la propagation.

**Alternatives considered** :

- Polling `request.is_disconnected()` — rejeté : moins fiable, complique le code.
- Timeout côté server uniquement (pas de cancellation) — rejeté : viole SC-007.

### D9 — Concurrence sur même thread

**Decision** : `pg_advisory_xact_lock(hashtext(thread_id))` au début de `run_agent`. Si la lock est déjà tenue par une autre transaction du même thread, soit on attend (configurable, par défaut 5s) soit on retourne 409 Conflict.

```python
async def run_agent(...):
    async with db.session() as session:
        # Acquire advisory lock (transaction-scoped, libéré au commit/rollback)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:thread_id))"),
            {"thread_id": thread_id},
        )
        # ... rest of agent run
```

**Rationale** :

- Postgres-natif, pas de dépendance externe.
- Transaction-scoped → libération automatique sur commit/rollback.
- `hashtext` map string → bigint (signature du lock).
- Pas besoin de table de lock applicative.

**Alternatives considered** :

- Optimistic concurrency (version_at_start dans state) — rejeté : plus complexe, gère mal le cas double-clic immédiat.
- Redis Redlock — rejeté : pas de Redis MVP.
- In-memory `asyncio.Lock` per `thread_id` — rejeté : ne marche pas en multi-worker uvicorn.

### D10 — Stratégie d'observabilité du graph

**Decision** : 3 couches d'observabilité :

1. **DB tracing** (FR-011) : `agent_run` + `agent_run_step` rows (default `LLM_AGENT_TRACE=db`).
2. **Stdout structured logs** (option `LLM_AGENT_TRACE=db+stdout`) : log JSON par event LangGraph.
3. **Off** (option `LLM_AGENT_TRACE=off`) : pas de tracing — réservé aux tests perf.

Chaque nœud du graph est wrappé par un décorateur `@traced_node` qui mesure la latence et écrit le `agent_run_step` row au sortir.

**Rationale** :

- DB tracing par défaut couvre 90 % du debug ops.
- Stdout en option pour logs centralisés (Datadog, Loki, etc. en prod).
- Off pour les benchmarks NFR-001.

**Alternatives considered** :

- LangSmith intégration — rejeté : SaaS US, viole hosting EU/UEMOA.
- OpenTelemetry — différé post-MVP (F60 le finalisera).

## Récap : 0 NEEDS CLARIFICATION restant

Toutes les décisions techniques sont arrêtées. Le plan peut passer à Phase 1 (data-model + contracts).
