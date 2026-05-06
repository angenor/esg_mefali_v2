# F55 — Tool Dispatch & SSE Bridge (mutations + bottom sheet + viz)

**Phase** : H — Agent Hardening
**Modules brainstorm** : 1.1.1 (Tools de réponse), 1.1.2 (Visualisation), 1.1.3 (LLM moteur d'action), 10.1 (Architecture en couches)
**Dépendances** : F15 (bottom sheet engine), F16 (viz library), F17 (tools mutation), F39 (UI sheet), F40 (UI viz), F41 (chat UI), F53 (LangGraph core)
**Estimation** : 4 jours

## Contexte et objectif

Les tools sont déclarés (F14), exposés au LLM (F53), validés (F14 payload validator). Reste à les **exécuter** quand le LLM les invoque. Selon la nature du tool, "exécuter" signifie quelque chose de très différent :

| Catégorie | Exemples | Action backend | Action frontend |
|---|---|---|---|
| **Question fermée** | `ask_qcu`, `ask_qcm`, `ask_select`, `ask_number`, `ask_yes_no`, `ask_date`, `ask_file_upload`, `show_form` | rien (juste émettre l'event) | ouvrir bottom sheet F39 |
| **Visualisation** | `show_kpi_card`, `show_radar_chart`, `show_bar_chart`, `show_line_chart`, `show_donut_chart`, `show_timeline`, `show_comparison_table`, `show_match_card`, `show_map`, `show_mermaid`, `show_summary_card` | rien (payload sourcé déjà validé) | rendre composant F40 inline dans la bulle assistant |
| **Mutation** | `update_company_profile`, `create_project`, `update_project`, `delete_project`, `create_candidature`, `update_candidature_status`, `attach_document`, `recompute_score`, `generate_attestation`, `revoke_attestation`, `generate_dossier` | exécuter handler → DB + audit_log + EventBus | refresh page concernée via EventBus |
| **Lecture / RAG** | `cite_source`, `search_source`, `flag_unsourced`, `recall_history` | exécuter handler → résultat re-injecté au LLM | aucune action |

F55 livre le **dispatcher** côté backend + le **protocole SSE** vers le frontend + les hooks de **persistance** et **audit log**.

## User Stories

### US1 — Catégorisation déclarative des tools (P1)

**En tant que** dev,
**je veux** que chaque `ToolDef` enregistré dans `tool_registry` déclare une `category: ToolCategory` parmi `ASK`, `SHOW`, `MUTATION`, `READ`,
**afin que** le dispatcher route automatiquement chaque tool call vers la bonne stratégie d'exécution.

Implementation : ajout d'un champ `category` à `ToolDef` (F14), migration des tools existants en F15/F16/F17.

### US2 — Dispatcher central (P1)

**En tant que** dev,
**je veux** un module `app/agent/dispatcher.py` exposant `async def dispatch(call: ValidatedToolCall, state: AgentState, db: Session) -> ToolDispatchResult` qui switche sur la catégorie :
- `ASK` / `SHOW` → renvoie un `ToolDispatchResult(kind="frontend_event", payload=...)` ; pas d'effet de bord backend.
- `MUTATION` → exécute le handler du tool dans une **transaction DB** avec contexte RLS, écrit un row `audit_log` (`source_of_change='llm'`), publie un message EventBus, retourne `ToolDispatchResult(kind="mutation_result", entity_type, entity_id, fields_updated)`.
- `READ` → exécute le handler, sérialise le résultat, retourne `ToolDispatchResult(kind="tool_message", content=json.dumps(result))` qui sera ré-injecté en `ToolMessage` LangChain pour le prochain tour LLM (boucle).

### US3 — Émission SSE événements F41-compatibles (P1)

**En tant que** dev,
**je veux** que le runner F53 émette les events SSE suivants, conformes au protocole F41 (frontend déjà prêt) :

| Event SSE | Source backend | Frontend handler |
|---|---|---|
| `text_delta` | LangChain `on_chat_model_stream` | append au content du message assistant |
| `tool_call_started` | LangChain `on_tool_start` | (debug only, optionnel) |
| `tool_invoke` | dispatcher catégorie `ASK` ou `SHOW` | `useChatToolBridge` → `useChatBottomSheet().open` (F39) ou `<VizRenderer>` inline (F40) |
| `mutation` | dispatcher catégorie `MUTATION` | `useChatEventBus().emit('entity_updated', ...)` → stores Pinia refresh |
| `tool_call_completed` | dispatcher succès | `tool_call_log.status = 'ok'` (admin only) |
| `error` | retry exhausted ou handler exception | bulle d'erreur F41 |
| `message_done` | fin du graph | finalisation du message assistant |

Format event :
```
event: tool_invoke
data: {"tool": "ask_qcu", "id": "<call_id>", "payload": { question: "...", choices: [...] }}
```

### US4 — Handler des tools de mutation (P1)

**En tant que** dev,
**je veux** que chaque tool de mutation déclare un `handler: Callable[[ValidatedArgs, MutationCtx], Awaitable[MutationResult]]` au moment de l'enregistrement F17, signature exemple :

```python
async def update_company_profile_handler(
    args: UpdateCompanyProfileArgs,
    ctx: MutationCtx,  # account_id, user_id, db, audit_logger
) -> MutationResult:
    # 1. Vérifier RLS (déjà appliqué via SET LOCAL au niveau session)
    # 2. Calculer le diff field-by-field
    # 3. Appliquer le UPDATE SQL via service.update_entreprise(...)
    # 4. ctx.audit_logger.append_many(diffs, source='llm')
    # 5. Retourner MutationResult(entity_type='Entreprise', entity_id=..., fields_updated=[...])
```

**afin de** centraliser la logique d'exécution et garantir l'audit_log à 100%.

### US5 — Audit log automatique (P1)

**En tant que** dev,
**je veux** qu'à chaque mutation effectuée par l'agent, une ligne soit ajoutée dans `audit_log` avec :
- `user_id`, `account_id`, `timestamp`, `entity_type`, `entity_id`
- `field` + `old_value` + `new_value` (pour chaque champ modifié)
- `source_of_change = 'llm'`
- `tool_call_id` (référence vers `tool_call_log`)
- `agent_run_id` (référence vers `agent_run` F53)

**afin de** offrir une traçabilité totale en cas de litige (P3 constitution).

### US6 — Confirmation pour mutations destructives (P1)

**En tant que** utilisateur,
**je veux** que les tools `delete_*`, `revoke_attestation`, `update_candidature_status(closed)` ne s'exécutent **jamais** directement même si le LLM les invoque,
**afin d'** éviter une perte de données par hallucination.

Implémentation : ces tools sont marqués `requires_confirmation=True` dans `ToolDef`. Quand le LLM les invoque, le dispatcher :
1. Émet un `tool_invoke` `ask_yes_no` avec un récap clair ("Confirmer la suppression du projet 'Solaire 50 kWc' ?").
2. Attend la réponse user (next turn).
3. Si confirmation → exécute le handler. Sinon → annulation propre.

### US7 — Rate limiting par tool et par compte (P1)

**En tant que** ops,
**je veux** un rate limiter (Redis si dispo, sinon in-memory bounded LRU) sur les mutations agent par `(account_id, tool_name)`,
**afin d'** empêcher un comportement runaway (boucle de mutations) :
- `update_*` : max 30 / minute / account.
- `create_*` : max 10 / minute / account.
- `delete_*` : max 5 / minute / account.
- `generate_*` : max 5 / minute / account.

Dépassement → `tool_call_log.status = 'rate_limited'`, fallback texte "trop de modifications successives, ralentissons".

### US8 — Idempotence des tool calls (P1)

**En tant que** dev,
**je veux** que chaque tool call ait un `idempotency_key = hash(account_id, agent_run_id, call_id)` et que le dispatcher vérifie en table `tool_call_log` avant d'exécuter,
**afin d'** éviter les doubles exécutions en cas de retry réseau ou de reconnexion SSE.

Si `idempotency_key` déjà présent → retourner le résultat précédent, ne pas ré-exécuter.

### US9 — Hooks pre / post handler (P2)

**En tant que** dev,
**je veux** un système de hooks (`@before_dispatch`, `@after_dispatch`) pour ajouter transversalement des comportements (telemetry F60, feature flags, A/B testing),
**afin de** éviter de modifier chaque handler individuellement.

### US10 — Mode "dry run" admin (P2)

**En tant que** admin,
**je veux** pouvoir activer un mode `agent.dry_run = True` par session admin,
**afin de** voir ce que ferait l'agent sans qu'il modifie réellement la DB. Les events SSE sont émis avec un préfixe `dry_run:` pour le frontend.

## Exigences fonctionnelles

- **FR-001** : Module `backend/app/agent/dispatcher.py` exposant `async def dispatch(call, state, db) -> ToolDispatchResult`. Routing par `ToolCategory`.
- **FR-002** : Type `ToolCategory = Literal["ASK", "SHOW", "MUTATION", "READ"]`. Champ ajouté à `ToolDef` (extension F14, migration des tools existants).
- **FR-003** : Type `ToolDispatchResult` (Pydantic, extra='forbid') : variantes `frontend_event | mutation_result | tool_message | error`.
- **FR-004** : Module `backend/app/agent/sse.py` exposant `format_event(event_type: str, data: dict, id: int | None = None) -> str` pour générer les frames SSE conformes F41.
- **FR-005** : Le runner F53 (`runner.py`) consomme les events LangGraph (`astream_events(version='v2')`), les transforme en frames SSE via `format_event`, yield au client.
- **FR-006** : Module `backend/app/agent/mutation_ctx.py` exposant la classe `MutationCtx` qui groupe `account_id`, `user_id`, `db`, `audit_logger`, `event_bus_publisher`, `tool_call_log_id`, `agent_run_id`.
- **FR-007** : Décorateur `@mutation_handler(tool_name: str, requires_confirmation: bool = False)` pour enregistrer un handler. Stocké dans `MUTATION_HANDLERS: dict[str, Handler]`.
- **FR-008** : Tous les tools mutation existants (F17 — `update_company_profile`, `create_project`, `update_project`, `delete_project`) reçoivent un handler décoré. Si un handler manque → exception au boot (fail-fast).
- **FR-009** : Audit log via `app.audit.append_diff(account_id, user_id, entity_type, entity_id, diffs, source_of_change='llm', tool_call_id, agent_run_id)`. Ajout des deux colonnes `tool_call_id`, `agent_run_id` (NULLABLE) dans `audit_log` via migration Alembic.
- **FR-010** : Rate limiter `app.agent.rate_limit.check_and_increment(account_id, tool_name)` avec backend Redis ou in-memory. Limites configurables via `LLM_AGENT_RATE_LIMITS` JSON env.
- **FR-011** : Idempotence : table `tool_call_log` (déjà prévue F14) servant de store. Index unique sur `(account_id, idempotency_key)`.
- **FR-012** : Confirmation flow : tools `requires_confirmation=True` ne sont **jamais** appelés directement. Le dispatcher convertit le call en `ask_yes_no` SSE event + stocke un `pending_confirmation` dans `agent_run.metadata`. Au tour suivant, si la réponse user est "Oui" pour ce `pending_confirmation`, on exécute le call original.
- **FR-013** : EventBus publish via `app.chat.event_bus.publish(account_id, event_type, payload)` (déjà existant).
- **FR-014** : Tests d'intégration `tests/integration/test_dispatcher.py` : 1 test par catégorie, 1 test pour rate limit, 1 test pour idempotence, 1 test pour confirmation.

## Exigences non-fonctionnelles

- **NFR-001** : Latence dispatch d'un `ASK`/`SHOW` (juste l'event SSE) < 5 ms.
- **NFR-002** : Latence dispatch d'une `MUTATION` simple (1 update + 1-3 audit rows + 1 publish) < 100 ms p95.
- **NFR-003** : Latence dispatch d'un `READ` (recall_history avec embedding cosine search 1M lignes) < 500 ms p95.
- **NFR-004** : Dispatcher est thread-safe et asyncio-safe (un seul `MutationCtx` par tour, jamais partagé).
- **NFR-005** : Aucune mutation ne peut s'exécuter sans contexte RLS appliqué — vérifié par test E2E.
- **NFR-006** : Couverture de test ≥ 90 % sur `app/agent/dispatcher.py` et `app/agent/mutation_ctx.py`.
- **NFR-007** : Rate limiter back-pressure : si le store rate-limit est inaccessible (Redis down), le dispatcher refuse d'exécuter les mutations (fail-safe, pas fail-open).

## Entités clés

- **ToolCallLog** (F14) — étendue avec `idempotency_key`, `agent_run_id`, `dispatch_result_kind`.
- **AuditLog** (F04) — étendue avec `tool_call_id` et `agent_run_id` NULLABLE.
- **PendingConfirmation** — JSON dans `agent_run.metadata`, pas de table dédiée.

## Success Criteria

- **SC-001** : LLM invoque `ask_qcu("Quelle forme juridique?")` → frontend ouvre la bottom sheet sans rechargement, l'utilisateur clique "SARL", le tour suivant l'agent reçoit `sheet_result` et continue.
- **SC-002** : LLM invoque `update_company_profile(secteur="C10.71")` → DB updated, audit_log row créé avec `source_of_change='llm', tool_call_id=..., agent_run_id=...`, page `Profil → Entreprise` ouverte ailleurs se rafraîchit via EventBus.
- **SC-003** : LLM invoque `delete_project(id=...)` → l'agent ne supprime PAS, il émet `ask_yes_no` "Confirmer la suppression du projet 'X'?". User clique "Non" → annulation propre, projet intact.
- **SC-004** : 31 invocations `update_company_profile` en 60 s → 30 passent, la 31e échoue avec `tool_call_log.status='rate_limited'`, fallback texte poli.
- **SC-005** : Reconnexion SSE pendant un `create_project` → dispatcher détecte l'idempotency_key existant → ne re-crée pas le projet, retourne le result précédent.
- **SC-006** : LLM invoque `show_radar_chart(payload=...)` → SSE `tool_invoke` avec payload validé Pydantic, frontend rend le composant inline dans la bulle assistant.
- **SC-007** : LLM invoque `recall_history("scoring 2024")` → résultat top-3 messages re-injecté en `ToolMessage`, le LLM rappelle correctement le contexte au tour suivant.
- **SC-008** : Mode `dry_run=True` activé → mutation simulée, audit_log NON écrit, frontend reçoit event préfixé `dry_run:mutation` (bandeau "simulation").

## Hors-scope MVP (post-MVP)

- Transactions multi-tools atomiques (un rollback si une mutation échoue parmi 3 tool calls dans un même tour) — MVP : best-effort sequentiel.
- Compensations / sagas (annulation automatique des mutations précédentes en cas d'échec d'une suivante) — post-MVP.
- Webhooks externes pour notifier des intégrations tierces — post-MVP.
- File de mutations différées (queue Celery pour mutations longues comme `generate_dossier`) — MVP : sync, on accepte la latence.
- A/B testing par tool (50 % des users avec handler v1, 50 % avec v2) — post-MVP.

## Risques et points de vigilance

- **Inconsistance audit_log ↔ DB** : si le UPDATE réussit mais l'INSERT audit_log échoue, on a une mutation non tracée. Solution : exécuter les deux dans la **même transaction** ; rollback unique si l'un échoue.
- **Boucle infinie via READ tools** : si le LLM appelle en boucle `recall_history` sans jamais répondre, on consomme tokens à l'infini. Limite hard : `agent_run.tool_calls_count <= 10` par tour, après quoi on force `compose_response`.
- **EventBus loop** : une mutation publie un event qui arrive sur la page Profil ouverte → la page recharge → si le code de page redéclenche par erreur une autre mutation chat → boucle. Garde-fou : `event.source = 'llm'` ne doit JAMAIS déclencher une mutation chat (P8).
- **Rate limit shared state** : in-memory ne marche pas en multi-instance backend. Utiliser Redis dès qu'on a > 1 worker. Documenter dans README.md.
- **Confirmation flow multi-tours** : le `pending_confirmation` doit avoir un TTL (3 minutes) pour éviter qu'un user clique "Oui" 1h plus tard sur une mutation hors contexte. Stocké avec `expires_at`.
- **Idempotency key collision** : si deux requêtes utilisateur ont les mêmes `(account, agent_run, call_id)`, on a un bug ailleurs. Test : assertion d'unicité, alerte.
- **Drift dispatcher ↔ registry** : si un nouveau tool est ajouté sans `category`, il échoue au boot — bonne chose, fail-fast. CI peut linter pour confirmer.

## Spec-Kit hooks

```bash
/speckit.specify "$(cat docs_et_brouillons/features/55-agent-tool-dispatch-sse.md)"
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```
