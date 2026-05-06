# Feature Specification: Agent Memory & Long-term Recall (LangGraph + pgvector RAG)

**Feature Branch**: `057-agent-memory-rag`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "F57 — Agent Memory & Long-term Recall. Phase H — Agent Hardening. Dépend de F18 (memory recent + recall_history tool), F53 (LangGraph core), F54 (Context builder), F55 (Tool dispatch). Livrer un nœud LangGraph `recall_memory` à 2 niveaux (court terme = 15 derniers messages chronologiques, long terme = top-K cosine sur embeddings Voyage 1024 dim via pgvector), un tool `recall_history(query)` invocable par le LLM, une compaction async des threads >100 messages (résumé < 500 tokens), une table `agent_entity_memory` partagée par account, un endpoint `GET/DELETE /me/chat/threads/{id}/memory` enrichi (forget RGPD synchrone), un anti-fuite cross-thread testé, un cache embedding par tour, et le tracing complet des recalls."

## Clarifications

### Session 2026-05-06

- Q: Quel storage pour les logs de recall (FR-012) — table SQL dédiée, log structuré JSON, ou hybride ? → A: Table SQL dédiée `recall_log(id, agent_run_id, thread_id, account_id, recall_type, query_hash, top_k, top_scores JSONB, latency_ms, created_at)` avec RLS par account_id ; rétention défaut 90 jours via env `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`. Cohérent P2 (RLS) et P3 (audit-grade) ; permet à F60 d'agréger en SQL sans dépendance externe.
- Q: Quel scope/TTL pour le cache embedding (FR-011) ? → A: Cache embedding scope = un tour (un cycle d'exécution du graph LangGraph). Implémentation : dict in-state attaché à `AgentState` en champ transient, garbage-collected à la fin du tour. Évite fuites mémoire process-wide et complexité de cache invalidation cross-run.
- Q: Comment lier `agent_entity_memory` à un thread pour le forget RGPD (FR-008) ? → A: `agent_entity_memory` N'EST PAS purgée par `DELETE /me/chat/threads/{id}/memory` car elle représente un fait account-wide (alimentée par toutes les mutations, pas thread-spécifique). Le DELETE purge uniquement embeddings + summary + last_compacted_at du thread. Pour effacer entity_memory, l'utilisateur passera par un endpoint séparé "Mes données" (F32) post-MVP.
- Q: Quel scope frontend pour F57 (MemoryBadge enrichi, bouton F32) ? → A: F57 livre BACKEND complet (endpoints GET/DELETE memory, recall_memory node, compaction, entity_memory, dispatcher hooks) + 1 test E2E Playwright minimal (`frontend/tests/e2e/memory.spec.ts`) qui appelle directement les endpoints via fetch et vérifie le contrat. Aucune modification de `MemoryBadge.vue` ni de la page F32 dans F57.
- Q: Politique de compaction au-delà de 100 messages (FR-006) ? → A: Chunks fixes par batch de 50, summary REMPLACÉ à chaque compaction (pas cumulatif). À 100 msgs → compact 1-50 et `summary` écrit ; à 150 msgs → compact 51-100 et `summary` remplacé (le précédent summary 1-50 est perdu mais les messages bruts restent en DB pour audit P3). Hierarchical summaries (résumés de résumés) explicitement out-of-scope MVP.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Recall automatique court+long terme au début du tour (Priority: P1)

Une PME a déjà tenu un long thread de 60 messages couvrant plusieurs sujets (panneaux solaires 50 kWc, scooters électriques, audit ESG B Corp). Vingt tours plus tard, elle écrit « Reprends ce qu'on disait sur le solaire 50 kWc, j'ai des chiffres à mettre à jour ». L'agent, avant de planifier sa réponse, charge automatiquement les 15 derniers messages chronologiques (court terme) et fait une cosine search sur les embeddings du thread (long terme), excluant ces 15 derniers, retient les 3 messages les plus pertinents au-dessus du seuil de similarité, les insère en tête du contexte LLM avec un préfixe explicite « Souvenirs pertinents d'échanges précédents », et répond avec cohérence en citant les chiffres précédemment mentionnés.

**Why this priority** : C'est le cœur de la valeur produit « l'agent se souvient ». Sans recall automatique, l'agent répète ses questions à chaque tour et perd l'utilisateur sur les longs threads. Cohérence avec P8 (DB source de vérité, contexte LLM est du transient).

**Independent Test** : Créer un thread avec 50 messages dont 5 mentionnent explicitement « solaire 50 kWc » au début du thread, puis envoyer « Reprends ce qu'on disait sur le solaire 50 kWc » → vérifier que (1) le contexte LLM transmis contient bien les 15 derniers messages + 3 messages anciens pertinents préfixés, (2) la réponse LLM cite des chiffres du début du thread.

**Acceptance Scenarios** :

1. **Given** un thread de 50 messages avec des mentions « solaire 50 kWc » uniquement dans les 30 premiers, **When** la PME envoie « Reprends ce qu'on disait sur le solaire 50 kWc », **Then** le contexte LLM contient les 15 derniers messages chronologiques + un bloc préfixé « Souvenirs pertinents d'échanges précédents » avec 3 messages anciens dont la similarité cosine ≥ 0.7, et la réponse cite des éléments de ces messages anciens.
2. **Given** un thread de 10 messages (< 15), **When** la PME envoie un nouveau message, **Then** le recall long terme N'EST PAS déclenché (pas d'appel embedding), seuls les messages disponibles sont chargés en contexte.
3. **Given** un thread de 100 messages mais aucun message ancien au-dessus du seuil de similarité, **When** la PME envoie une requête, **Then** seuls les 15 derniers messages sont chargés et aucun bloc « Souvenirs pertinents » n'est inséré.

