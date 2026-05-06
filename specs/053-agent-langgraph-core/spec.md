# Feature Specification: Agent LangGraph Core (orchestration backend câblée)

**Feature Branch**: `053-agent-langgraph-core`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "F53 — Phase H Agent Hardening — racine. Remplacer le proxy LLM brut de F13 par une machine d'état LangGraph qui orchestre tous les composants déjà livrés (F13 chat, F14 tool-use validation, F18 memory, F19 skills, F21 skills MVP). Brancher chat/api.py POST /messages sur l'agent. Sans cette feature, F13–F21 restent des bibliothèques inertes."

## Clarifications

### Session 2026-05-06

- Q: Comment gérer les tables de checkpoint LangGraph (Alembic ou setup() de la lib) ? → A: Déléguer à LangGraph `PostgresSaver.setup()` au boot ; aucune migration Alembic ne touche aux tables LangGraph. La migration Alembic créée par F53 ne porte que sur `agent_run` et `agent_run_step`. À documenter dans `backend/alembic/README.md`.
- Q: Comment garantir l'isolation tenant sur les checkpoints LangGraph ? → A: Utiliser un `thread_id` composite `"{account_id}:{conv_uuid}"`. Le runner valide que le préfixe correspond bien à l'`account_id` de la session avant tout usage du checkpointer (pas de RLS native sur tables LangGraph).
- Q: Comportement attendu sur timeout LLM ? → A: Annulation propre — `agent_run.status='timeout'`, aucun message assistant tronqué persisté, SSE fermé proprement, pas de retry automatique côté backend (l'utilisateur peut renvoyer manuellement).
- Q: Stratégie de concurrence sur le même thread (double-clic utilisateur) ? → A: Sérialisation via `pg_advisory_xact_lock(hashtext(thread_id))` côté runner. Le 2e tour attend le 1er ou retourne 409 Conflict si délai dépassé. Pas de dépendance Redis ajoutée.
- Q: Format des tests E2E pour la feature ? → A: Mix pytest E2E backend (httpx + ASGI, dominant) + 2 specs Playwright pour valider la chaîne UI complète (chat F41 → bottom sheet → mutation visible). Mocker l'LLM via une fixture `fakellm` pour la reproductibilité.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Création de projet via tool calls validés (Priority: P1)

Une PME utilisatrice écrit dans le chat « Crée un projet de panneaux solaires de 50 kWc ». L'assistant ESG Mefali ne se contente plus d'un texte libre : il identifie l'intention de mutation, détermine les champs manquants (montant, localisation, dates), affiche une bottom sheet de saisie (`ask_qcu` ou `show_form`), valide les réponses utilisateur, puis crée effectivement le projet en base et le rend visible dans l'écran « Profil → Projets » sans rechargement.

**Why this priority** : C'est la promesse produit centrale (« je parle à ESG Mefali, il agit »). Sans branchement effectif, l'assistant reste un chatbot inutile et tous les efforts F13–F21 sont gaspillés.

**Independent Test** : Avec le backend démarré et un compte PME authentifié, envoyer ce message via l'UI chat F41 → l'assistant déclenche la bottom sheet, l'utilisateur complète et valide → le projet apparaît dans la liste Projets et l'audit log contient une ligne `projet_create` avec `source_of_change=llm`.

**Acceptance Scenarios** :

1. **Given** une PME authentifiée sur la page Chat avec aucun projet existant, **When** elle envoie « Crée un projet de panneaux solaires de 50 kWc » et complète la bottom sheet (montant 25M FCFA, Abidjan, démarrage 2026-09), **Then** un projet est créé en base avec `account_id` correct, l'audit log enregistre la mutation avec `source_of_change=llm`, l'EventBus pousse l'item au store Pinia front et le projet est visible dans Profil → Projets sans rechargement.
2. **Given** une PME qui interrompt la saisie (clic « Annuler » sur la bottom sheet), **When** elle ferme la bottom sheet, **Then** aucun projet n'est créé, aucune ligne audit n'est écrite, le tour de chat se termine par un message assistant neutre.
3. **Given** une PME qui réécrit librement « Finalement c'est 100 kWc » avant de valider, **When** la nouvelle valeur est soumise, **Then** la bottom sheet précédente est mise à jour ou re-générée et la création reflète la nouvelle valeur.

---

### User Story 2 — Analyse ESG avec mémoire et sourçage (Priority: P1)

Une PME demande « Quel est le score ESG attendu pour ma boulangerie ? ». L'assistant rappelle l'historique et les indicateurs déjà saisis, exécute le tool `recall_history`, charge les indicateurs récents, retourne un graphe radar (`show_radar_chart`), un texte d'analyse, et **chaque chiffre cité est rattaché à une source vérifiée** via `cite_source`.

**Why this priority** : Sans mémoire et sans sourçage, l'agent fait des hallucinations en cascade et viole l'invariant constitutionnel P1 (sourcing obligatoire). Les démos auprès des fonds (BOAD, GCF) reposent intégralement sur cette capacité.

**Independent Test** : Démarrer une session avec une PME ayant 3-4 indicateurs ESG déjà saisis lors de tours précédents, envoyer le message → vérifier que la réponse contient un radar viz, un texte de synthèse, et au moins un appel à `cite_source` pointant un `Source` au statut `verified`.

**Acceptance Scenarios** :

1. **Given** une PME avec un historique de chat existant et des indicateurs ESG saisis, **When** elle envoie le message d'analyse, **Then** l'assistant exécute en séquence `recall_history` → lit la mémoire → invoque `show_radar_chart` (avec données indicateurs) → produit un texte de réponse → ce texte cite au moins une source via `cite_source` pointant un `Source.status=verified`.
2. **Given** un chiffre cité sans source associée, **When** l'assistant tente d'émettre le message final, **Then** le payload est rejeté par le validateur (P1 invariant) et un retry est déclenché ou un fallback texte sobre est affiché.

---

### User Story 3 — Boucle Validate ↔ Retry sur hallucination (Priority: P1)

Le LLM invente un champ non listé dans le schéma (par ex. `severity: "critical"` qui n'est pas dans l'enum). L'agent ne propage pas cette hallucination : il rejette le tool call via Pydantic strict (`extra='forbid'`), renvoie l'erreur structurée au LLM, qui corrige son tool call, qui passe alors la validation et s'exécute correctement.

**Why this priority** : La fiabilité tool-use (Module 10 du brainstorming + invariant P9) est ce qui distingue ESG Mefali d'un chatbot grand public. Toutes les mutations DB en dépendent.

**Independent Test** : Mocker une réponse LLM contenant un champ illégal au premier appel et un payload valide au second → vérifier qu'un seul retry est consommé, que le tool call s'exécute, que le `tool_call_log` enregistre les deux tentatives.

**Acceptance Scenarios** :

1. **Given** une requête utilisateur qui devrait déclencher un tool call, **When** le LLM produit un premier payload invalide, **Then** une erreur Pydantic structurée est renvoyée au LLM dans un message tool, `retry_count` passe à 1, et un nouveau tour LLM est déclenché.
2. **Given** deux hallucinations consécutives sur le même tour, **When** la 3e tentative serait nécessaire, **Then** l'agent abandonne le tool call, affiche un fallback texte sobre (« Je n'arrive pas à formaliser cette action — peux-tu reformuler ? »), marque `agent_run.status='error'` et écrit `tool_call_log.status='validation_error'`.
3. **Given** une 1re tentative invalide puis une 2e valide, **When** la 2e passe la validation, **Then** le tool call s'exécute, `retry_count=1` est journalisé dans `agent_run`, et la séquence finale du chat est correcte.

