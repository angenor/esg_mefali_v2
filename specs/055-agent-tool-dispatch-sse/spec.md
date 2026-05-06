# Feature Specification: Agent Tool Dispatch & SSE Bridge

**Feature Branch**: `055-agent-tool-dispatch-sse`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "F55 — Tool Dispatch & SSE Bridge (mutations + bottom sheet + viz). Phase H — Agent Hardening. Dépend de F15 bottom sheet engine, F16 viz library, F17 tools mutation, F39 UI sheet, F40 UI viz, F41 chat UI, F53 LangGraph core. Livrer un dispatcher central côté backend qui exécute chaque tool call validé selon sa catégorie (ASK/SHOW frontend-only, MUTATION DB+audit, READ ré-injection LLM), puis pousser les résultats au frontend via un protocole SSE incluant text_delta, tool_invoke, mutation, tool_call_completed, error, message_done. Couvre la confirmation pour mutations destructives, le rate limit (30/10/5/5 par minute par account), l'idempotence par hash(account_id, agent_run_id, call_id), le mode dry_run admin, l'audit log automatique 100% (tool_call_id + agent_run_id sur audit_log), les hooks pre/post handler."

## Clarifications

### Session 2026-05-06

- Q: Quel est le scope d'unicité de l'`idempotency_key` ? → A: UNIQUE per (account_id, idempotency_key) (cohérent P2 RLS multi-tenant ; collision improbable mais détection fail-fast).
- Q: Quel backend de stockage du rate limiter doit-on retenir par défaut en dev et prod ? → A: In-memory bounded LRU acceptable en dev single-worker ; Redis obligatoire en prod multi-worker. L'interface garantit le fail-safe NFR-007 indépendamment du backend.
- Q: Comment stocker un `pending_confirmation` ? → A: JSON dans `agent_run.metadata` (TTL 3 min applicatif) ; pas de table dédiée — évite une migration et reflète le brief.
- Q: Quel format pour le résultat d'un tool READ ré-injecté en `ToolMessage` ? → A: JSON résumé/structuré tronqué à un budget tokens configurable via env (défaut top-N, paramétré par tool) ; jamais de JSON brut illimité — protège le contexte LLM et le coût.
- Q: L'event SSE `tool_call_completed` est-il émis pour tous les users ou admin only ? → A: Admin only (debug/QA). Le frontend filtre par rôle ; les users PME ne le reçoivent pas pour réduire le bruit UI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mutation pilotée par le LLM avec audit complet (Priority: P1)

Une PME authentifiée écrit dans le chat « Mets à jour mon secteur d'activité, c'est de la boulangerie pâtisserie ». L'agent valide le tool call `update_company_profile(secteur="C10.71")`, exécute le handler en transaction DB sous contexte RLS, écrit la ligne `audit_log` (`source_of_change='llm'`, `tool_call_id`, `agent_run_id`), publie un event sur l'EventBus. La page « Profil → Entreprise » ouverte sur un autre onglet se rafraîchit automatiquement, et la PME voit confirmation visuelle dans le chat.

**Why this priority** : C'est la promesse produit centrale (« je parle à ESG Mefali, il agit »). Sans dispatcher correct, les mutations LLM restent purement déclaratives et la mémoire/audit/RLS ne sont pas garantis.

**Independent Test** : Avec un compte PME authentifié, envoyer le message via l'UI chat → vérifier que (1) la ligne `audit_log` existe avec `source_of_change='llm'`, `tool_call_id`, `agent_run_id`, (2) une page Profil ouverte ailleurs se met à jour sans rechargement, (3) le `tool_call_log.status='ok'`.

**Acceptance Scenarios** :

