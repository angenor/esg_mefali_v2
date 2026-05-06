# F53 — Agent LangGraph Core (orchestration backend câblée)

**Phase** : H — Agent Hardening
**Modules brainstorm** : 1.0–1.4 (Agent conversationnel principal), 10.1–10.5 (Tool-use fiable), 11.1 (Skills engine)
**Dépendances** : F13 (chat backend), F14 (LangGraph routing & validation), F18 (memory), F19 (skills loader), F21 (skills MVP)
**Estimation** : 4 jours

## Contexte et objectif

Un audit du code F13 a révélé que `backend/app/chat/llm_stream.py` ne fait qu'un **proxy LLM brut** :

```python
client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=[{"role": "user", "content": user_content}],
    stream=True,
)
```

Aucun `tools=[...]`, aucun system prompt, aucun contexte, aucun historique. Conséquence directe :
- Les tools de `app/orchestrator/tools/*` sont **construits mais jamais offerts au LLM**.
- Le pipeline F14 (classifier → selector → validator → retry) est **isolé**.
- Le moteur de Skills F19 n'est appelé que par l'endpoint dev `/internal/skill-loader/test`.
- Aucune mutation, aucune visualisation, aucune bottom sheet ne peut être déclenchée par l'agent.

**F53 est la feature de branchement** : remplacer `stream_assistant()` par une **machine d'état LangGraph** qui orchestre tous les composants déjà livrés. Sans cette feature, F13/F14/F15/F16/F17/F18/F19/F21 restent des bibliothèques inertes.

L'agent assemblé est exposé à l'utilisateur sous le nom **ESG Mefali** (identité figée dans le system prompt par F54). Le frontend (F41) affiche déjà cette marque dans la sidebar ("Assistant IA") et dans les bulles assistant.

### Architecture livrée

```
                    ┌─────────────────────────────────────────┐
                    │       LangGraph StateGraph              │
                    │                                         │
  POST /messages → ROUTE → CONTEXT → MEMORY → SELECT → LLM   │
                    ↑                                  │      │
                    │                                  ↓      │
                    └── RETRY (max 2)  ←  VALIDATE ←──┤      │
                                                       ↓      │
                                                    DISPATCH  │
                                                       ↓      │
                                                    RESPOND   │
                                                       ↓      │
                                                      END     │
                    └─────────────────────────────────────────┘
                                       ↓
                          SSE stream → frontend F41
```

Chaque nœud du graphe est une fonction async pure prenant un `AgentState` et retournant un `AgentState` partiel. Le graphe est compilé une fois au démarrage (`compile()`), invoqué par requête (`astream()`).

## User Stories

### US1 — Définition du StateGraph (P1)

**En tant que** dev backend,
**je veux** un module `app/agent/graph.py` qui définit un `StateGraph[AgentState]` avec les nœuds `route`, `build_context`, `recall_memory`, `select_tools`, `call_llm`, `validate_payload`, `dispatch_tool`, `compose_response`,
**afin que** chaque tour de chat soit reproductible, debuggable, et testable nœud par nœud.

**AgentState (Pydantic)** :
- `thread_id: UUID`, `account_id: UUID`, `user_id: UUID`
- `user_message: str`, `context_json: ContextJson`
- `intent: Intent | None`
- `system_prompt: str`
- `messages: list[BaseMessage]` (LangChain messages, format OpenAI)
- `available_tools: list[ToolDef]`
- `llm_response: AIMessage | None`
- `tool_calls: list[ToolCall]`
- `validated_calls: list[ValidatedToolCall]`
- `dispatch_results: list[ToolDispatchResult]`
- `final_text: str`
- `retry_count: int`
- `errors: list[AgentError]`

### US2 — Nœud `route` (P1)

**En tant que** dev,
**je veux** un nœud qui appelle `app.orchestrator.intent_classifier.classify(user_message, context)` et écrit `state.intent`,
**afin de** conditionner les nœuds suivants (memory, tool selection).

Branchement conditionnel :
- `intent ∈ {profilage, mutation, analyse}` → `build_context` complet (entreprise + projets)
- `intent ∈ {aide, navigation, autre}` → `build_context` minimal
- `intent == question_fermee` → injecter forçage tool `ask_*` dans `select_tools`

### US3 — Nœud `call_llm` avec tools (P1)

**En tant que** dev,
**je veux** un nœud qui invoque le LLM via **LangChain ChatOpenAI** avec :
- `model = settings.LLM_MODEL`
- `base_url = settings.LLM_BASE_URL`
- `api_key = settings.LLM_API_KEY`
- `tools = [t.to_openai_function() for t in state.available_tools]`
- `tool_choice = "auto"` (ou forcé si `intent == question_fermee`)
- `streaming = True`,
**afin de** récupérer soit des `AIMessageChunk` (tokens texte) soit des `ToolCall`.

