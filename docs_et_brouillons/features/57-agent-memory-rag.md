# F57 — Agent Memory & Long-term Recall (LangGraph node + pgvector RAG)

**Phase** : H — Agent Hardening
**Modules brainstorm** : 1.4 (Mémoire contextuelle), 11.5 (Skills + Memory)
**Dépendances** : F18 (memory recent + recall_history tool), F53 (LangGraph core), F54 (Context builder)
**Estimation** : 3 jours

## Contexte et objectif

F18 a livré :
- Persistance de chaque message dans `chat_message` avec `embedding VECTOR(1024)` (Voyage `voyage-3.5`).
- Tool `recall_history(query)` qui fait un cosine search.
- Helper `build_context()` côté backend qui assemble les 15 derniers messages.

Mais ce mécanisme **n'est pas branché à un agent vivant** (le chat actuel envoie juste le dernier message du user).

F57 livre l'**intégration LangGraph** :
1. Un nœud `recall_memory` dans le graph F53 qui décide **quand** et **comment** charger l'historique.
2. Une stratégie **2 niveaux** : court terme (15 derniers messages chronologiques) + long terme (top-K via embedding).
3. Compaction périodique des longs threads (résumés générés par LLM) pour éviter de saturer pgvector.
4. Memory snapshot consultable par l'utilisateur (badge `MemoryBadge.vue` déjà existant frontend).

## User Stories

### US1 — Nœud `recall_memory` dans le graph (P1)

**En tant que** dev,
**je veux** un nœud LangGraph `app/agent/nodes/recall_memory.py` qui :
1. Charge les **15 derniers messages** (`role IN ('user', 'assistant')`) du thread, ordre chronologique ASC, format LangChain `BaseMessage`.
2. Si le thread compte > 15 messages, embed la `user_message` du tour courant (Voyage), fait une cosine search sur `chat_message.embedding` du thread (excluant les 15 derniers), retient le top-K (K=3 par défaut) au-dessus d'un seuil de similarité (`0.7` cosine).
3. Insère les messages "long terme" en tête de `state.messages` avec un préfixe explicite : `[Souvenirs pertinents d'échanges précédents]`.

**afin que** l'agent ait à la fois la cohérence locale et l'accès aux sujets passés.

### US2 — Tool `recall_history(query)` invocable explicitement (P1)

**En tant que** dev,
**je veux** que le tool `recall_history(query: str, limit: int = 5)` soit toujours disponible (cf. F56),
**afin que** l'agent puisse explicitement chercher dans la mémoire si la query courante ne déclenche pas le recall automatique.

Différence avec US1 : US1 est automatique au début du tour ; US2 est invoqué par le LLM en cours de raisonnement ("Cherche dans nos échanges précédents : '...'").

### US3 — Compaction async du thread (P2)

**En tant que** ops,
**je veux** un job async (lancé par `BackgroundTasks` FastAPI) qui, quand un thread atteint 100 messages, génère un **résumé compact** (< 500 tokens) couvrant les messages 1 à 50, l'enregistre dans `chat_thread.summary` et marque les messages compactés `compacted=True` (gardés en DB pour audit mais exclus du recall),
**afin de** maîtriser la taille des prompts et le coût pgvector.

Trigger : après chaque insertion message, si `count(messages) % 50 == 0`, enqueue compaction.

### US4 — Memory snapshot endpoint enrichi (P1)

**En tant que** utilisateur,
**je veux** que `GET /me/chat/threads/{id}/memory` retourne :
- `total_messages: int`
- `recent_messages_count: int` (15)
- `summary: str | null` (US3)
- `vector_index_size: int` (combien de messages embed-indexés)
- `last_compaction_at: datetime | null`
- `entities_referenced: list[{type, id, label}]` (entreprise, projets, candidatures cités dans le thread)

**afin que** la badge frontend `MemoryBadge` puisse afficher le détail de la mémoire active.

### US5 — Persistance résumée par entité (P2)

**En tant que** dev,
**je veux** une table `agent_entity_memory` qui stocke, par `(account_id, entity_type, entity_id)`, un résumé de tout ce que l'agent a appris sur cette entité à travers les threads (max 800 tokens),
**afin que** l'agent ait un "fait stable" sur l'entreprise / un projet / une candidature, même en commençant un nouveau thread.

Mise à jour : déclenchée par `dispatch.MUTATION` quand un tool modifie une entité, ou par compaction périodique.

### US6 — Forget / suppression RGPD (P1)