---

### User Story 4 — Isolation multi-tenant stricte de l'agent (Priority: P1)

Une PME A authentifiée tente, via le chat, de manipuler une entité (projet, candidature, indicateur) appartenant à une PME B. L'agent ne doit jamais « voir » ni « toucher » cette entité, même si l'utilisateur fournit l'UUID exact. La réponse retournée doit être un 404 (« cette entité n'existe pas pour vous »), pas un 403.

**Why this priority** : C'est l'invariant constitutionnel P2 (RLS strict, cross-tenant → 404). Toute fuite cross-tenant est un incident de sécurité bloquant.

**Independent Test** : Créer deux comptes A et B, créer un projet `P_B` côté B, se connecter en A et envoyer « supprime le projet `<UUID-P_B>` » → vérifier que l'agent retourne un message neutre type « projet introuvable », qu'aucune mutation n'est tentée côté B, et que les logs tracent la tentative.

**Acceptance Scenarios** :

1. **Given** un compte A et un projet `P_B` du compte B, **When** A demande à l'agent une mutation sur `P_B`, **Then** l'agent répond comme si l'entité n'existait pas (404 logique), aucune ligne audit ne référence l'entité B et le `tool_call_log` est marqué `dispatch_error: not_found`.
2. **Given** la même tentative, **When** on inspecte la base de données, **Then** la session SQL utilisée par les nœuds de l'agent avait bien `app.current_account_id` égal à l'`account_id` de A pendant tout le tour.