Le nœud émet en parallèle des **events SSE** vers le client (cf. F55) au fur et à mesure du stream LangChain (`astream_events(version='v2')`).

### US4 — Boucle Validate ↔ Retry (P1)

**En tant que** dev,
**je veux** que le nœud `validate_payload` exécute `app.orchestrator.payload_validator.validate(tool_call.name, tool_call.arguments)` pour chaque tool call,
**afin de** rejeter les hallucinations de schéma.

En cas d'erreur :
- `retry_count < 2` → repasser à `call_llm` avec un message système supplémentaire `{"role": "tool", "tool_call_id": ..., "content": "{erreur structurée}"}` et `retry_count += 1`.
- `retry_count == 2` → fallback texte ("Je n'arrive pas à formaliser cette action — peux-tu reformuler ?") + log d'incident `tool_call_log.status = 'validation_error'`.

### US5 — Nœud `dispatch_tool` (P1)

**En tant que** dev,
**je veux** un nœud qui pour chaque `ValidatedToolCall` route vers le bon dispatcher selon la catégorie du tool :
- `ask_*` / `show_*` → émettre SSE `tool_invoke` vers frontend (handled par F39/F40 bottom sheet/viz). Pas d'exécution backend.
- `update_*` / `create_*` / `delete_*` → exécuter le `handler` enregistré dans `tool_registry`, écrire en DB (RLS via `SET LOCAL app.current_account_id`), journaliser dans `audit_log`, émettre SSE `mutation`,
- `cite_source` / `search_source` / `recall_history` → exécuter, le résultat retourne au LLM dans un message `tool` puis re-call LLM (loop sur `call_llm`).

**afin de** matérialiser les actions agent dans la DB et le frontend.

### US6 — Compilation et invocation (P1)

**En tant que** dev,
**je veux** un module `app/agent/__init__.py` exposant :
- `compile_agent_graph() -> CompiledGraph` (compile une fois au boot)
- `async def run_agent(user_message, thread_id, account_id, user_id, context_json) -> AsyncIterator[SseEvent]` (orchestre via `astream_events`),
**afin que** `chat/api.py` POST `/messages` puisse l'appeler à la place du `stream_assistant()` actuel.

### US7 — Branchement effectif dans `chat/api.py` (P1)

**En tant que** dev,
**je veux** que `chat/api.py:post_message` soit modifié pour appeler `run_agent(...)` à la place de `stream_assistant()`,
**afin que** l'utilisateur final bénéficie immédiatement de l'agent complet.

L'ancien `stream_assistant()` est conservé sous flag `LLM_AGENT_MODE=raw` pour rollback rapide en cas d'incident en prod.

### US8 — Persistance de l'état du graph (P2)

**En tant que** dev,
**je veux** que LangGraph persiste l'état d'un thread via le `Checkpointer` PostgreSQL (`PostgresSaver` officiel),
**afin de** pouvoir reprendre une conversation en cours après crash et déboguer un tour précédent.

Schéma : table `agent_checkpoints` (auto-créée par LangGraph), filtrée par `thread_id`.

### US9 — Tracing et observabilité (P2)

**En tant que** dev,
**je veux** que chaque exécution du graphe émette un trace structuré incluant : `node_name`, `latency_ms`, `tokens_in/out`, `tool_calls_emitted`, `retry_count`, `final_status`,
**afin de** mesurer la santé de l'agent (alimentation de F60).

Format : table `agent_run` (un row par exécution complète) + `agent_run_step` (un row par nœud). Indexable pour debug.

### US10 — Configuration par environnement (P2)

**En tant que** ops,
**je veux** des variables d'environnement pour ajuster le comportement de l'agent sans redéploiement :
- `LLM_AGENT_MODE` ∈ {`langgraph` (défaut), `raw` (fallback)}
- `LLM_AGENT_MAX_TOOLS` (défaut 10)
- `LLM_AGENT_MAX_RETRIES` (défaut 2)
- `LLM_AGENT_TIMEOUT_S` (défaut 30)
- `LLM_AGENT_TRACE` ∈ {`off`, `db` (défaut), `db+stdout`}.

## Exigences fonctionnelles