**En tant que** utilisateur,
**je veux** depuis "Mes données" (F32) un bouton "Effacer la mémoire long terme de ce thread" qui supprime les embeddings, le résumé compaction, et les `agent_entity_memory` correspondants — **sans** supprimer les messages eux-mêmes (conservés pour audit log P3),
**afin que** mon droit à l'oubli soit respecté.

L'agent au tour suivant verra uniquement les 15 derniers messages bruts.

### US7 — Anti-fuite cross-thread (P1)

**En tant que** dev,
**je veux** que **toutes** les requêtes mémoire soient strictement scopées par `thread_id` ET `account_id`,
**afin qu'** un thread A ne voie jamais les messages d'un thread B, même au sein d'un même account (privacy par thread).

Exception : `agent_entity_memory` est partagé **au sein d'un account** (logique : "ce que je sais de cette entreprise"), mais n'expose jamais des messages bruts.

### US8 — Cache embedding (P2)

**En tant que** dev,
**je veux** que l'embedding d'un message soit calculé une seule fois (background task après insert) et **mis en cache** côté Voyage (déjà géré) + indexé dans pgvector,
**afin de** ne pas recomputer à chaque tour.

Pour le `recall_memory` US1, l'embedding de la `user_message` du tour courant doit être réutilisé pour le cosine search (calcul unique).

### US9 — Tracing des recalls (P2)

**En tant que** dev,
**je veux** que chaque recall (auto ou explicite) soit loggué : `agent_run_id, recall_type, query, top_k, top_scores, latency_ms`,
**afin de** mesurer la qualité de la mémoire (nourrit F60).

## Exigences fonctionnelles

- **FR-001** : Nœud `app/agent/nodes/recall_memory.py` exposant `async def node(state) -> dict`. Logique US1.
- **FR-002** : Module `app/chat/memory/long_term.py` exposant `async def search_long_term(thread_id, account_id, query_embedding, exclude_message_ids, limit, threshold) -> list[ChatMessage]`. Cosine search via pgvector `<=>` operator. RLS appliqué.
- **FR-003** : Champ `chat_thread.summary TEXT NULLABLE` + `chat_thread.last_compacted_at TIMESTAMP NULLABLE` + `chat_message.compacted BOOL NOT NULL DEFAULT FALSE`. Migration Alembic.
- **FR-004** : Module `app/chat/memory/compactors.py` (étendu de F18) : `async def compact_thread(thread_id, db) -> int` (retourne nombre messages compactés). Génère le résumé via LLM, stocke dans `chat_thread.summary`, marque les messages `compacted=True`.
- **FR-005** : Endpoint `GET /me/chat/threads/{id}/memory` (déjà existant F18) **étendu** au format US4. Backwards-compatible (champs ajoutés, pas modifiés).
- **FR-006** : Table `agent_entity_memory` : `id, account_id, entity_type, entity_id, summary TEXT, sources_used JSONB, last_updated_at, version INT`. Index `(account_id, entity_type, entity_id)`.
- **FR-007** : Hook dispatch (F55) : après chaque mutation `update_*` réussie, enqueue background task `update_entity_memory(account_id, entity_type, entity_id)`.
- **FR-008** : Endpoint `DELETE /me/chat/threads/{id}/memory` qui réalise le forget RGPD (US6). Pas de suppression de messages, juste embeddings + summary + entity memories liées au thread.
- **FR-009** : Logs structurés `recall` : `thread_id, query_hash, top_scores, latency_ms, source: 'auto'|'tool'`.
- **FR-010** : Variable d'env `LLM_AGENT_MEMORY_TOP_K: int = 3`, `LLM_AGENT_MEMORY_THRESHOLD: float = 0.7`, `LLM_AGENT_MEMORY_RECENT_COUNT: int = 15`, `LLM_AGENT_COMPACT_THRESHOLD: int = 100`.
- **FR-011** : Tests d'intégration `tests/integration/test_memory.py` : 1 test recall auto, 1 test compaction trigger, 1 test forget RGPD, 1 test anti-fuite cross-thread, 1 test entity_memory update.

## Exigences non-fonctionnelles