1. **Given** une PME authentifiée avec son entreprise existante et le chat ouvert, **When** elle envoie « Mets à jour mon secteur, c'est de la boulangerie pâtisserie » et l'agent invoque `update_company_profile(secteur="C10.71")`, **Then** une ligne audit_log est créée avec `source_of_change='llm'`, `tool_call_id`, `agent_run_id`, le secteur en base devient `C10.71`, l'EventBus pousse `entity_updated` aux stores Pinia front et la page Profil ouverte sur un autre onglet reflète la valeur sans rechargement.
2. **Given** la mutation a échoué côté DB (contrainte violée), **When** l'agent tente d'écrire, **Then** la transaction est rollback, aucune ligne audit_log n'est créée, le `tool_call_log.status='error'` et un event SSE `error` est émis vers le frontend avec un message neutre.
3. **Given** un compte A et un projet `P_B` du compte B, **When** l'agent du compte A invoque par erreur `update_project(id=P_B.id)`, **Then** le handler retourne « entité introuvable » (404 logique RLS), aucune mutation ne traverse vers B et aucune ligne audit ne référence B.

---

### User Story 2 — Bottom sheet (ASK) et visualisation inline (SHOW) (Priority: P1)

Une PME demande « Quel est mon score ESG attendu ? ». L'agent invoque `ask_qcu("Quelle forme juridique?", choices=["SARL","SAS","SA","Autre"])` ; la bottom sheet F39 s'ouvre côté frontend, animée par gsap, sans inline dans la bulle assistant. La PME clique « SARL », le résultat est renvoyé au tour suivant. L'agent invoque ensuite `show_radar_chart(payload)` ; le composant F40 se rend inline dans la bulle assistant.

**Why this priority** : Sans cette catégorisation et le push SSE adéquat, l'UX bottom sheet (P10) n'est jamais déclenchée et la viz ne s'affiche pas inline. La règle P10 est non négociable : tout input interactif vit en bottom sheet, jamais inline.

**Independent Test** : Envoyer via le chat un message qui force `ask_qcu` puis `show_radar_chart` → vérifier que (1) la bottom sheet s'ouvre via SSE `tool_invoke`, (2) la sélection retournée est ré-injectée au tour suivant, (3) le radar chart se rend dans la bulle assistant.

**Acceptance Scenarios** :

1. **Given** une PME en chat, **When** l'agent invoque `ask_qcu` (catégorie ASK), **Then** un event SSE `tool_invoke` est émis sans toucher la DB, le frontend ouvre la bottom sheet F39, l'utilisateur valide et le résultat est ré-injecté au tour suivant via le composable `useChatToolBridge`.
2. **Given** une PME en chat avec un score ESG calculé, **When** l'agent invoque `show_radar_chart(payload validé Pydantic strict)`, **Then** le frontend rend le composant F40 inline dans la bulle assistant et la bulle reste display-only (pas d'input).
3. **Given** un payload `show_*` non sourcé (pas de `source_id`), **When** le validateur F14 le voit, **Then** le tool call est rejeté en amont (P1 sourcing) et n'atteint jamais le dispatcher.

---

### User Story 3 — Confirmation utilisateur pour mutations destructives (Priority: P1)

Une PME demande « Supprime mon projet de panneaux solaires ». L'agent invoque `delete_project(id=...)` mais ce tool est marqué `requires_confirmation=True`. Le dispatcher n'exécute PAS la suppression, il convertit le call en `ask_yes_no("Confirmer la suppression du projet 'Solaire 50 kWc' ?")` et stocke un `pending_confirmation` (avec `expires_at` à 3 minutes). Si la PME clique « Non » → annulation propre, le projet reste intact et un message neutre s'affiche. Si la PME clique « Oui » → le call original est ré-exécuté et la suppression aboutit.

**Why this priority** : Sans ce garde-fou, une hallucination LLM peut déclencher une perte de données irréversible. C'est un invariant produit qui doit être inviolable.

**Independent Test** : Envoyer le message « supprime ce projet », vérifier que la bottom sheet `ask_yes_no` apparaît, cliquer « Non », vérifier en base que le projet existe toujours et que `tool_call_log.status='cancelled_by_user'`.

**Acceptance Scenarios** :

