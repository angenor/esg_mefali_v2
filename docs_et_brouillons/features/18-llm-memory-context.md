# F18 — Mémoire Contextuelle (15 derniers messages + RAG pgvector + recall_history)

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 1.4 (Mémoire Contextuelle MVP simplifié)
**Dépendances** : F03, F11, F12, F13, F14
**Estimation** : 1.5–2 jours

## Contexte et objectif

Le LLM a besoin de savoir **qui est la PME** et **ce qui s'est dit avant** pour répondre pertinemment. Cette feature livre le **contexte transmis à chaque tour** :

1. **Profil entreprise + projets** (F11+F12) : injectés systématiquement dans le system prompt à chaque tour, avec budget tokens contrôlé (résumé compact si trop volumineux).
2. **15 derniers messages** : conservés en clair dans le contexte (dialogue récent).
3. **Historique ancien** : indexé via **pgvector + Voyage AI embeddings** (RAG basique), récupéré à la demande via le tool `recall_history(query)`.
4. **Synchronisation bidirectionnelle** avec les éditions manuelles du Profil (cohérent F11/F12) : aucune valeur stale ne doit fuiter au LLM.

## User Stories

### US1 — Profil entreprise + projets injectés à chaque tour (P1)
**En tant que** PME,
**je veux** que le LLM ait toujours une vue à jour de mon entreprise et de mes projets sans que j'aie à les répéter,
**afin de** ne pas avoir des conversations qui repartent de zéro.