---

### User Story 2 — Tool `recall_history(query)` invocable par le LLM (Priority: P1)

L'agent répond à une PME et réalise en cours de raisonnement qu'il a besoin d'une information précise (« quel était le budget mentionné pour la rénovation ? »). Le LLM invoque explicitement le tool `recall_history(query="budget rénovation")` avec un `limit=5`. Le dispatcher (F55) exécute le handler READ qui fait un cosine search dans le thread courant, retourne les 5 messages les plus pertinents en `ToolMessage` ré-injecté au tour suivant.

**Why this priority** : Le recall automatique (US1) couvre 80 % des cas, mais le LLM doit pouvoir aussi chercher explicitement quand le recall auto n'a rien remonté ou quand il a besoin d'une recherche ciblée. Cohérent avec P9 (tool-use strict).

**Independent Test** : Forcer un prompt système qui suggère l'usage de `recall_history`, observer que le LLM produit le tool call avec arguments validés, le dispatcher l'exécute, et le résultat est ré-injecté en `ToolMessage` au tour suivant.

**Acceptance Scenarios** :

1. **Given** un thread avec des messages anciens mentionnant un budget, **When** le LLM invoque `recall_history(query="budget", limit=5)`, **Then** le dispatcher F55 valide le payload (Pydantic strict, `query` non vide ≤ 256 chars, `limit` entre 1 et 10), exécute le cosine search scoping `thread_id`+`account_id`, retourne 5 messages au format `ToolMessage` au tour suivant.
2. **Given** un appel `recall_history(query="x")` avec un `query` vide, **When** la validation Pydantic s'exécute, **Then** le tool call est rejeté en amont avec une erreur structurée et un retry max 2 fois (cohérent P9).
3. **Given** le tool est invoqué dans le thread A par l'agent du compte X, **When** le cosine search s'exécute, **Then** aucun résultat de thread B (même compte) ni d'un autre compte ne peut apparaître (anti-fuite cross-thread, voir US7).

---

### User Story 3 — Memory snapshot endpoint enrichi (Priority: P1)

Une PME ouvre la page chat. Le badge `MemoryBadge.vue` (déjà livré) affiche « 47 messages, 32 indexés, résumé disponible ». La PME clique pour voir le détail. Le frontend appelle `GET /me/chat/threads/{id}/memory` et reçoit un payload structuré indiquant le nombre total de messages, le nombre de messages récents (15), le résumé compaction (si présent), la date de dernière compaction, la liste d'entités référencées (entreprise, projets, candidatures cités dans le thread).

**Why this priority** : L'utilisateur doit savoir « ce que l'agent retient de moi » — fondamental pour la confiance et la conformité RGPD. Sans cette transparence, le forget RGPD (US6) n'a pas de point d'entrée naturel.

**Independent Test** : Avec un thread connu (50 messages, déjà compacté), appeler `GET /me/chat/threads/{id}/memory` et vérifier que tous les champs du contrat sont remplis (total_messages, recent_messages_count, summary, vector_index_size, last_compaction_at, entities_referenced).

**Acceptance Scenarios** :

1. **Given** un thread de 50 messages dont 25 ont un embedding indexé et qui a été compacté il y a 2 jours, **When** la PME appelle `GET /me/chat/threads/{id}/memory`, **Then** la réponse contient `{total_messages: 50, recent_messages_count: 15, summary: "<texte>", vector_index_size: 25, last_compaction_at: "<iso>", entities_referenced: [...]}`.
2. **Given** un thread sans compaction encore, **When** l'endpoint est appelé, **Then** `summary: null` et `last_compaction_at: null` sans erreur.
3. **Given** une PME du compte A qui tente d'appeler `GET /me/chat/threads/{id}/memory` pour un thread du compte B, **When** la requête arrive, **Then** la réponse est 404 (P2 RLS, cross-tenant retourne 404 pas 403).

---

### User Story 4 — Forget RGPD synchrone (Priority: P1)

Une PME, depuis la page « Mes données » (F32, livrée ailleurs), clique « Effacer la mémoire long terme » sur un thread. Le frontend appelle `DELETE /me/chat/threads/{id}/memory`. L'endpoint exécute synchroniquement la purge des embeddings du thread et du résumé de compaction (`summary`, `last_compacted_at`) — SANS supprimer les messages eux-mêmes (conservés pour audit log P3) NI les `agent_entity_memory` (faits account-wide, voir Clarification Q3 ; un endpoint séparé sera livré post-MVP). L'API retourne 200 quand c'est effectivement fait. Au tour suivant, l'agent ne voit que les 15 derniers messages bruts.