1. **Given** une PME avec un projet existant, **When** l'agent invoque `delete_project(id=...)`, **Then** le dispatcher émet un SSE `tool_invoke` `ask_yes_no` avec un récap clair, stocke `pending_confirmation` dans `agent_run.metadata` avec `expires_at`, et n'appelle PAS le handler de suppression.
2. **Given** une `pending_confirmation` active, **When** la PME répond « Non » au tour suivant, **Then** le dispatcher annule le call, écrit `tool_call_log.status='cancelled_by_user'`, n'écrit AUCUNE ligne audit, le projet est intact.
3. **Given** une `pending_confirmation` qui a expiré (>3 min), **When** la PME clique « Oui » tardivement, **Then** le dispatcher refuse l'exécution avec un message `confirmation_expired`, n'exécute pas la mutation, demande à la PME de relancer la demande.

---

### User Story 4 — Rate limit anti-runaway et idempotence (Priority: P1)

Un agent buggé ou un comportement runaway tente d'exécuter 31 appels `update_company_profile` en moins de 60 secondes. Le rate limiter laisse passer les 30 premiers, refuse le 31e avec `tool_call_log.status='rate_limited'` et un fallback texte « Trop de modifications successives, ralentissons ». En parallèle, si le frontend reconnecte sa connexion SSE pendant qu'un `create_project` est en vol, le dispatcher détecte l'`idempotency_key` déjà présent en DB et retourne le résultat précédent au lieu de re-créer.

**Why this priority** : Sans rate limit et idempotence, un bug ou une reconnexion réseau peut multiplier les mutations DB et corrompre le tenant. Ces deux garde-fous sont strictement requis pour une plateforme multi-tenant.

**Independent Test** : Lancer un script de stress qui invoque 31 fois `update_company_profile` en 60 s → vérifier 30 succès + 1 `rate_limited`. Lancer un test qui ré-envoie deux fois le même `(account, agent_run, call_id)` → vérifier qu'une seule ligne business est créée.

**Acceptance Scenarios** :

1. **Given** un compte PME, **When** 31 invocations de `update_*` sont émises en 60 s, **Then** la 31e échoue avec `tool_call_log.status='rate_limited'`, aucun row business n'est écrit pour la 31e, un SSE `error` côté frontend explique poliment.
2. **Given** un `create_project` exécuté avec succès, **When** une reconnexion SSE déclenche le re-envoi du même tool_call_id, **Then** le dispatcher détecte la collision d'`idempotency_key`, ne re-crée pas, retourne le `ToolDispatchResult` précédent.
3. **Given** le store rate-limit (Redis) inaccessible, **When** une mutation est tentée, **Then** le dispatcher refuse fail-safe avec `tool_call_log.status='error'` et `error_summary='rate_limit_unavailable'` ; en aucun cas la mutation n'est exécutée sans contrôle.

---

### User Story 5 — READ tool ré-injecté au LLM (Priority: P1)

Une PME demande « Comment était mon scoring en 2024 ? ». L'agent invoque `recall_history(query="scoring 2024")`. Le handler effectue la recherche embedding + cosine sur l'historique du tenant, sérialise les top-3 messages, retourne un `ToolDispatchResult(kind="tool_message")` que le runner ré-injecte en `ToolMessage` LangChain au tour suivant. Le LLM rappelle correctement le contexte et compose la réponse.

**Why this priority** : Sans ré-injection des résultats READ, l'agent ne peut pas faire de RAG ni rappeler la mémoire conversationnelle, ce qui est central pour la promesse produit (analyse contextuelle PME).

**Independent Test** : Démarrer une session avec historique non-vide, invoquer `recall_history` via un message qui force ce tool → vérifier que les top-3 messages historiques apparaissent dans le contexte du tour LLM suivant.

**Acceptance Scenarios** :

1. **Given** une PME avec 50+ messages d'historique, **When** elle demande un rappel, **Then** l'agent invoque `recall_history`, le handler retourne top-3 résultats sérialisés, le runner injecte un `ToolMessage` LangChain, le LLM produit une réponse cohérente avec ces 3 messages.
2. **Given** le LLM appelle en boucle 10+ READ sans répondre, **When** la limite hard `tool_calls_count <= 10` est atteinte, **Then** le runner force `compose_response` et émet un fallback texte au frontend.