- **FR-001** : Module `backend/app/agent/graph.py` exposant `build_graph() -> StateGraph` qui assemble les nœuds (`route`, `build_context`, `recall_memory`, `select_tools`, `call_llm`, `validate_payload`, `dispatch_tool`, `compose_response`).
- **FR-002** : Module `backend/app/agent/state.py` définissant `AgentState` (BaseModel Pydantic v2, `extra='forbid'`) et les types associés (`Intent`, `ToolCall`, `ValidatedToolCall`, `ToolDispatchResult`, `AgentError`).
- **FR-003** : Module `backend/app/agent/nodes/` un fichier par nœud, fonction async pure `async def node_xxx(state: AgentState) -> dict[str, Any]` retournant les patches d'état. Aucun side-effect en dehors du nœud `dispatch_tool`.
- **FR-004** : Adapter `backend/app/agent/llm_factory.py` qui retourne un `ChatOpenAI` LangChain configuré avec `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`. Ne hard-coder aucun endpoint.
- **FR-005** : Adapter `backend/app/agent/tool_factory.py` qui convertit chaque `ToolDef` du registry en `langchain_core.tools.StructuredTool` (description = use_when + dont_use_when, args_schema = Pydantic schema).
- **FR-006** : Module `backend/app/agent/runner.py` exposant `async def run_agent(...) -> AsyncIterator[SseEvent]` qui consomme `graph.astream_events(version='v2')`, mappe les events LangChain vers les events SSE du protocole F13/F55, et persiste les `AIMessage` finaux via `service.persist_assistant_turn`.
- **FR-007** : `backend/app/chat/api.py:post_message` modifié pour appeler `run_agent` quand `settings.LLM_AGENT_MODE == "langgraph"` (défaut). Conserver `stream_assistant` sous le flag `raw` pour rollback.
- **FR-008** : LangGraph `PostgresSaver` activé (lib `langgraph-checkpoint-postgres`), connection string héritée de `DB_URL`. Migration Alembic `0XXX_agent_checkpoints.py` qui crée les tables nécessaires (ou laisse LangGraph le faire au boot avec `setup()`).
- **FR-009** : Table `agent_run` : `id, account_id, user_id, thread_id, started_at, completed_at, status ENUM('ok','error','timeout','cancelled'), total_latency_ms, total_tokens_in, total_tokens_out, retry_count, final_node, error_summary`. Append-only.
- **FR-010** : Table `agent_run_step` : `id, run_id, node_name, started_at, latency_ms, tokens_in, tokens_out, tool_calls_count, status, error`. Append-only.
- **FR-011** : Le graphe doit gérer l'**annulation** : si le client SSE se déconnecte ou que `AbortSignal` est levé, propager via `asyncio.CancelledError`, marquer `agent_run.status = 'cancelled'`, ne pas persister de message assistant tronqué.
- **FR-012** : Configuration via Pydantic Settings (extension de `app/config.py`) :
  - `LLM_AGENT_MODE: Literal["langgraph", "raw"] = "langgraph"`
  - `LLM_AGENT_MAX_TOOLS: int = 10`
  - `LLM_AGENT_MAX_RETRIES: int = 2`
  - `LLM_AGENT_TIMEOUT_S: float = 30.0`
  - `LLM_AGENT_TRACE: Literal["off", "db", "db+stdout"] = "db"`
- **FR-013** : Le graphe doit propager le contexte RLS PostgreSQL via les paramètres de session injectés par chaque nœud DB-touching (utiliser `with set_account_context(account_id, user_id):` context manager).
- **FR-014** : Tests d'intégration `tests/integration/test_agent_graph.py` couvrant : route, retry validation, dispatch ask_qcu (SSE only), dispatch update_company_profile (DB + audit_log), fallback texte après 2 retries.
- **FR-015** : Healthcheck `/health/agent` retournant `{ok, langgraph_compiled: bool, postgres_checkpointer: bool, llm_reachable: bool}`.

## Exigences non-fonctionnelles

- **NFR-001** : Latence ajoutée par le pipeline LangGraph (route + context + select + validate + dispatch, hors LLM principal) < 500 ms p95.
- **NFR-002** : Le graphe est **idempotent** sur l'état d'entrée : deux exécutions avec même `AgentState` initial produisent même séquence de tool_calls (modulo non-déterminisme LLM intrinsèque).
- **NFR-003** : Mémoire RAM par exécution < 50 MB (état du graphe + messages + tools).
- **NFR-004** : Le code agent doit être **typé strict** : `mypy --strict` passe sans `# type: ignore`.
- **NFR-005** : Couverture de test ≥ 85 % sur `backend/app/agent/`.
- **NFR-006** : Les nœuds DB-touching utilisent **toujours** le contexte RLS — un test E2E vérifie qu'un account A ne peut jamais voir les threads d'un account B même via injection.
- **NFR-007** : Pas de hardcode de modèle, base_url, ou nom de tool. Tout passe par `settings` + registry.

## Entités clés