---

### User Story 5 — Branchement effectif et rollback opérationnel (Priority: P1)

L'opérateur de production peut basculer instantanément entre le nouvel agent (mode `langgraph`, par défaut) et l'ancien proxy LLM (mode `raw`, fallback) via une variable d'environnement, sans rebuild ni migration. En mode `langgraph`, `POST /messages` invoque le runner LangGraph ; en mode `raw`, l'ancien `stream_assistant()` est utilisé tel quel.

**Why this priority** : L'agent est complexe et nouveau. Sans rollback simple, un incident en prod est ingérable et risque de stopper le chat pour tous les utilisateurs.

**Independent Test** : Démarrer le backend avec `LLM_AGENT_MODE=langgraph`, envoyer un message → vérifier qu'un nœud route est exécuté (trace `agent_run_step`). Redémarrer avec `LLM_AGENT_MODE=raw` → vérifier qu'aucun `agent_run` n'est créé et que la réponse est purement texte (pas de tool call).

**Acceptance Scenarios** :

1. **Given** le backend démarré en mode `langgraph` (défaut), **When** un message est envoyé, **Then** un row `agent_run` est créé, des rows `agent_run_step` apparaissent pour chaque nœud, et le SSE émis suit le protocole F13/F55.
2. **Given** le backend redémarré avec `LLM_AGENT_MODE=raw`, **When** un message est envoyé, **Then** aucun `agent_run` n'est créé, l'ancien `stream_assistant` produit un stream texte simple, et l'utilisateur reçoit une réponse minimale (pas de tools, pas de mutations).

---

### User Story 6 — Persistance et reprise après crash (Priority: P2)