---

### User Story 6 — Mode dry_run admin (Priority: P2)

Un admin active `agent.dry_run=True` pour sa session de support. Il interagit avec l'agent normalement ; les mutations sont simulées (pas de UPDATE DB, pas de ligne audit) mais les events SSE sont émis avec un préfixe `dry_run:` qui pousse au frontend un bandeau « simulation ».

**Why this priority** : Permet aux admins de tester l'agent et de reproduire un bug client sans risquer de toucher les données réelles. Important pour le support et le QA mais non bloquant pour le MVP utilisateur.

**Independent Test** : Activer `agent.dry_run=True` côté admin, invoquer une mutation, vérifier que le SSE event est `dry_run:mutation`, qu'aucune ligne audit n'est écrite et qu'aucun row business n'est touché.

**Acceptance Scenarios** :

1. **Given** un admin avec `dry_run=True`, **When** il déclenche une mutation, **Then** aucun UPDATE DB ne se fait, aucune ligne audit n'est écrite, le SSE event est préfixé `dry_run:`, le frontend affiche un bandeau « simulation ».
2. **Given** un user PME normal (pas admin), **When** il tente d'activer `dry_run`, **Then** la requête est refusée avec 403.

---

### User Story 7 — Hooks pre/post handler (Priority: P2)

Un dev plateforme ajoute un hook `@before_dispatch` pour logger toutes les mutations dans un système de telemetry externe (F60), sans modifier chaque handler individuellement. Un autre `@after_dispatch` ajoute un compteur Prometheus.

**Why this priority** : Améliore la maintenabilité et l'observabilité, mais peut être ajouté progressivement après le MVP fonctionnel.

**Independent Test** : Enregistrer un hook trivial qui incrémente un compteur, exécuter une mutation, vérifier que le compteur est incrémenté.

**Acceptance Scenarios** :

1. **Given** un hook `@before_dispatch` enregistré, **When** une mutation est dispatchée, **Then** le hook s'exécute avant le handler, sa sortie est loggée, et la sortie ne casse pas le dispatch même si elle lève une exception (best-effort, exception absorbée et loggée).

---

### Edge Cases