**Test indépendant** : la PME édite manuellement son CA en F11, puis dit "calcule mon ratio CA/effectifs" → le LLM utilise la nouvelle valeur (pas l'ancienne).

### US2 — Budget tokens contrôlé pour le contexte (P1)
**En tant que** dev,
**je veux** que le contexte injecté (profil + projets + historique récent) ne dépasse jamais un budget configuré (ex : 2 000 tokens), avec compaction automatique si dépassement,
**afin de** maîtriser les coûts et ne pas saturer la fenêtre.

**Compaction** : si > N projets, ne lister que les actifs (statut ≠ `cloture`) avec champs essentiels. Si description très longue, tronquer à 200 caractères + lien `recall_history` implicite.

### US3 — 15 derniers messages préservés (P1)
**En tant que** dev,
**je veux** que les 15 derniers messages utilisateur+assistant du thread courant soient inclus dans le contexte (avec leurs payloads tools si pertinent),
**afin que** le LLM ait la mémoire courte de la conversation.

### US4 — Tool recall_history(query) pour la mémoire longue (P2)
**En tant que** PME,
**je veux** dire au LLM "tu te rappelles ce qu'on avait dit sur le projet biogaz le mois dernier ?" → le LLM invoque `recall_history(query)` qui fait une recherche vectorielle dans tous les messages plus anciens que les 15 récents,
**afin de** retrouver des éléments enterrés.

**Test indépendant** : invoquer `recall_history(query="biogaz Sénégal")` retourne les 5 messages les plus pertinents anciens du thread (ou de tous les threads du compte ? — voir clarify).

### US5 — Embeddings calculés via Voyage AI (P1)
**En tant que** dev,
**je veux** que chaque message persisté ait son embedding `voyage-3.5` (1024 dim) calculé en background et stocké dans `chat_message.embedding` (F13),
**afin de** alimenter `recall_history` (US4) et `search_source` (F03).

**Mode** : calcul synchrone après persistance (pas async pour MVP — accepté la latence de quelques 100ms).

### US6 — Sync édition manuelle ↔ contexte LLM (P1)
**En tant que** PME,
**je veux** qu'une édition manuelle dans `/profil/entreprise` ou `/profil/projets` invalide immédiatement le cache du contexte LLM,
**afin que** mon prochain message au LLM voie la nouvelle valeur.

**Mécanisme MVP simple** : pas de cache du profil — on relit en début de chaque tour. Pas de TTL, pas de problème de cohérence.

## Exigences fonctionnelles

- **FR-001** : Module backend `context_builder.py` exposant `build_context(account_id, thread_id, current_message?) -> ContextBundle` qui assemble :
  - profil entreprise (F11) compact JSON,
  - liste projets actifs (F12) compact JSON,
  - skills actives (F19, optionnel à ce stade),
  - 15 derniers messages du thread (F13).
- **FR-002** : Helper `compact_profile(entreprise) -> dict` et `compact_projets(projets, max_n=10) -> list` qui appliquent la compaction (US2).
- **FR-003** : Estimation des tokens (`tiktoken` ou approximation `n_chars/4`). Budget configurable `CONTEXT_TOKEN_BUDGET=2000`.
- **FR-004** : Tool `recall_history(query: str, k: int = 5) -> list[ChatMessage]` :
  - calcul embedding de la query via Voyage AI,
  - recherche `pgvector` cosine sur `chat_message.embedding` filtrée par `account_id` (RLS) et antérieur aux 15 derniers messages,
  - retour des K messages avec snippet + thread_id + date.
- **FR-005** : Calcul d'embeddings à la persistance des messages (`POST /me/chat/threads/{id}/messages` de F13) → enrichi pour appeler `embeddings_client.embed([content])` synchrone et stocker.
- **FR-006** : Pas de cache de profil/projet côté LLM — relecture à chaque tour. Performance acceptée : 1 SELECT/tour.
- **FR-007** : Le contexte construit est **un système message** ajouté au début de la conversation envoyée à OpenRouter, formaté en sections lisibles ("# Profil entreprise", "# Projets actifs", "# Conversation récente").
- **FR-008** : Le tool `recall_history` est exposé au LLM uniquement sur les threads ayant > 15 messages (utile seulement à partir d'un certain volume). Sinon, omis du sélecteur (F14).

## Exigences non-fonctionnelles

- **NFR-001** : Calcul embedding Voyage AI < 300ms par message en moyenne (API).
- **NFR-002** : `recall_history` < 200ms p95 (index `ivfflat` ou `hnsw` sur `chat_message.embedding`).
- **NFR-003** : Compaction du profil ne perd pas d'info critique pour le scoring/diagnostic — ne tronquer que les champs descriptifs.
- **NFR-004** : Aucun champ sensible dans le contexte LLM (mots de passe, JWT, refresh tokens). Whitelist explicite dans `compact_profile`.

## Entités clés

- Aucune nouvelle table — `chat_message.embedding` (F13) suffit.
- Index pgvector ajouté sur `chat_message.embedding` (`ivfflat` ou `hnsw`).

## Success Criteria

- **SC-001** : Profil entreprise édité manuellement → prochaine réponse LLM utilise la nouvelle valeur (testé sur 5 cas).
- **SC-002** : Conversation longue (50 messages) — `recall_history` retrouve un message ancien pertinent en < 200ms.
- **SC-003** : Le contexte injecté ne dépasse pas le budget tokens (testé avec 20 projets, 100 messages).
- **SC-004** : Embeddings persistés à 100% des messages.

## Hors-scope MVP (post-MVP)

- Digest périodique automatique (résumé mensuel généré par LLM).
- Snapshot mensuel du profil utilisateur (pour montrer l'évolution).
- Mémoire long-terme cross-thread (recall_history multi-threads).
- Compression intelligente du contexte par LLM léger.
- Embeddings re-calculés en batch en cas de changement de modèle Voyage.

## Risques et points de vigilance

- **Drift de coût Voyage** : 1 embedding/message = 1 appel API/message. Sur 1000 PME × 10 msgs/jour = 10 000 appels/jour. Voyage tier gratuit limité — vérifier le quota et passer en payant si MVP scale.
- **Index pgvector** : `ivfflat` rapide à construire mais qualité moyenne ; `hnsw` plus lent à construire mais meilleur. Pour MVP avec < 100k messages, `ivfflat lists=100` suffit. Migration `hnsw` post-MVP.
- **Compaction perd-elle de l'info critique ?** : tester sur des cas réels. Un projet avec 30 indicateurs d'impact compactés à 5 = perte. Préférer un format JSON dense plutôt que prose résumée.
- **`recall_history` cross-thread** : tentation de chercher dans tous les threads du compte. Risque : ramener un message d'un thread sur un autre sujet. Démarrer par recherche **dans le thread courant uniquement**, élargir post-MVP.
- **Embedding du content texte uniquement** : si le message est un payload (visualisation), embedder le label/title plutôt que le JSON brut.