**Why this priority** : Droit à l'oubli RGPD — invariant légal non négociable. Doit être synchrone (pas un job background) pour que l'utilisateur sache que c'est fait au moment du clic.

**Independent Test** : Sur un thread avec 50 messages indexés et compactés, appeler `DELETE /me/chat/threads/{id}/memory`, vérifier (1) la réponse 200 synchrone, (2) `chat_thread.summary IS NULL`, (3) `chat_thread.last_compacted_at IS NULL`, (4) tous les `chat_message.embedding IS NULL` pour ce thread, (5) les messages bruts (`chat_message.content`) intacts en DB, (6) `agent_entity_memory` du compte INTACTE (pas purgée par cet endpoint, voir Clarification Q3), (7) une ligne audit `{action: 'memory_forget', thread_id, user_id, ts}` est écrite.

**Acceptance Scenarios** :

1. **Given** un thread avec 50 messages indexés et compactés, **When** la PME appelle `DELETE /me/chat/threads/{id}/memory`, **Then** l'endpoint répond 200 dans la même requête HTTP (synchrone), tous les embeddings du thread sont à NULL, `summary` est effacé, `last_compacted_at` est NULL, `chat_message.content` reste intact pour audit P3, et `agent_entity_memory` du compte est INCHANGÉE (purge dédiée ailleurs, post-MVP).
2. **Given** un thread déjà vide (rien à purger), **When** la PME appelle l'endpoint, **Then** la réponse est 200 idempotent et aucune erreur.
3. **Given** une PME du compte A qui appelle l'endpoint pour un thread du compte B, **When** la requête arrive, **Then** la réponse est 404 (P2 RLS), aucune purge n'est effectuée.
4. **Given** une mutation business antérieure (`update_company_profile`) liée à un fait extrait du thread, **When** la PME efface la mémoire du thread, **Then** la table business `entreprise` n'est PAS modifiée (forget RGPD partiel : la mémoire conversationnelle est purgée mais pas les entités business). Cette frontière est documentée dans la page « Mes données ».

---

### User Story 5 — Anti-fuite cross-thread et cross-account (Priority: P1)

Une PME a deux threads distincts : Thread A « panneaux solaires » et Thread B « scooters électriques ». Dans Thread B, elle écrit « Rappelle-moi ce qu'on disait sur les panneaux ». L'agent fait un recall (auto et/ou tool) scope strictement `thread_id=B`+`account_id=X`. Aucun message du Thread A n'apparaît dans le contexte. L'agent répond honnêtement « Je ne trouve rien sur les panneaux dans CE thread, voulez-vous que je crée un nouveau thread ou que je reprenne le thread précédent ? ».

**Why this priority** : Privacy par thread non négociable. L'utilisateur peut volontairement séparer ses sujets. Cohérent avec P2 (RLS) mais étend le scoping AU THREAD pas seulement à l'account.

**Independent Test** : Setup deux threads d'un même compte avec des contenus distincts, lancer un recall dans Thread B sur un sujet présent uniquement dans Thread A, vérifier que zéro message de A n'apparaît dans la réponse ni dans le tracing du recall.

**Acceptance Scenarios** :

1. **Given** Thread A (account X) avec 10 messages sur "panneaux solaires" et Thread B (account X) sans aucune mention solaire, **When** la PME dans Thread B envoie « Rappelle ce qu'on disait sur les panneaux » et le recall auto + tool s'exécute, **Then** zéro message du Thread A n'apparaît dans le contexte LLM ni dans la réponse.
2. **Given** Thread B account X et Thread C account Y, même utilisateur usurpateur, **When** un appel API tenterait de scoper sur Thread C depuis le compte X, **Then** la requête est refusée par RLS et retourne 404 logique.
3. **Given** la table `agent_entity_memory` partagée par account (`Entreprise` du compte X), **When** une PME du même account commence un nouveau Thread D, **Then** l'entity_memory est accessible et utilisée pour cadrer le contexte (légitime, scope=account), mais aucun message brut d'un autre thread n'est inclus.

---

### User Story 6 — Compaction async des threads ≥ 100 messages (Priority: P2)

Un thread atteint 100 messages. Après la 100e insertion, un job `BackgroundTasks` FastAPI s'enclenche (non bloquant pour l'utilisateur) qui demande au LLM de générer un résumé compact (< 500 tokens) couvrant les messages 1-50, l'enregistre dans `chat_thread.summary`, met à jour `chat_thread.last_compacted_at`, marque les messages 1-50 avec `compacted=True` (gardés en DB pour audit, exclus du recall futur). Au prochain tour, le contexte LLM utilise `summary` + 15 derniers messages, sans charger les 50 messages compactés.

**Why this priority** : Sans compaction, les threads très longs feront exploser la latence pgvector, le coût LLM (contexte trop gros) et la qualité (signal noyé). P2 (pas P1) car les threads ≥ 100 messages restent rares au début.

**Independent Test** : Insérer 100 messages dans un thread, vérifier qu'un BackgroundTask s'enclenche (log + état mémoire), attendre la fin (< 5 s), vérifier `chat_thread.summary` non null < 500 tokens, vérifier les 50 premiers messages avec `compacted=True`, vérifier que le tour suivant utilise le summary.