- **Inconsistance audit ↔ DB** : si l'INSERT audit_log échoue après le UPDATE business, la transaction est intégralement rollback (pas de mutation orpheline).
- **EventBus loop** : un event publié par une mutation `source='llm'` n'est jamais consommé par le code chat pour redéclencher une mutation (P8).
- **Idempotency collision improbable** : deux requêtes user ayant le même `(account, agent_run, call_id)` constitueraient un bug ailleurs ; le dispatcher refuse via contrainte d'unicité DB et émet une alerte.
- **Confirmation TTL expirée** : un user qui clique « Oui » plus de 3 min après le `pending_confirmation` voit l'opération refusée proprement.
- **Rate limit store down** : le dispatcher refuse les mutations en mode fail-safe ; jamais de fail-open silencieux.
- **READ infinite loop** : limite hard de 10 tool calls par tour ; au-delà, fallback texte.
- **Tool sans handler** : un tool MUTATION enregistré sans handler ferait crasher au boot (fail-fast) plutôt qu'au runtime.
- **Drift dispatcher ↔ registry** : tout nouveau tool sans `category` déclarée fait crasher au boot (fail-fast).
- **Dry-run vs P10** : le mode dry_run émet quand même les `tool_invoke` pour `ask_*`/`show_*`, mais avec préfixe `dry_run:` ; le frontend affiche le bandeau et permet à l'admin de simuler le flux complet.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST exposer un module dispatcher central capable de router chaque tool call validé vers la stratégie d'exécution adaptée à sa catégorie (ASK, SHOW, MUTATION, READ).
- **FR-002** : Le système MUST déclarer pour chaque tool enregistré sa `ToolCategory` parmi `ASK`, `SHOW`, `MUTATION`, `READ`. Tout tool sans catégorie déclarée MUST faire échouer le boot (fail-fast).
- **FR-003** : Le système MUST exposer un type `ToolDispatchResult` strictement validé (extra='forbid') avec quatre variantes : `frontend_event` (ASK/SHOW), `mutation_result` (MUTATION), `tool_message` (READ), `error`.
- **FR-004** : Le système MUST formater des frames SSE conformes au protocole frontend F41 pour les events `text_delta`, `tool_call_started`, `tool_invoke`, `mutation`, `tool_call_completed`, `error`, `message_done`.
- **FR-005** : Le runner LangGraph MUST consommer les events LangChain (`astream_events`) et les transformer en frames SSE en streaming, sans buffering de bout en bout.
- **FR-006** : Le système MUST grouper toutes les dépendances d'une mutation (account_id, user_id, db, audit_logger, event_bus_publisher, tool_call_log_id, agent_run_id) dans un objet immuable `MutationCtx` instancié une fois par tool call.
- **FR-007** : Le système MUST fournir un mécanisme d'enregistrement de handlers de mutation (décorateur `@mutation_handler`) avec option `requires_confirmation: bool = False`.
- **FR-008** : Tous les tools MUTATION existants (au minimum `update_company_profile`, `create_project`, `update_project`, `delete_project`, `create_candidature`, `update_candidature_status`) MUST avoir un handler enregistré au boot. Un handler manquant MUST faire échouer le boot (fail-fast).
- **FR-009** : Le système MUST écrire automatiquement une ligne `audit_log` à chaque mutation LLM, avec `source_of_change='llm'`, `tool_call_id` (NULLABLE jusqu'ici, désormais renseigné pour mutations LLM) et `agent_run_id` (NULLABLE), dans la même transaction DB que la mutation business. Une migration de schéma MUST ajouter ces deux colonnes.
- **FR-010** : Le système MUST appliquer un rate limit par `(account_id, tool_name)` configurable via env var (défaut : 30/min pour `update_*`, 10/min pour `create_*`, 5/min pour `delete_*`, 5/min pour `generate_*`). Dépassement → `tool_call_log.status='rate_limited'` et fallback texte. Le backend par défaut est in-memory bounded LRU en dev (single-worker) ; Redis est requis en prod multi-worker. L'interface du rate limiter MUST exposer le fail-safe NFR-007 indépendamment du backend retenu.
- **FR-011** : Le système MUST garantir l'idempotence d'un tool call via une clé `idempotency_key = hash(account_id, agent_run_id, call_id)`. Une seconde exécution MUST retourner le résultat précédent sans ré-exécuter le handler. Une contrainte UNIQUE per `(account_id, idempotency_key)` MUST exister en base (pas global) pour respecter l'isolation tenant P2.
- **FR-012** : Pour les tools marqués `requires_confirmation=True`, le système MUST convertir le call en `ask_yes_no` SSE event, stocker un `pending_confirmation` (avec `expires_at` 3 min) dans `agent_run.metadata`, et ne PAS exécuter le handler. Le tour utilisateur suivant doit pouvoir valider ou annuler.
- **FR-013** : À chaque mutation réussie, le système MUST publier un event sur l'EventBus (key=account_id) pour que les pages frontend ouvertes ailleurs se rafraîchissent. Aucun event `source=llm` ne doit déclencher une nouvelle mutation chat (anti-loop P8).
- **FR-014** : Le système MUST inclure des tests d'intégration couvrant : 1 test par catégorie (ASK, SHOW, MUTATION, READ), 1 test rate limit, 1 test idempotence, 1 test confirmation flow + expiration, 1 test isolation cross-tenant, 1 test fail-safe rate limit store down.
- **FR-015** : Le système MUST limiter le nombre de tool calls par tour à 10 (hard cap). Au-delà, le runner force `compose_response` avec un fallback texte sobre. Pour les tools READ, le résultat ré-injecté en `ToolMessage` MUST être un JSON structuré et tronqué à un budget de tokens configurable par env (défaut top-N) ; jamais de JSON brut illimité.
- **FR-016** : Le système MUST exposer un mode `dry_run=True` activable par les comptes admin uniquement. En dry_run, aucune mutation business ni audit ne s'écrit ; les SSE events sont préfixés `dry_run:` pour signaler la simulation au frontend.
- **FR-017** : Le système MUST exposer un mécanisme de hooks `before_dispatch` et `after_dispatch` (best-effort, exceptions absorbées et loggées sans casser le dispatch).
- **FR-018** : Le frontend MUST consommer les nouveaux events SSE et router : `tool_invoke` (ASK) → bottom sheet F39 ; `tool_invoke` (SHOW) → composant viz F40 inline dans la bulle ; `mutation` → EventBus front + refresh stores Pinia concernés ; `error` → bulle d'erreur F41 ; `message_done` → finalisation message ; `tool_call_completed` → admin only (filtré côté frontend selon rôle, pas affiché aux PME pour réduire le bruit UI).
- **FR-019** : Le frontend MUST garder la bulle assistant strictement display-only (P10) ; tout input interactif passe par la bottom sheet F39.
- **FR-020** : Toute exécution de mutation MUST se faire avec le contexte RLS appliqué via `app.current_account_id` (P2 constitution). Une tentative d'exécution sans ce contexte MUST échouer fail-safe.

### Non-Functional Requirements

- **NFR-001** : Latence dispatch d'un `ASK`/`SHOW` (juste l'event SSE) sous 5 ms.
- **NFR-002** : Latence dispatch d'une `MUTATION` simple (1 update + 1-3 audit rows + 1 publish) sous 100 ms p95.
- **NFR-003** : Latence dispatch d'un `READ` (recall_history avec embedding cosine search 1M lignes) sous 500 ms p95.
- **NFR-004** : Le dispatcher MUST être thread-safe et asyncio-safe ; un `MutationCtx` n'est jamais partagé entre tool calls concurrents.
- **NFR-005** : Aucune mutation ne peut s'exécuter sans contexte RLS — vérifié par test E2E qui force l'absence du GUC et observe le refus.
- **NFR-006** : Couverture de test ≥ 90 % sur le module dispatcher, le `MutationCtx`, et le rate limiter.
- **NFR-007** : Rate limiter back-pressure : si le store (Redis ou in-memory) est inaccessible, le dispatcher REFUSE d'exécuter les mutations (fail-safe, pas fail-open).
- **NFR-008** : Le système MUST maintenir l'invariant constitutionnel P5 (Money typé Decimal+ISO, peg FCFA-EUR 655.957) sur tout payload monétaire dispatché.