Si l'instance backend redémarre au milieu d'un long échange (par ex. génération d'analyse complexe), l'état du graphe pour ce thread est récupérable depuis le stockage de checkpoints (PostgresSaver), permettant de reprendre la conversation au bon point sans perdre le contexte.

**Why this priority** : Améliore la robustesse et le debug. Pas indispensable pour le MVP fonctionnel mais critique pour la qualité perçue en prod.

**Independent Test** : Démarrer un échange, tuer le worker uvicorn pendant un nœud LLM, redémarrer, reprendre la conversation → vérifier que l'état (intent, contexte, mémoire) est restauré.

**Acceptance Scenarios** :

1. **Given** un thread en cours dont l'état est checkpointé, **When** le backend redémarre, **Then** l'état du graphe pour ce `thread_id` peut être lu via le checkpointer et utilisé pour la prochaine requête.
2. **Given** deux requêtes concurrentes sur le même thread (double-clic utilisateur), **When** elles atteignent le checkpointer en parallèle, **Then** l'une réussit, l'autre détecte le conflit et se retire proprement (pas d'état corrompu).

---

### User Story 7 — Tracing et observabilité (Priority: P2)

Chaque exécution de l'agent produit un trace structuré exploitable : un row `agent_run` par tour de chat (latence totale, statut, retries), N rows `agent_run_step` (un par nœud avec latence et compteurs token/tool calls). Cela alimente le dashboard ops (F60) et facilite le debug.

**Why this priority** : Indispensable pour exploiter l'agent en prod, mais le MVP fonctionnel peut commencer sans (logs stdout suffisent pour les premiers jours).

**Independent Test** : Exécuter 10 messages variés → la table `agent_run` contient 10 rows, `agent_run_step` en contient au moins 60-80 (8 nœuds × 10 tours, avec quelques retries). Une requête SQL par `thread_id` reconstitue la timeline.

**Acceptance Scenarios** :

1. **Given** un message envoyé qui parcourt tous les nœuds sans erreur, **When** l'exécution se termine, **Then** un row `agent_run` est écrit avec `status=ok`, latence totale, tokens, et un row `agent_run_step` par nœud avec sa latence individuelle.
2. **Given** un tour avec timeout LLM, **When** la limite `LLM_AGENT_TIMEOUT_S` est atteinte, **Then** `agent_run.status='timeout'`, le step concerné est tagué `status=timeout`, et la session SSE est fermée proprement.

---

### User Story 8 — Annulation côté client (Priority: P1)

L'utilisateur clique « Stop » dans le chat ou ferme l'onglet pendant la génération. Le backend détecte la déconnexion SSE, annule proprement le tour LangGraph (pas de message tronqué persisté), marque `agent_run.status='cancelled'` et libère les ressources.

**Why this priority** : Sans annulation propre, des messages assistant orphelins polluent l'historique et l'utilisateur voit des artefacts. Inclut aussi la prévention du gaspillage de tokens.

**Independent Test** : Simuler une coupure SSE après 1s sur un tour de 10s → vérifier qu'aucun message assistant complet n'est en DB, que `agent_run.status='cancelled'`, qu'aucun tool de mutation n'a été dispatché.

**Acceptance Scenarios** :

1. **Given** un tour LangGraph en cours de génération LLM, **When** le client ferme la connexion SSE, **Then** le runner détecte `asyncio.CancelledError`, marque `agent_run.status='cancelled'`, ne persiste aucun message assistant tronqué, et libère les ressources LLM.
2. **Given** la même annulation pendant un dispatch de mutation, **When** la mutation a déjà commencé en DB, **Then** la transaction est rollback (pas de mutation partielle), aucune ligne audit n'est écrite, et `agent_run.status='cancelled'`.

---

### Edge Cases

- **Drift du registre de tools** — un nouveau tool ajouté en F15/F16/F17 mais non référencé par le sélecteur F14 doit être détecté par un test d'intégration (« tous les tools du registry sont accessibles via au moins une combinaison intent×page »). Sinon il sera ignoré silencieusement.
- **Chaînage tool → re-call LLM** — pour `cite_source`, `search_source`, `recall_history`, le résultat est renvoyé au LLM dans un message tool puis un nouveau call LLM est déclenché (boucle bornée par `LLM_AGENT_MAX_RETRIES` pour éviter un loop infini).
- **Tool d'écriture qui échoue côté DB** (ex. constraint violation) — le dispatcher doit retourner une erreur structurée à l'agent, qui peut soit la réessayer (max 1 fois) soit afficher un fallback texte. Aucune mutation partielle n'est laissée.
- **LLM_AGENT_TIMEOUT_S dépassé** au milieu d'un nœud LLM — l'exécution est annulée proprement (cf. clarification Q3) : `agent_run.status='timeout'`, aucun message assistant tronqué persisté, message d'erreur clair envoyé au client (« la requête a pris trop de temps »). Pas de retry automatique côté backend ; l'utilisateur peut renvoyer la requête.
- **Compilation du graph qui échoue au boot** — le backend doit refuser de démarrer (`fail fast`), `/health/agent` retourne `langgraph_compiled=false`, et un log de niveau ERROR explique la cause.
- **Forme `intent=question_fermee`** — sélection forcée d'un tool `ask_*` ; si aucun tool `ask_*` n'est disponible (par ex. registry mal initialisé), fallback texte direct.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST exposer un module agent (chemin sous `backend/app/agent/`) qui définit une machine d'état (StateGraph) avec les nœuds `route`, `build_context`, `recall_memory`, `select_tools`, `call_llm`, `validate_payload`, `dispatch_tool`, `compose_response`, et compile cette machine une seule fois au démarrage.
- **FR-002** : Le système MUST définir un type `AgentState` strictement validé (Pydantic v2 avec `extra='forbid'`) couvrant les champs : identité (thread_id, account_id, user_id), entrée utilisateur (user_message, context_json), routing (intent), prompt (system_prompt), historique (messages), tools disponibles, réponse LLM, tool_calls, validations, dispatch_results, texte final, retry_count, errors.
- **FR-003** : Chaque nœud MUST être implémenté comme une fonction asynchrone pure prenant l'état complet et retournant un patch d'état partiel. Aucun nœud sauf `dispatch_tool` ne MUST écrire en DB ou émettre des effets externes.
- **FR-004** : Le nœud `route` MUST appeler le classifier d'intentions existant (Module orchestrator) et écrire l'intent dans l'état. Le branchement conditionnel MUST suivre la matrice : `{profilage, mutation, analyse}` → contexte complet ; `{aide, navigation, autre}` → contexte minimal ; `question_fermee` → forçage tool `ask_*`.
- **FR-005** : Le nœud `call_llm` MUST utiliser une intégration LLM via `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` (pas de hard-code), exposer la liste des tools courants au LLM, supporter `tool_choice` `auto` ou forcé, et streamer les chunks (texte ou tool call) au runner.
- **FR-006** : Le nœud `validate_payload` MUST exécuter la validation Pydantic stricte de chaque tool call via le validator F14. En cas d'erreur, MUST renvoyer un message tool d'erreur structurée au LLM et incrémenter `retry_count` ; au-delà de la limite (`LLM_AGENT_MAX_RETRIES`, défaut 2), MUST déclencher un fallback texte sobre et écrire `tool_call_log.status='validation_error'`.
- **FR-007** : Le nœud `dispatch_tool` MUST router selon la catégorie du tool : (a) `ask_*`/`show_*` → SSE event vers le frontend (pas d'exécution backend) ; (b) `update_*`/`create_*`/`delete_*` → exécution DB sous RLS, écriture audit log, SSE mutation ; (c) `cite_source`/`search_source`/`recall_history` → exécution puis re-injection du résultat dans une nouvelle itération `call_llm`.
- **FR-008** : Le système MUST exposer un runner `run_agent(...)` (point d'entrée du graph) qui orchestre `astream_events` et mappe les events natifs LangGraph vers le protocole SSE attendu par le frontend (F13/F55) et qui persiste les messages assistant finaux via le service `chat`. Conformément à la clarification Q1, **aucune migration Alembic** ne crée les tables LangGraph (`checkpoints*`) — elles sont créées par `setup()` de la lib au boot (cf. FR-010).
- **FR-009** : `chat/api.py:post_message` MUST appeler le runner agent quand `LLM_AGENT_MODE='langgraph'` (défaut) et conserver l'ancien `stream_assistant` quand `LLM_AGENT_MODE='raw'`. Le basculement MUST être instantané (pas de migration, pas de rebuild).
- **FR-010** : Le système MUST persister l'état des threads via un checkpointer PostgreSQL officiel (compatible LangGraph). Les tables du checkpointer MUST être créées par `setup()` de la lib au démarrage (pas de migration Alembic les versionnant). La migration Alembic produite par F53 ne MUST porter QUE sur `agent_run` et `agent_run_step`. Le système MUST gérer la concurrence sur le même `thread_id` via `pg_advisory_xact_lock(hashtext(thread_id))` ; en cas de second tour concurrent, le 2e attend le 1er (avec timeout) puis poursuit ou retourne un conflit.
- **FR-011** : Le système MUST tracer chaque exécution dans deux nouvelles tables append-only : `agent_run` (un row par tour : id, account_id, user_id, thread_id, started_at, completed_at, status enum {ok, error, timeout, cancelled}, total_latency_ms, total_tokens_in, total_tokens_out, retry_count, final_node, error_summary) et `agent_run_step` (un row par nœud : id, run_id, node_name, started_at, latency_ms, tokens_in, tokens_out, tool_calls_count, status, error). Ces deux tables MUST porter `account_id` et MUST être protégées par RLS.
- **FR-012** : Le système MUST gérer l'annulation côté client : sur déconnexion SSE ou `asyncio.CancelledError`, MUST marquer `agent_run.status='cancelled'`, MUST rollback toute transaction DB en cours, MUST n'écrire aucun message assistant tronqué, et MUST libérer les ressources LLM.
- **FR-013** : Tous les nœuds DB-touching MUST propager le contexte multi-tenant via le mécanisme de session existant (paramètre Postgres `app.current_account_id`). Un appel cross-tenant MUST se traduire par 404 (pas 403) — l'agent ne MUST jamais retourner d'indice sur l'existence d'une entité d'un autre tenant. L'isolation tenant des checkpoints LangGraph MUST être assurée par l'usage d'un `thread_id` composite `"{account_id}:{conv_uuid}"` ; le runner MUST valider que le préfixe correspond à l'`account_id` de la session avant tout accès au checkpointer.
- **FR-014** : Le système MUST exposer un endpoint de santé spécifique à l'agent (par ex. `/health/agent`) retournant : `ok`, `langgraph_compiled` (bool), `postgres_checkpointer` (bool), `llm_reachable` (bool). Le démarrage backend MUST échouer si la compilation du graph échoue.
- **FR-015** : Le système MUST supporter via configuration d'environnement : `LLM_AGENT_MODE` ∈ {`langgraph`, `raw`} (défaut `langgraph`), `LLM_AGENT_MAX_TOOLS` (défaut 10), `LLM_AGENT_MAX_RETRIES` (défaut 2), `LLM_AGENT_TIMEOUT_S` (défaut 30.0), `LLM_AGENT_TRACE` ∈ {`off`, `db`, `db+stdout`} (défaut `db`).
- **FR-016** : Tout chiffre ESG/financier produit par l'agent MUST être lié à un `Source.status='verified'` via un appel `cite_source` préalable ; sinon, le validator MUST rejeter le message final (P1 invariant). Si aucune source n'est disponible, l'agent MUST utiliser `flag_unsourced` ou refuser de répondre.
- **FR-017** : Le runner MUST limiter à 1–2 skills par tour (P9 invariant). Si plusieurs skills correspondent à l'intent, le sélecteur MUST en prendre le sous-ensemble pertinent (`LLM_AGENT_MAX_TOOLS` plafonne aussi le nombre de tools exposés au LLM).
- **FR-018** : Le système MUST fournir une suite de tests automatisés (cf. clarification Q5) couvrant : route conditionnelle, retry après hallucination Pydantic, dispatch SSE-only (`ask_*`/`show_*`), dispatch DB+audit (`update_*`/`create_*`/`delete_*`), fallback après dépassement retry, isolation cross-tenant (404), annulation côté client, mode raw rollback, healthcheck, concurrence sur même thread (advisory lock), reprise depuis checkpoint après redémarrage. Format : (a) pytest E2E backend (httpx + ASGI) pour les cas dominants, (b) 2 specs Playwright pour la chaîne UI complète (chat F41 → bottom sheet → mutation visible côté Profil), (c) fixture `fakellm` mockant le LLM pour idempotence (NFR-002). Couverture cible ≥ 85 % sur `backend/app/agent/`.

### Key Entities *(include if feature involves data)*

- **AgentState** : la structure de données circulant dans le graphe pendant un tour de chat. Inclut : identité multi-tenant, message utilisateur, intent classifié, prompt système, messages historiques, tools disponibles, réponse LLM courante, tool calls bruts/validés, résultats de dispatch, texte final, compteur de retry, erreurs accumulées. **Pas persistée directement** : c'est un objet de transit ; sa persistance passe par le checkpointer LangGraph (snapshot d'état pour resume).
- **AgentRun** : trace d'une exécution complète du graph. Attributs : identifiant, identité multi-tenant (account_id, user_id, thread_id), timestamps début/fin, statut final (ok/error/timeout/cancelled), latence totale, tokens cumulés (in/out), nombre de retries, nœud final atteint, résumé d'erreur. **Append-only**.
- **AgentRunStep** : trace d'une exécution de nœud individuel. Attributs : identifiant, run_id (FK), nom du nœud, timestamps, latence, tokens (in/out), nombre de tool calls émis, statut, erreur éventuelle. **Append-only**.
- **AgentCheckpoint** (table gérée par la lib checkpointer) : snapshot opaque de l'état d'un thread, indexé par `thread_id`. Permet la reprise après crash. La gestion (création, purge) est déléguée à la lib externe pour limiter la dette de schéma.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME peut, via le chat, créer un projet en moins de 90 secondes (envoi message → bottom sheet → validation → projet visible dans Profil), sans rechargement et avec ligne audit `source_of_change=llm`.
- **SC-002** : Sur un panel de 50 messages d'analyse ESG (golden set F35), 100 % des chiffres cités dans les réponses sont rattachés à au moins une source `verified` (sourçage P1 enforcé). Les messages non sourcés sont filtrés ou rejetés.
- **SC-003** : Sur 100 tool calls générés par le LLM dont 30 % volontairement défectueux (test d'injection), 95 % des défauts sont corrigés en 1 seul retry, ≤ 5 % aboutissent au fallback texte, 0 % laissent passer un payload invalide en DB.
- **SC-004** : Le démarrage du backend (boot complet incluant compilation du graph et setup checkpointer) se fait en moins de 5 secondes en environnement local. `/health/agent` retourne tout vert en moins de 100 ms après boot.
- **SC-005** : Test cross-tenant : sur 50 tentatives d'accès cross-tenant variées (UUID corrects d'un autre compte, références indirectes), 100 % retournent 404 logique. Aucune ligne audit ne référence l'entité de l'autre tenant. Aucune fuite SQL n'est observée dans les logs.
- **SC-006** : Sur 100 tours de chat normaux, la latence ajoutée par le pipeline de l'agent (hors appel LLM principal) est inférieure à 500 ms en p95.
- **SC-007** : Annulation : sur 20 simulations de coupure SSE pendant la génération, 100 % marquent `agent_run.status='cancelled'` et 0 message assistant orphelin n'est trouvé en base.
- **SC-008** : Bascule rollback : changer `LLM_AGENT_MODE` de `langgraph` à `raw` (ou inverse) prend effet au prochain tour de chat sans redémarrage forcé. Les deux modes restent fonctionnels (CI exécute les deux jeux de tests).
- **SC-009** : La couverture de tests automatisés sur le module agent (`backend/app/agent/`) atteint ≥ 85 % de lignes couvertes, mesurée par l'outil de coverage existant.
- **SC-010** : Sur un échantillon de 10 threads en cours, 100 % peuvent être repris après redémarrage backend (état restauré depuis le checkpointer).

## Assumptions

- Une convention de nommage de chemin sous `backend/app/agent/` (avec sous-dossier `nodes/`) est adoptée pour matérialiser l'architecture du graphe en code.
- Le module agent réutilise les composants déjà livrés : classifier d'intentions et validator (F14), tool registry (F15/F16/F17), service mémoire (F18), skills loader (F19), prompts (F19) — il n'introduit pas de logique métier supplémentaire.
- La base `Source` (F03) et le service `cite_source` sont supposés déployés et alimentés (référence aux sources `verified` BOAD-2024, ADEME, etc.).
- Le frontend chat (F41) consomme déjà le protocole SSE (event types `token`, `tool_invoke`, `mutation`, `error`, `done`) ; F53 émet ces events sans en ajouter de nouveaux. Les nouveaux events spécifiques (par ex. `validation_retry`) seront introduits par F55.
- Les tables `tool_call_log` et `audit_log` existent déjà (F04 et F14) ; F53 écrit dedans mais ne change pas leur schéma.
- Le routeur d'admin et les endpoints existants (Profil, Projets) consomment déjà les EventBus front pour rafraîchir leurs vues sans rechargement (F41).
- L'identité « ESG Mefali » est figée par F54 (system prompt dynamique) ; F53 expose simplement un point d'extension (`state.system_prompt`) que F54 alimentera.
- Le routage SSE et la cohérence des events (token/mutation/tool_invoke) seront finalisés par F55 — F53 se contente d'émettre des events conformes au protocole F13 actuel et expose les hooks nécessaires à F55.
- L'enforcement strict du sourçage (P1) est partagé avec F56 : F53 exécute le validator et le `cite_source`, F56 ajoute la post-vérification fine et le bandeau « non sourcé ».
- Les tests d'évaluation continue (F58) consomment les traces `agent_run`/`agent_run_step` pour mesurer la qualité — F53 produit ces traces mais ne porte pas l'évaluation.
- L'hébergement reste UE/UEMOA (pas USA) — aucune donnée PME ne sort de l'infrastructure backend, pas même via les checkpoints (qui restent en Postgres local au déploiement).

## Dependencies

- **F13 — Chat backend** : fournit `chat/api.py`, `chat/service.py`, `chat/llm_stream.py` (à brancher), schémas SSE.
- **F14 — LangGraph routing & validation** : fournit `orchestrator/intent_classifier.py`, `orchestrator/payload_validator.py`, `orchestrator/retry_policy.py`, `orchestrator/tool_selector.py`.
- **F15 / F16 / F17 — Tools** : fournissent les tools `ask_*`, `show_*`, `update_*`, `create_*`, `delete_*` avec leurs schemas Pydantic.
- **F18 — Memory** : fournit le service `recall_history` et la table `chat_memory`.
- **F19 — Skills loader** : fournit le moteur de fusion prompt + tools.
- **F21 — Skills MVP** : fournit les playbooks ESG/scoring/dossier.
- **F03 — Source** : fournit le tool `cite_source` et la table `sources`.
- **F04 — Audit** : fournit le service d'écriture audit append-only.

## Out of Scope (MVP)

- Routage multi-modèle (Haiku pour le classifier, Sonnet pour l'analyse) — un seul modèle MVP.
- Streaming partiel des arguments de tool calls (tool_call_chunks) — on attend la fin du tool call pour valider/émettre.
- Sub-graphs LangGraph (un graph par skill) — un seul graph, les skills paramètrent prompt/tools mais pas la topologie.
- Compaction asynchrone des checkpoints (job de purge automatique) — laisser grossir, purge manuelle.
- Cache sémantique des réponses agent (réutiliser une réponse pour une question quasi-identique) — post-MVP.
- Identité « ESG Mefali » figée + résistance aux jailbreaks → F54/F58.
- Bandeau « non sourcé » côté front + post-vérification fine du sourçage → F56.
- Mémoire long-terme RAG pgvector + compaction → F57.
- Eval continue + golden set 50-100 cas + kill-switch → F58.

## Shared Write Zones (concurrent feature notice)

Les chemins suivants sont touchés par cette feature et le seront aussi par d'autres features de la Phase H (F54-F58). Les features suivantes doivent considérer ces chemins comme « zone d'écriture partagée » et coordonner via revue de code :

- `backend/app/main.py` — branchement du router agent / healthcheck
- `backend/app/config.py` — nouvelles variables `LLM_AGENT_*`
- `backend/app/chat/api.py` — basculement langgraph/raw
- `backend/app/chat/llm_stream.py` — préservé (mode raw) mais voisin de l'agent
- `backend/app/agent/` — nouveau module (initié par F53 ; étendu par F54 system prompt, F55 SSE, F56 sourcing, F57 memory, F58 guardrails)
- `backend/alembic/versions/` — migrations agent_run/agent_run_step (F53 seulement pour cette phase)
- `backend/pyproject.toml` — nouvelles dépendances (LangGraph, langchain-core, langchain-openai, langgraph-checkpoint-postgres) — F53 only
