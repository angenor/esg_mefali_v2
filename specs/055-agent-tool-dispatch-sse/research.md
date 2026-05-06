# Phase 0 — Research: Agent Tool Dispatch & SSE Bridge

Date: 2026-05-06

Cette feature (F55) intervient après F53 (LangGraph core mergée) et en // de F54 (context builder, sourcing). Aucun NEEDS CLARIFICATION résiduel — les 5 questions ouvertes ont été tranchées en `## Clarifications` du `spec.md`. Cette section recense les **décisions techniques** prises pour les composants à livrer.

## Décisions techniques

### D1 — Architecture du dispatcher central

**Decision** : Module `app/agent/dispatcher.py` exposant `async def dispatch(call, state, db, *, mutation_ctx, dry_run, hooks) -> ToolDispatchResult`. Switch par `ToolCategory` (ASK/SHOW → frontend_event ; MUTATION → handler exec + audit + EventBus ; READ → handler exec + serialized result). Le dispatcher est idempotent (lookup `tool_call_log` par `idempotency_key`) et fail-safe (refuse si rate-limit store inaccessible).

**Rationale** :
- Centralisation = un seul point d'audit, de rate limit et d'idempotence (P3 + sécurité).
- La dépendance `MutationCtx` immuable (frozen dataclass Python) garantit thread-safety asyncio (NFR-004).
- Hooks pre/post via décorateurs `@before_dispatch` et `@after_dispatch` (best-effort, exceptions absorbées).

**Alternatives considered** :
- Dispatcher distribué par catégorie (3 modules) : plus de surface d'API, moins de cohérence. Rejeté.
- Dispatcher en method d'`AgentState` : impossible (state Pydantic immuable côté LangGraph).

### D2 — `ToolDispatchResult` : variante union vs champs optionnels

**Decision** : Pydantic `BaseModel` avec `kind: Literal["frontend_event","mutation_result","tool_message","error"]` + champs optionnels conditionnés par `kind`. Validation cohérence via `model_validator`. `model_config = ConfigDict(extra='forbid')`.

**Rationale** :
- Compatible avec le squelette F53 existant (`ToolDispatchResult` enum-driven).
- `extra='forbid'` (P9) garantit que les champs LLM hallucinés sont rejetés.
- Sérialisation JSON simple pour SSE.

**Alternatives** :
- Discriminated union Pydantic v2 (`Discriminator`) : plus verbose à étendre, choix similaire.

### D3 — Rate limit : interface pluggable

**Decision** : Interface `RateLimitStore(Protocol)` avec `async def check_and_increment(account_id, tool_name, limit_per_minute) -> RateLimitDecision`. Deux implémentations :
- `InMemoryRateLimitStore` (dict + asyncio Lock + bounded LRU 1000 keys, fenêtre glissante 60 s).
- `RedisRateLimitStore` (INCR + EXPIRE atomique via Lua script).

Sélection au boot par `LLM_AGENT_RATE_LIMIT_BACKEND=memory|redis` (défaut `memory`). Limites configurables via env JSON `LLM_AGENT_RATE_LIMITS={"update_*":30,"create_*":10,"delete_*":5,"generate_*":5}`.

**Rationale** :
- Pas de Redis en dev (Postgres seul service Docker — cf. CLAUDE.md).
- Fail-safe NFR-007 : try/except qui retourne `RateLimitDecision(allowed=False, reason='store_unavailable')` plutôt que de laisser passer.
- Multi-worker prod : Redis avec script atomique évite les races.

**Alternatives** :
- Postgres advisory lock + table : trop lent pour 30 ops/sec/account.
- SlowAPI middleware FastAPI : ne couvre pas le scope per-tool intra-agent.

### D4 — Idempotence : lookup en DB

**Decision** : Lors du dispatch, calculer `idempotency_key = sha256(f"{account_id}:{agent_run_id}:{call_id}").hexdigest()[:32]`. Avant exécution :
1. SELECT FOR SHARE sur `tool_call_log WHERE account_id=? AND idempotency_key=?`.
2. Si trouvé → retourner `ToolDispatchResult` reconstitué depuis le row précédent (champs `dispatch_result_kind`, `output_payload`).
3. Sinon → INSERT row `pending` puis exécuter handler et UPDATE `status='ok'|'error'` à la fin.

Contrainte UNIQUE per `(account_id, idempotency_key)` (cf. clarification Q1).

**Rationale** :
- DB est déjà la source de vérité (Postgres + RLS) — pas besoin de Redis.
- SELECT FOR SHARE évite la double exécution concurrente (worst case : 1 SQL en plus).
- Hash 32 chars suffit pour ~1B tool calls par tenant sans collision (espace 2^128 → 2^64 birthday).