### Key Entities *(include if feature involves data)*

- **ToolCallLog** (existant F14) — étendu avec `idempotency_key` (TEXT NOT NULL UNIQUE per account), `agent_run_id` (UUID NULLABLE FK vers agent_run), `dispatch_result_kind` (ENUM frontend_event | mutation_result | tool_message | error).
- **AuditLog** (existant F04) — étendu avec `tool_call_id` (UUID NULLABLE FK vers tool_call_log) et `agent_run_id` (UUID NULLABLE FK vers agent_run), pour traçabilité totale des mutations LLM.
- **PendingConfirmation** — JSON dans `agent_run.metadata`, contient `tool_call_id`, `tool_name`, `arguments`, `expires_at`. Pas de table dédiée.
- **MutationCtx** — objet runtime (pas persisté), instancié par tool call, regroupe account_id, user_id, db session, audit_logger, event_bus_publisher, tool_call_log_id, agent_run_id, dry_run flag.
- **ToolCategory** — énumération `ASK | SHOW | MUTATION | READ` portée par chaque `ToolDef` du registre.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Un utilisateur PME peut, en moins de 8 secondes après envoi d'un message, voir une bottom sheet `ask_qcu` s'ouvrir, valider sa réponse, et recevoir le tour LLM suivant. La bulle assistant ne contient AUCUN input interactif (vérifiable par test Playwright).
- **SC-002** : Une mutation `update_company_profile` déclenchée par l'agent aboutit en moins de 100 ms p95 (UPDATE + audit_log + EventBus publish), avec une ligne audit complète et la page Profil ouverte ailleurs synchronisée sans rechargement utilisateur.
- **SC-003** : Une mutation destructive (`delete_project`) ne s'exécute jamais sans confirmation utilisateur explicite ; le projet reste intact si l'utilisateur clique « Non » ou si la `pending_confirmation` expire après 3 minutes.
- **SC-004** : Sur un test de stress de 31 invocations `update_company_profile` en 60 s pour un même compte, exactement 30 mutations DB se produisent et la 31e est refusée proprement avec `tool_call_log.status='rate_limited'` et un message frontend poli.
- **SC-005** : Une reconnexion SSE pendant un `create_project` ne crée jamais deux projets ; la 2e tentative retourne le résultat précédent.
- **SC-006** : Un payload `show_radar_chart` non sourcé est rejeté par le validateur F14 et n'atteint jamais le dispatcher (P1 constitution garantie).
- **SC-007** : Une mutation tentée par un compte A sur une entité du compte B retourne 404 logique, n'écrit aucune ligne audit côté B, et n'expose aucune information cross-tenant (P2 constitution).
- **SC-008** : En mode `dry_run=True`, exactement 0 ligne business et 0 ligne audit sont écrites, mais 100% des SSE events sont émis avec préfixe `dry_run:` et le frontend affiche un bandeau « simulation ».
- **SC-009** : Couverture de tests ≥ 90 % sur les modules dispatcher, mutation_ctx, rate limiter, et ≥ 80 % sur les modules frontend `useChatStream` et `stores/chat`.
- **SC-010** : Le boot du backend échoue (exit code != 0) si un tool MUTATION est enregistré sans handler ou si un tool est enregistré sans catégorie — vérifiable par test pytest dédié.