**Acceptance Scenarios** :

1. **Given** un thread à 99 messages, **When** la 100e insertion s'exécute, **Then** un `BackgroundTask` `compact_thread(thread_id)` est enqueué et la réponse au user n'est pas bloquée.
2. **Given** la compaction terminée, **When** un nouveau tour démarre, **Then** le contexte LLM contient `summary` + 15 derniers messages, et les 50 premiers messages (compacted=True) ne sont ni chargés ni considérés pour le recall long terme.
3. **Given** deux requêtes concurrentes qui déclencheraient compaction, **When** elles tentent d'écrire `summary`, **Then** un lock optimiste sur `chat_thread.last_compacted_at` empêche le double-compact et seul le premier passe.

---

### User Story 7 — Persistance résumée par entité (Priority: P2)

Une PME tient plusieurs threads où elle parle de son entreprise (chiffre d'affaires, secteur, effectif). Indépendamment du thread courant, l'agent doit avoir un « fait stable » sur l'entreprise. La table `agent_entity_memory(account_id, entity_type='Entreprise', entity_id, summary)` stocke un résumé ≤ 800 tokens de tout ce que l'agent sait sur l'entreprise. Quand l'agent invoque `update_company_profile` via le dispatcher F55, un `BackgroundTask` `update_entity_memory(account_id, entity_type, entity_id)` est enqueué pour rafraîchir le summary.

**Why this priority** : Améliore drastiquement la cohérence cross-thread mais n'est pas bloquant. P2.

**Independent Test** : Créer un thread, invoquer `update_company_profile(secteur="C10.71")`, attendre 30 s, vérifier que `agent_entity_memory(Entreprise, ...).summary` contient une mention du nouveau secteur.

**Acceptance Scenarios** :

1. **Given** un agent qui invoque `update_company_profile(secteur="C10.71")` via le dispatcher, **When** la mutation aboutit, **Then** un `BackgroundTask update_entity_memory(account_id, 'Entreprise', entity_id)` est enqueué et < 30 s plus tard, `agent_entity_memory(...).summary` mentionne le nouveau secteur et `version` est incrémenté.
2. **Given** une `agent_entity_memory(Entreprise, ...)` existante, **When** un nouveau Thread D commence, **Then** son contexte initial peut inclure le summary entity (logique : « ce que je sais de cette entreprise »), mais aucun message brut d'un autre thread n'est inclus.
3. **Given** un projet supprimé (`delete_project`), **When** la suppression aboutit, **Then** un `BackgroundTask` purge `agent_entity_memory('Projet', project_id)` (drift entity memory évité).

---

### User Story 8 — Cache embedding et tracing (Priority: P2)

Lors d'un tour, l'embedding de la `user_message` du tour est calculé une seule fois et réutilisé à la fois par le recall_memory automatique (US1) et par d'éventuels appels `recall_history` du LLM dans le même tour. Chaque recall (auto ou tool) est loggué avec `agent_run_id, recall_type ('auto'|'tool'), query_hash, top_k, top_scores, latency_ms`.

**Why this priority** : Optimisation coût Voyage et observabilité pour F60. P2.

**Independent Test** : Tour avec recall auto + 1 tool `recall_history` → vérifier qu'un seul appel Voyage par tour est effectué (mock spy). Vérifier deux lignes `recall_log` (auto + tool) avec `agent_run_id` identique.

**Acceptance Scenarios** :

1. **Given** un tour qui déclenche US1 puis le LLM invoque `recall_history(query=même_user_message)`, **When** les deux recalls s'exécutent, **Then** un seul appel Voyage embedding est effectué (cache mémoire par `agent_run_id`+hash query).
2. **Given** un tour avec recall auto + tool, **When** les recalls s'exécutent, **Then** deux lignes `recall_log` sont écrites avec `recall_type='auto'` et `recall_type='tool'`, partageant le même `agent_run_id`.

---

### Edge Cases

- **Thread vide ou nouveau** : 0 message → recall_memory ne tente aucun embedding ni cosine search ; retourne contexte vide sans erreur.
- **Voyage API indisponible** : embedding échoue → fallback mode dégradé : seuls les 15 derniers messages chronologiques sont chargés ; un log warning est émis ; le tour LLM continue sans recall long terme.
- **pgvector indisponible** : la requête cosine échoue → fallback identique au point précédent ; aucun crash 500 visible utilisateur.
- **Embedding de message manquant** (background task pas encore terminé) : le message est exclu du recall long terme mais reste visible dans les 15 derniers chronologiques.
- **Thread dépassant 1000 messages** : hors-scope MVP (hierarchical summaries) ; comportement attendu : compaction successive par tranches de 50, summary se met à jour au-delà des messages 1-50, 51-100, etc., en mode flat (post-MVP : summary de summaries).
- **Forget RGPD pendant compaction en cours** : si `DELETE /memory` arrive pendant qu'un `BackgroundTask` de compaction tourne sur le même thread, le DELETE doit acquérir le lock optimiste, attendre ou refuser proprement, jamais corrompre l'état.
- **Cross-thread recall manuel (utilisateur le demande explicitement)** : non supporté MVP — l'agent répond « Je n'ai accès qu'à CE thread, voulez-vous reprendre l'autre thread ? ».
- **Account X tente DELETE /memory thread Y du compte Z** : 404 logique (P2 RLS), aucune purge.
- **Race compaction + insertion** : 100e message insère et 101e arrive avant fin compaction → 101e message reste indexé normalement, compaction continue ; pas de double-compact grâce au lock.
- **Embedding dimension mismatch** (config Voyage modifiée) : dim attendue 1024, mismatch détecté → fail-safe au boot backend (config validation), refuse de démarrer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST exposer un nœud LangGraph `recall_memory` qui charge les 15 derniers messages chronologiques (`role IN ('user', 'assistant')`, `compacted=False`) du thread courant ET, si le thread compte > 15 messages, exécute un cosine search via pgvector pour retenir top-K=3 messages anciens au-dessus du seuil de similarité 0.7.
- **FR-002** : Le système MUST insérer les messages "long terme" en tête du contexte LLM avec un préfixe explicite « [Souvenirs pertinents d'échanges précédents] » distinct du flux chronologique courant.
- **FR-003** : Le système MUST exposer un tool `recall_history(query: str, limit: int = 5)` invocable par le LLM via le dispatcher F55, validé Pydantic strict (`extra='forbid'`, `query` non vide ≤ 256 chars, `limit` entre 1 et 10), avec docstring « use when / don't use when ».
- **FR-004** : Le système MUST scoper toutes les requêtes mémoire par `thread_id` ET `account_id` (RLS appliqué via GUC `app.current_account_id`). Aucun message d'un autre thread ne peut apparaître dans le contexte ou le résultat d'un tool.
- **FR-005** : Le système MUST persister un champ `chat_thread.summary TEXT NULLABLE`, `chat_thread.last_compacted_at TIMESTAMP NULLABLE`, et `chat_message.compacted BOOL NOT NULL DEFAULT FALSE`. Migration Alembic `0036_f57_memory_rag.py` (cible 0036 ; renumérotation triviale au merge si F56 prend 0036 — `down_revision` ajusté en post-merge).
- **FR-006** : Le système MUST exécuter une compaction async par chunks fixes de 50 messages, déclenchée à chaque seuil ≥ 100 (100, 150, 200, …) via `BackgroundTasks` FastAPI. À chaque compaction, le LLM génère un résumé ≤ 500 tokens couvrant le chunk de 50 messages les plus anciens encore non compactés (1-50 puis 51-100, etc.). Le résumé REMPLACE `chat_thread.summary` (pas cumulatif), les messages compactés sont marqués `compacted=True` (gardés en DB pour audit P3), `chat_thread.last_compacted_at` est mis à jour. Hierarchical summary (résumés de résumés) explicitement out-of-scope MVP.
- **FR-007** : Le système MUST exposer `GET /me/chat/threads/{id}/memory` retournant `{total_messages, recent_messages_count, summary, vector_index_size, last_compaction_at, entities_referenced: [{type, id, label}]}`. Backwards-compatible avec F18 (champs ajoutés, pas renommés).
- **FR-008** : Le système MUST exposer `DELETE /me/chat/threads/{id}/memory` qui exécute synchroniquement la purge des embeddings du thread (set `chat_message.embedding=NULL` pour tous les messages du thread), efface `chat_thread.summary`, met `chat_thread.last_compacted_at=NULL`, et écrit une ligne audit `{action: 'memory_forget', thread_id, user_id, ts, source_of_change: 'memory_system'}`. **NE supprime PAS** les `chat_message.content` (P3 audit) **ni** les `agent_entity_memory` (faits account-wide, voir Clarifications Q3 ; un endpoint séparé pour purger entity_memory sera livré post-MVP via "Mes données" F32). Idempotent (200 si déjà vide).
- **FR-009** : Le système MUST persister une table `agent_entity_memory(id UUID PK, account_id UUID NOT NULL, entity_type TEXT NOT NULL, entity_id UUID NOT NULL, summary TEXT NOT NULL, sources_used JSONB, last_updated_at TIMESTAMP NOT NULL, version INT NOT NULL DEFAULT 1)`. RLS policy par `account_id`. Index unique `(account_id, entity_type, entity_id)`.
- **FR-010** : Le système MUST hooker le dispatcher F55 : après chaque mutation `update_*` ou `create_*` ou `delete_*` réussie, enqueuer un `BackgroundTask update_entity_memory(account_id, entity_type, entity_id)` pour rafraîchir/créer/purger le summary correspondant.
- **FR-011** : Le système MUST calculer l'embedding de la `user_message` du tour courant **une seule fois** et le mettre en cache mémoire dans un dict transient attaché à `AgentState` (clé = hash(query)) pour réutilisation par recall auto (US1) et tool `recall_history` (US2) dans le même tour. Le cache est garbage-collected à la fin du tour (scope = un cycle d'exécution du graph LangGraph). Aucune persistance cross-run ni cache process-wide LRU.
- **FR-012** : Le système MUST écrire une ligne dans une table SQL dédiée `recall_log(id UUID PK, agent_run_id UUID, account_id UUID NOT NULL, thread_id UUID NOT NULL, recall_type TEXT CHECK IN ('auto','tool'), query_hash TEXT, top_k INT, top_scores JSONB, latency_ms INT, created_at TIMESTAMP NOT NULL DEFAULT now())` à chaque recall (auto ou tool). Index `(account_id, agent_run_id)` + `(account_id, thread_id, created_at)`. RLS policy `USING (account_id = current_setting('app.current_account_id')::uuid)`. Rétention applicative configurable via `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`.
- **FR-013** : Le système MUST exposer les variables d'env `LLM_AGENT_MEMORY_TOP_K=3`, `LLM_AGENT_MEMORY_THRESHOLD=0.7`, `LLM_AGENT_MEMORY_RECENT_COUNT=15`, `LLM_AGENT_COMPACT_THRESHOLD=100`, `LLM_AGENT_COMPACT_BATCH_SIZE=50`, `LLM_AGENT_COMPACT_MAX_TOKENS=500`, `LLM_AGENT_ENTITY_MEMORY_MAX_TOKENS=800`, `LLM_AGENT_RECALL_HISTORY_MAX_TOKENS=800`, `LLM_AGENT_RECALL_LOG_RETENTION_DAYS=90`. Échec fast au boot si valeurs invalides.
- **FR-014** : Le système MUST tomber en mode dégradé sans crash si Voyage API ou pgvector sont indisponibles (fallback : 15 derniers messages seulement, log warning, tour continue).
- **FR-015** : Le système MUST acquérir un lock optimiste sur `chat_thread.last_compacted_at` (CAS update) pour empêcher la double-compaction concurrente.
- **FR-016** : Le système MUST refuser le boot si la dimension Voyage configurée diffère de 1024 (validation config dim mismatch).
- **FR-017** : Le système MUST configurer un index pgvector HNSW (`m=16, ef_construction=64`) sur `chat_message.embedding` pour garantir la latence p95 < 300 ms sur 100 K messages. Documenté dans `quickstart.md`.
- **FR-018** : Le système MUST exposer la nouvelle table `agent_entity_memory` derrière une RLS policy `USING (account_id = current_setting('app.current_account_id')::uuid)` (cohérent P2).
- **FR-019** : Toute écriture mémoire (compaction summary, entity_memory create/update/delete, forget RGPD) MUST écrire une ligne audit_log avec `source_of_change='memory_system'` et le `tool_call_id`/`agent_run_id` pertinents si présents (P3 append-only).
- **FR-020** : Le tool `recall_history` MUST être exécuté par le dispatcher F55 en catégorie READ avec un budget tokens configurable pour la ré-injection en `ToolMessage` (cohérent F55 décision Q4).

### Non-Functional Requirements

- **NFR-001** : Latence `recall_memory` (court + long terme combinés) p95 < 300 ms sur un thread de 100 messages avec 100 K messages totaux indexés en DB (embedding query Voyage + pgvector cosine search).
- **NFR-002** : Latence p95 d'un tour incluant recall sur thread 100 msgs < 1 s côté agent (hors LLM streaming).
- **NFR-003** : Compaction async, jamais bloquante pour l'utilisateur. Latence d'écriture summary après trigger < 5 s p95 (LLM call inclus).
- **NFR-004** : Précision recall : ≥ 80 % des golden cases (30 cas thread→query→message attendu) retournent le message attendu dans le top 3.
- **NFR-005** : Aucune fuite cross-thread ou cross-account vérifiée par tests d'intégration (P2 RLS, anti-fuite par thread).
- **NFR-006** : Forget RGPD synchrone : `DELETE /me/chat/threads/{id}/memory` ne renvoie 200 que quand la purge est réellement effectuée (pas un job background).
- **NFR-007** : Couverture de test ≥ 90 % sur les modules `app/agent/memory/*` et `app/agent/nodes/recall_memory.py`, ≥ 80 % global.
- **NFR-008** : Aucune régression de F18 : les endpoints existants (`POST /me/chat/threads/{id}/messages`, `GET /me/chat/threads/{id}/memory` ancien format) continuent de fonctionner ; les champs ajoutés à l'endpoint memory sont en append (backwards-compatible).
- **NFR-009** : Le système MUST tracer chaque recall en moins de 5 ms d'overhead supplémentaire (log JSON structuré ou ligne SQL).

### Key Entities *(include if feature involves data)*

- **ChatThread** (existant F12/F18) — étendu avec `summary TEXT NULLABLE` et `last_compacted_at TIMESTAMP NULLABLE`.
- **ChatMessage** (existant F12/F18) — étendu avec `compacted BOOL NOT NULL DEFAULT FALSE`. L'embedding (VECTOR(1024)) est déjà existant F18.
- **AgentEntityMemory** (nouveau, FR-009) — `id UUID PK, account_id UUID NOT NULL, entity_type TEXT, entity_id UUID, summary TEXT, sources_used JSONB, last_updated_at TIMESTAMP, version INT`. RLS par account, partagée par thread (au sein d'un même account).
- **RecallLog** (nouveau, FR-012) — table SQL dédiée `recall_log(id UUID PK, agent_run_id UUID NULLABLE, account_id UUID NOT NULL, thread_id UUID NOT NULL, recall_type TEXT, query_hash TEXT, top_k INT, top_scores JSONB, latency_ms INT, created_at TIMESTAMP)`. RLS par `account_id`. Indexée `(account_id, agent_run_id)` et `(account_id, thread_id, created_at)`. Rétention 90 jours configurable.
- **EmbeddingCache** (in-memory runtime, pas persisté) — dict transient attaché à `AgentState` keyed par `hash(query)` → `vector(1024)` ; cycle de vie = un tour LangGraph (garbage-collected à la fin du tour). Aucune persistance ni cache cross-run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur un thread de 50 messages avec mentions « solaire 50 kWc » uniquement dans les 30 premiers, la requête « Reprends ce qu'on disait sur le solaire 50 kWc » fait apparaître 3 messages anciens pertinents en tête du contexte LLM avec préfixe « Souvenirs pertinents », et la réponse cite des chiffres du début du thread.
- **SC-002** : Un thread atteignant 100 messages déclenche une compaction async qui produit un `summary` < 500 tokens, marque les messages 1-50 avec `compacted=True`, met à jour `last_compacted_at`, et le tour suivant utilise `summary` + 15 derniers messages (pas les 50 compactés).
- **SC-003** : `GET /me/chat/threads/{id}/memory` retourne tous les champs US3 dont `entities_referenced` non vide quand le thread mentionne des entités business connues.
- **SC-004** : `DELETE /me/chat/threads/{id}/memory` répond 200 synchrone et purge effectivement les embeddings, le `summary`, `last_compacted_at` du thread sans toucher aux `chat_message.content` ni aux `agent_entity_memory` (purge entity = endpoint séparé post-MVP).
- **SC-005** : Test cross-thread : Thread A « panneaux solaires » (account X), Thread B « scooters » (account X), dans Thread B la requête « Rappelle ce qu'on disait sur les panneaux » → l'agent répond « Je ne trouve rien dans CE thread » et zéro message du Thread A n'apparaît dans le contexte ni la réponse.
- **SC-006** : `update_company_profile(secteur="C10.71")` → 30 s plus tard, `agent_entity_memory(Entreprise, ...).summary` mis à jour avec mention du nouveau secteur et `version` incrémenté.
- **SC-007** : Latence p95 d'un tour incluant recall sur thread de 100 msgs < 1 s côté agent (hors LLM streaming), mesurée sur dataset synthétique 100 K messages indexés.
- **SC-008** : Précision recall ≥ 80 % sur le golden set 30 cas (thread, query, message attendu en top 3).
- **SC-009** : Couverture de tests ≥ 90 % sur `app/agent/memory/*` et `app/agent/nodes/recall_memory.py` ; ≥ 80 % global du périmètre F57.
- **SC-010** : Un appel `recall_history` avec `query` vide est rejeté par le validateur Pydantic en amont du dispatcher (P9), aucune trace dans les logs recall ni dans la DB.
- **SC-011** : En mode Voyage API down, le tour LLM continue (fallback 15 derniers messages), zéro 500 utilisateur, un log warning est émis.

## Assumptions

- F53 (LangGraph core) est mergée et fournit `app/agent/state.py`, `AgentState`, `ToolDispatchResult`, `DispatchCategory`.
- F54 (Context builder) est mergée et fournit le squelette `app/agent/nodes/recall_memory.py` (15 derniers messages SQL simple) que F57 réécrit totalement, ainsi que `app/agent/context/*` et `app/agent/prompts/*`.
- F55 (Tool dispatch) est mergée et fournit le `dispatcher`, `MutationCtx`, hooks pre/post handler, catégories ASK/SHOW/MUTATION/READ. F57 utilise le dispatcher pour `recall_history` (catégorie READ) et le hook post-mutation pour `update_entity_memory`.
- F18 a livré la persistance `chat_message.embedding VECTOR(1024)` (Voyage `voyage-3.5`), un tool `recall_history` minimaliste, et un endpoint `GET /me/chat/threads/{id}/memory` ancien format. F57 enrichit le tool avec l'intégration LangGraph et étend l'endpoint au format US3.
- L'authentification chat assure que `app.current_account_id` est SET dans la session DB avant tout appel mémoire (middleware F02).
- Voyage API `voyage-3.5` produit des vecteurs 1024 dim ; configuration documentée dans `embeddings_client.py` (probablement déjà existant). Si manquant, F57 ajoutera un `app/embeddings/voyage_client.py` minimal.
- La table `chat_message` existe et possède déjà la colonne `embedding VECTOR(1024)` ; l'index pgvector HNSW peut être créé ou recréé via migration Alembic 0035 ou 0036.
- pgvector ≥ 0.5 (HNSW supporté). Vérifié à la migration.
- LLM model unchanged : OpenRouter `minimax-m2.7` via `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`.
- Le badge `MemoryBadge.vue` côté frontend existe (livré antérieurement). F57 expose le contrat enrichi côté API. La mise à jour du composant MemoryBadge pour consommer les nouveaux champs sera livrée dans une feature UI dédiée (voir Clarification Q4).
- F32 « Mes données » existe ou son point d'entrée pour le bouton "Effacer la mémoire" sera livré dans une feature UI dédiée. F57 valide le contrat backend `DELETE /me/chat/threads/{id}/memory` via un test E2E Playwright minimal qui appelle l'endpoint via fetch direct.
- Hosting EU/Afrique de l'Ouest uniquement (P. Souveraineté constitution).
- Tests d'intégration backend dominants en pytest+httpx ; 1 test E2E Playwright minimal `frontend/tests/e2e/memory.spec.ts` qui appelle directement les endpoints `GET /me/chat/threads/{id}/memory` puis `DELETE /me/chat/threads/{id}/memory` via fetch et vérifie le contrat de réponse (sans toucher MemoryBadge.vue ni F32 page).
- F56 (sourcing enforcement) tourne en parallèle ; F57 ne touche PAS `app/agent/sourcing/*`, `app/agent/handlers/cite_source.py`, `app/sourcing/*`, ni `app/agent/nodes/validate_payload.py`. Si F56 modifie `app/main.py`/`app/config.py`/`pyproject.toml`/`.specify/feature.json`, F57 fait des ajouts seulement (jamais de modif des lignes existantes ; conflit attendu sur `feature.json` au merge, résolu au 2e merge).

## Out of Scope (Hors-scope MVP, post-MVP)

- Hierarchical summaries (résumés de résumés pour threads de 1000+ messages) — MVP : un seul niveau de compaction.
- Cross-thread sharing volontaire ("transfère cette conversation à un nouveau thread") — post-MVP.
- User-facing edit de mémoire ("oublie ce que je viens de dire en gardant le reste") — post-MVP.
- Multi-modal memory (images, fichiers attachés indexés sémantiquement) — post-MVP, lié à F22 OCR.
- Cohort-based recall (réponses à des PME similaires) — post-MVP, soulève des questions privacy fortes.
- Auto-summarization du résumé par compaction successive (>1000 messages) — post-MVP.
- Hierarchical summary cumulatif (résumé qui agrège tous les chunks compactés au lieu de remplacer) — post-MVP, voir Clarification Q5.
- UI MemoryBadge enrichi (consommation des nouveaux champs) et bouton "Effacer la mémoire" sur la page F32 « Mes données » — F57 livre uniquement les endpoints backend + un test E2E Playwright minimal qui appelle directement les endpoints. Intégration UI complète livrée dans une feature UI dédiée (voir Clarification Q4).
- Endpoint séparé pour purger `agent_entity_memory` (account-wide) — post-MVP, voir Clarification Q3.

## Dependencies

- **F53 LangGraph core** (mergée PR #37) : `AgentState`, `ToolDispatchResult`, graph orchestration.
- **F54 Context builder** (mergée PR #38) : squelette `recall_memory.py` à réécrire ; `app/agent/context/*`, `app/agent/prompts/*`.
- **F55 Tool dispatch** (mergée PR #39) : dispatcher, hooks pre/post, catégories tool, `MutationCtx`.
- **F18 LLM memory & context** : embeddings DB déjà en place, tool `recall_history` minimaliste, endpoint memory ancien format.
- **F02 Auth & RLS** : middleware GUC `app.current_account_id`.
- **F04 Audit log & versioning** : audit_log append-only, tool_call_id, agent_run_id.
- **F12 Chat interface base** : `chat_thread`, `chat_message` tables.
- **F32 Mes données** : point d'entrée UI pour le forget RGPD (à clarifier).
- **Voyage AI `voyage-3.5`** : embeddings 1024 dim.
- **pgvector** : ≥ 0.5 (HNSW).

## Constitutional Alignment

- **P1 Sourcing** : `agent_entity_memory.sources_used` JSONB conserve les `source_id` des faits agrégés ; toute écriture entity_memory référence des sources verified.
- **P2 RLS account_id** : toutes les requêtes mémoire scopées par `account_id` GUC ; cross-tenant retourne 404 ; anti-fuite cross-thread testée.
- **P3 Audit append-only** : compaction, entity_memory CRUD, forget RGPD écrivent des lignes audit avec `source_of_change='memory_system'`.
- **P4 Versioning** : `agent_entity_memory.version` incrémenté à chaque mise à jour (logique referential).
- **P5 Money typé** : forget RGPD ne touche pas aux montants Money en DB business (frontière documentée).
- **P6 Indicateur pivot** : entity_memory référence `Indicateur` via `entity_type='Indicateur'` si pertinent (pas de duplication de valeurs).
- **P7 Pas d'intermédiaire** : aucun partage cross-account, entity_memory strictement par account.
- **P8 Sync DB↔LLM** : la DB reste source de vérité ; entity_memory est un cache reproductible. Toute mutation LLM invalide la mémoire LLM en cache et déclenche refresh entity_memory.
- **P9 Tool-use strict** : `recall_history` Pydantic strict, docstring use when/don't, validé en amont du dispatcher F55, max 2 retries.
- **P10 UI bottom sheet** : pas d'inputs interactifs ajoutés par F57 ; seul le bouton « Effacer la mémoire » (déclenche action) est concerné, conforme P10 (action explicite, pas un input dans bulle assistant).