**Alternatives** :
- UUID v4 du frontend comme idempotency_key : cassé si reconnexion SSE génère un nouvel UUID.
- Cache Redis : redondant avec la DB.

### D5 — Confirmation flow : `agent_run.metadata` JSON

**Decision** : Pour les tools `requires_confirmation=True`, le dispatcher :
1. NE call PAS le handler.
2. Stocke un JSON `{tool_call_id, tool_name, arguments, expires_at: now + 180 s}` dans `agent_run.metadata['pending_confirmations'][call_id]`.
3. Retourne un `ToolDispatchResult(kind='frontend_event')` mappé à un faux tool ASK `ask_yes_no` côté frontend (avec les arguments du tool original encodés).
4. Au tour suivant, si la réponse user est interprétée comme « Oui » et que le `pending_confirmation` n'a pas expiré, le runner re-soumet le call original au dispatcher (qui cette fois bypass la confirmation).
5. Si « Non » ou expiré → `tool_call_log.status='cancelled_by_user'` ou `'confirmation_expired'`.

**Rationale** :
- Pas de table dédiée (cf. clarification Q3). Migration unique pour audit/tool_call_log.
- TTL applicatif 180 s vérifié par le dispatcher au début du tour suivant.

**Alternatives** :
- Table `agent_pending_confirmation` : alourdit le schéma sans gain.
- Redis : réintroduit une dépendance non-essentielle dev.

### D6 — SSE protocole : format & framing

**Decision** : Module `app/agent/sse.py` exposant :
```python
def format_event(event_type: str, data: dict, *, id: int | None = None, dry_run: bool = False) -> str
```
qui retourne une string `event: {type}\ndata: {json}\n\n` (avec préfixe `dry_run:` au type si flag activé). Le runner consomme `astream_events(version='v2')` et yield les frames.

**Rationale** :
- Format SSE standard (compatible EventSource navigateur).
- `id` optionnel pour la résilience reconnect (Last-Event-ID header).
- Préfixe `dry_run:` simple au lieu d'un champ `data.dry_run` pour permettre au frontend de filtrer même sans parser.

**Alternatives** :
- WebSocket : surface plus large à sécuriser, pas nécessaire pour streaming descendant.
- Server-Sent Events via httpx-sse côté frontend : Nuxt 4 + `EventSource` natif suffit.

### D7 — `MutationCtx` immuable

**Decision** : `frozen=True` dataclass Python avec champs `account_id, user_id, db, audit_logger, event_bus_publisher, tool_call_log_id, agent_run_id, dry_run`. Pas de modification après instanciation. Un `MutationCtx` par tool call (jamais partagé entre calls concurrents NFR-004).

**Rationale** :
- Cohérent invariant immuabilité (rules common/coding-style.md).
- Audit logger et event bus publisher sont des callables, pas des classes mutables.

**Alternatives** :
- Pydantic BaseModel : pas nécessaire (pas de validation runtime utile pour un objet interne).

### D8 — Audit log automatique : transaction unifiée

**Decision** : Le décorateur `@mutation_handler` enveloppe le handler dans une transaction unique :
```python
async with db.begin():
    SET LOCAL "app.current_account_id" = ?
    result = await handler(args, ctx)
    audit_logger.append_many(diffs, source='llm', tool_call_id=ctx.tool_call_log_id, agent_run_id=ctx.agent_run_id)
```
En dry_run : la transaction est rollback-only (`db.begin_nested()` puis ROLLBACK forcé), aucune ligne n'est commit.

**Rationale** :
- Une seule transaction = atomicité garantie (FR-009 + edge case "audit ↔ DB"). Si `audit_logger.append_many` échoue, le UPDATE business rollback aussi.
- `SET LOCAL` reset à la fin de la transaction (pas de leak du GUC).

**Alternatives** :
- Audit en background (queue) : viole P3 (audit synchrone obligatoire) et risque la désynchronisation.

### D9 — Migration Alembic

**Decision** : Une seule migration `XXXX_f55_audit_tool_call_extensions.py` qui :
1. ALTER TABLE `audit_log` ADD COLUMN `tool_call_id UUID NULL REFERENCES tool_call_log(id)`.
2. ALTER TABLE `audit_log` ADD COLUMN `agent_run_id UUID NULL REFERENCES agent_run(id)`.
3. ALTER TABLE `tool_call_log` ADD COLUMN `idempotency_key TEXT NULL`.
4. ALTER TABLE `tool_call_log` ADD COLUMN `agent_run_id UUID NULL REFERENCES agent_run(id)`.
5. ALTER TABLE `tool_call_log` ADD COLUMN `dispatch_result_kind TEXT NULL` (CHECK IN frontend_event|mutation_result|tool_message|error).
6. CREATE UNIQUE INDEX `idx_tool_call_log_account_idempotency ON tool_call_log(account_id, idempotency_key) WHERE idempotency_key IS NOT NULL`.
7. INDEX `idx_audit_log_tool_call_id ON audit_log(tool_call_id)`.