- **NFR-001** : Latence `recall_memory` < 300 ms p95 (embedding query + pgvector search 100 K msgs).
- **NFR-002** : Compaction async, jamais bloquante pour l'utilisateur. Latence d'écriture summary < 5 s.
- **NFR-003** : Précision recall (golden set 30 cas thread→query→message attendu) ≥ 80 %.
- **NFR-004** : Aucune fuite cross-thread/cross-account vérifiée par test E2E.
- **NFR-005** : Index pgvector HNSW configuré pour balance vitesse/précision (`m=16, ef_construction=64`). Documenter le tuning.
- **NFR-006** : Le forget RGPD est **synchrone** côté utilisateur (l'API renvoie 200 quand c'est effectivement fait), pas un job background.

## Entités clés

- **ChatThread** étendu : `summary`, `last_compacted_at`.
- **ChatMessage** étendu : `compacted` boolean.
- **AgentEntityMemory** (FR-006) — nouveau, partagé par account, pas par thread.

## Success Criteria

- **SC-001** : Thread de 50 messages, l'utilisateur dit "Reprends ce qu'on disait sur le solaire 50 kWc" → `recall_memory` automatique ramène les 3 messages les plus pertinents en tête, l'agent répond avec cohérence sur ce projet.
- **SC-002** : Thread de 200 messages → compaction déclenchée, `chat_thread.summary` contient un résumé < 500 tokens, les messages 1-100 sont marqués `compacted=True`, le prompt suivant utilise `summary` + 15 derniers messages.
- **SC-003** : `GET /me/chat/threads/{id}/memory` retourne tous les champs US4 dont `entities_referenced = [{type:'Projet', id:..., label:'Solaire 50 kWc'}, ...]`.
- **SC-004** : `DELETE /me/chat/threads/{id}/memory` → embeddings purgés, summary effacé, `agent_entity_memory` du thread effacés. Messages bruts conservés.
- **SC-005** : Test cross-thread : Thread A (account X) parle de "panneaux solaires", Thread B (account X) parle de "scooters électriques". Dans Thread B, demander "rappelle ce qu'on disait sur les panneaux" → l'agent répond "rien dans CE thread" (anti-fuite).
- **SC-006** : `update_company_profile(secteur="C10.71")` → 30 s plus tard, `agent_entity_memory(Entreprise, ...).summary` mis à jour avec mention du nouveau secteur.
- **SC-007** : Latence p95 d'un tour incluant recall sur thread de 100 msgs < 1 s côté agent (hors LLM).
- **SC-008** : Précision recall : 80 % des golden cases retournent le bon message dans le top 3.

## Hors-scope MVP (post-MVP)

- Hierarchical summaries (résumés de résumés pour threads de 1000+ messages) — MVP : un seul niveau.
- Cross-thread sharing volontaire ("transfère cette conversation à un nouveau thread") — post-MVP.
- User-facing edit de mémoire ("oublie ce que je viens de dire") — post-MVP.
- Multi-modal memory (images, fichiers attachés indexés sémantiquement) — post-MVP, lié à F22 OCR.
- Cohort-based recall (réponses à des PME similaires) — post-MVP, soulève des questions privacy fortes.

## Risques et points de vigilance

- **Voyage API quotas** : embedding de chaque message ajoute du coût. Estimer : si 1000 PME × 50 messages/jour = 50K embeddings/jour, vérifier limites Voyage. Cache server-side de l'embedding pour la query du tour (FR utilisé une fois par recall_memory + une fois par tool recall_history dans le même tour).
- **pgvector performance** : sur 1M messages, les cosine search peuvent ralentir sans HNSW. Tester avec dataset synthétique.
- **Compaction qualité** : un mauvais résumé fait perdre l'info importante. Évaluer sur golden : "après compaction, l'agent doit toujours pouvoir répondre correctement à 90 % des questions sur les sujets compactés".
- **Drift entity memory** : si un projet est créé puis supprimé, `agent_entity_memory` doit être purgée. Ajouter trigger SQL ou background task au DELETE.
- **Privacy entity memory** : "ce que l'agent sait de l'entreprise" peut contenir des infos personnelles (nom CEO, anecdotes). Limiter à des faits structurés sourcés (pas de free-form). Tester avec des cas réels.
- **Forget RGPD partiel** : si l'utilisateur efface un thread, mais des données extraites (via tool mutation) sont en DB business → on ne les efface PAS (c'est l'entité, pas la mémoire). Bien documenter cette frontière dans la page "Mes données".
- **Concurrence compaction** : si deux requêtes simultanées triggerent compaction du même thread → double summary. Lock optimiste sur `chat_thread.last_compacted_at`.

## Spec-Kit hooks

```bash
/speckit.specify "$(cat docs_et_brouillons/features/57-agent-memory-rag.md)"
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```