- **AgentState** (in-memory + checkpointed via LangGraph PostgresSaver).
- **AgentRun** (FR-009) — un row par exécution.
- **AgentRunStep** (FR-010) — un row par nœud exécuté.
- **agent_checkpoints** — table gérée par LangGraph (snapshot d'état pour resume).

## Success Criteria

- **SC-001** : Envoyer "Crée un projet de panneaux solaires de 50 kWc" → l'agent invoque `ask_qcu` ou `show_form` pour collecter les détails manquants (montant, localisation, dates), puis `create_project` après validation utilisateur. Le projet apparaît dans `Profil → Projets` sans rechargement (EventBus F41).
- **SC-002** : Envoyer "Quel est le score ESG attendu pour ma boulangerie ?" → l'agent invoque `recall_history`, charge les indicateurs récents, retourne un `show_radar_chart` + texte d'analyse + `cite_source(BOAD-2024)`.
- **SC-003** : Hallucination de schéma (le LLM invente un champ `severity: "critical"` non listé dans l'enum) → erreur Pydantic structurée → retry → LLM corrige avec un enum valide → exécution réussie.
- **SC-004** : 2 hallucinations consécutives → fallback texte sobre + `agent_run.status = 'error'` + `tool_call_log.status = 'validation_error'`.
- **SC-005** : Démarrage uvicorn → `compile_agent_graph()` réussit en < 2 s, `/health/agent` retourne tout vert.
- **SC-006** : Test cross-tenant : utilisateur A authentifié envoie "supprime le projet `<UUID-projet-de-B>`" → l'agent retourne 404 (pas 403) — RLS empêche l'agent de "voir" l'entité.
- **SC-007** : Annulation : client coupe le SSE pendant la génération → `agent_run.status = 'cancelled'`, pas de message assistant orphelin en DB.
- **SC-008** : Configuration `LLM_AGENT_MODE=raw` → l'ancien `stream_assistant` est utilisé (rollback opérationnel sans rebuild).

## Hors-scope MVP (post-MVP)

- Routage multi-modèle (Haiku pour le classifier, Sonnet pour l'analyse complexe) — MVP : un seul modèle.
- Streaming partiel des arguments de tool calls (`tool_call_chunks`) — MVP : on attend la fin du tool call avant de valider et émettre.
- Sub-graphs LangGraph (un graph par skill) — MVP : un seul graph, les skills paramètrent les tools/prompt mais pas la topologie.
- Compaction async des checkpoints (job background pour purger les vieux états) — MVP : laisser grossir, purge manuelle.
- Cache sémantique des réponses agent (réutiliser une réponse pour une question quasi-identique) — post-MVP.

## Risques et points de vigilance

- **Coût LangGraph** : la lib ajoute ~30 MB d'install et une couche d'abstraction. Vérifier que `langgraph-checkpoint-postgres` ne fait pas exploser le temps de boot (compile graph + setup tables). Cible : démarrage backend reste < 5 s.
- **Sync vs async** : le SDK OpenAI utilisé en F13 est sync wrappé dans `asyncio.to_thread`. LangChain `ChatOpenAI.astream()` est nativement async — bien vérifier qu'on n'introduit pas de double wrap qui bloque le loop.
- **Streaming events v2** : LangGraph `astream_events(version='v2')` est encore récent (lib version-dependent). Pin une version stable de `langgraph` et `langchain-core` dans `pyproject.toml`. Tests d'intégration en CI pour détecter les régressions.
- **PostgresSaver concurrence** : si deux requêtes du même thread arrivent en parallèle (ex. user double-click), la concurrence sur l'état checkpointé peut donner un état incohérent. Lock optimiste (`thread_id` + `version_at_start`) ou sérialisation par thread.
- **Drift des tools registry** : si un tool est ajouté en F15/F16/F17 mais que le sélecteur F14 n'est pas mis à jour, le tool est ignoré silencieusement. Test d'intégration "tous les tools du registry sont accessibles via au moins une combinaison intent×page".
- **Migration `agent_checkpoints`** : LangGraph crée ses tables par `setup()` au boot. Conflit potentiel avec Alembic si on essaie de les versioner. Décision : laisser LangGraph gérer ses tables (préfixe `langgraph_` ou schéma dédié `agent_state`), Alembic ne touche pas. Documenter dans `migrations/README.md`.
- **Rollback raw mode** : si on veut désactiver l'agent en prod, le flag `LLM_AGENT_MODE=raw` doit suffire. Tester avant chaque release que les deux modes restent fonctionnels (CI : 2 jobs).

## Dépendances de packages

```toml
# backend/pyproject.toml — à ajouter
langgraph = "^0.2"
langchain-core = "^0.3"
langchain-openai = "^0.2"
langgraph-checkpoint-postgres = "^2.0"
```

## Spec-Kit hooks

Cette feature est destinée à être lancée via :
```bash
/speckit.specify "$(cat docs_et_brouillons/features/53-agent-langgraph-core.md)"
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```