**Rationale** :
- Toutes les colonnes sont NULLABLE : zéro impact sur le code existant.
- L'index UNIQUE partial filtre les anciennes lignes sans clé.
- `agent_run` table existe déjà (créée par F53).

**Alternatives** :
- Deux migrations séparées : OK pour rollback granulaire, mais +1 churn ; rejeté.

### D10 — Frontend : composable `useChatToolBridge`

**Decision** : Nouveau composable Nuxt qui consomme les events SSE poussés par `useChatStream` et route :
- `tool_invoke` avec `tool_name` matchant `ask_*` → `useChatBottomSheet().open(tool_name, payload)` (F39).
- `tool_invoke` avec `tool_name` matchant `show_*` → emit dans le store `chat.pendingViz[message_id].push({tool_call_id, payload})` pour rendu inline dans `MessageBubble.vue` (F40 `<VizRenderer>`).
- `mutation` → `useChatEventBus().emit('entity_updated', {entity_type, entity_id, fields_updated})`.
- `tool_call_completed` → admin only, log au store debug.
- `error` → bulle d'erreur F41.
- `message_done` → finalisation message + reset pending.

**Rationale** :
- Sépare la logique de routage SSE de la logique d'affichage (testabilité).
- `useChatEventBus` existe déjà côté F41.
- Le bandeau dry_run vit dans `DryRunBanner.vue`, isolé du composable.

**Alternatives** :
- Tout intégrer dans `useChatStream` : le composable atteint > 400 lignes, trop large (rules/common/coding-style.md).

### D11 — Tests E2E : pytest+httpx + Playwright

**Decision** :
- **Backend** : pytest+httpx ASGI (cohérent F53). Mocker LLM via `fakellm` fixture (renvoie un tool_call déterministe puis un texte). Couvrir les 9 scenarios d'intégration listés dans `plan.md` (Project Structure → tests/integration).
- **Frontend** : Playwright. 2 specs critiques :
  - `chat-bottom-sheet.spec.ts` — envoyer un message, vérifier l'ouverture de la bottom sheet `ask_qcu`, valider, vérifier le retour au tour suivant.
  - `chat-mutation-sync.spec.ts` — déclencher `update_company_profile` via le chat, vérifier que la page `/profile/entreprise` ouverte dans un autre tab se met à jour sans rechargement.

**Rationale** :
- Mix pytest E2E backend + Playwright UI = couverture rapide et reproductible.
- Fakellm fixture évite les dépendances réseau LLM en CI (clarification F53 reused).

**Alternatives** :
- Vitest jsdom pour les composants : OK pour unit, mais ne valide pas la chaîne SSE.
- Cypress : Nuxt 4 + Playwright étant déjà intégré (cf. F41), pas de motif pour switcher.

### D12 — Hard cap 10 tool calls par tour

**Decision** : Compteur `state.tool_calls_count_in_turn` incrémenté à chaque dispatch. Si > 10, le runner force `compose_response` (état `next_node = 'compose_response'`). Le frontend reçoit un SSE `text_delta` avec le fallback puis `message_done`.

**Rationale** :
- Empêche les boucles READ infinies (edge case "READ infinite loop" + risque coût LLM).
- Cap éprouvé en pratique pour l'orchestration LLM tool-use.

**Alternatives** :
- Cap dynamique (basé sur le rate limit) : trop complexe, sources de bug.

### D13 — Ré-injection des résultats READ : budget tokens

**Decision** : Module `app/agent/read_serializer.py` (ou dans dispatcher.py si court) avec :
```python
def serialize_read_result(payload: dict, *, budget_tokens: int = 1500) -> str:
```
Tronque le payload (top-N items) à un budget tokens configurable via `LLM_AGENT_READ_BUDGET_TOKENS=1500` (défaut). JSON structuré pour parsabilité LLM.

**Rationale** :
- Cf. clarification Q4 — protège le contexte LLM et les coûts.
- 1500 tokens ≈ 3 messages historiques avec metadata, suffisant pour `recall_history`.

**Alternatives** :
- Pas de troncature : viole NFR perf et budget tokens implicite.

## Synthèse

Toutes les unknowns du spec sont résolues. Aucun NEEDS CLARIFICATION résiduel. Les 13 décisions ci-dessus pilotent Phase 1 (data-model.md, contracts/, quickstart.md).