## Assumptions

- F53 LangGraph core est mergée dans `main` et fournit déjà `app/agent/state.py` (avec `AgentState`, `ToolDispatchResult` MVP, `DispatchCategory` enum) ; F55 enrichit/réécrit `app/agent/nodes/dispatch_tool.py` et `app/agent/sse_bridge.py`.
- F14 fournit `tool_registry` et `payload_validator` ; F55 ajoute le champ `category` à `ToolDef` (extension non destructive, défauts cohérents pour les tools existants).
- F17 fournit les schémas Pydantic des tools de mutation ; F55 ajoute les handlers décorés.
- F39/F40/F41 sont mergées et exposent côté frontend `useChatBottomSheet`, `<VizRenderer>`, et `useChatEventBus`.
- L'EventBus front existe déjà côté F41 ; F55 ajoute juste le canal `entity_updated`.
- Redis n'est pas obligatoire en dev (in-memory bounded LRU acceptable single-worker) mais doit être documenté pour multi-worker prod.
- L'authentification chat assure que `app.current_account_id` est SET dans la session DB avant tout dispatch (cf. middleware F02).
- La table `tool_call_log` existe (créée par F14) et peut accueillir les nouvelles colonnes via Alembic.
- Tests E2E backend dominants en pytest+httpx (cohérent avec F53), 2 specs Playwright pour valider la chaîne UI complète (chat → bottom sheet → mutation visible).
- Le frontend `composables/useChatStream.ts` et `stores/chat.ts` existent et sont enrichis (F41 → F55) pour consommer les nouveaux events SSE.
- F54 (agent-context-builder) tourne en parallèle ; F55 ne touche pas `nodes/build_context.py` ni `nodes/recall_memory.py` ni le module `app/agent/context/*`. Si F54 modifie `app/main.py`/`app/config.py`/`pyproject.toml`, F55 fait des ajouts seulement (jamais de modif des lignes existantes).
- LLM model unchanged : OpenRouter `minimax-m2.7` via `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` ; embeddings Voyage `voyage-3.5` (1024 dim).
- Hosting EU/Afrique de l'Ouest uniquement (P. Souveraineté constitution).
