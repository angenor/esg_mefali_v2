# Research — F18 Mémoire Contextuelle LLM

**Date**: 2026-04-29

## R1 — Modèle d'embeddings et dimension

**Decision**: Voyage AI `voyage-3.5`, dimension 1024.

**Rationale**: Le client `app/embeddings_client.py` est déjà en place (F01), testé et utilisé en BackgroundTask par F13 (`app/chat/embedding_task.py`). La table `chat_message` (migration 0011) porte déjà `embedding VECTOR(1024)`. Aucun coût d'intégration supplémentaire.

**Alternatives considérées**:
- OpenAI `text-embedding-3-small` (dim 1536) : exigerait migration de schéma — rejeté.
- Embeddings auto-hébergés : ajout de dépendances lourdes — rejeté.

## R2 — Type d'index pgvector

**Decision**: `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)`.

**Rationale**: Pour < 100 000 messages (cible MVP), `ivfflat lists=100` offre un build rapide et une qualité suffisante (rappel ~95 % avec `probes=10`). HNSW serait plus précis mais inutilement coûteux à ce volume.

**Note d'opération**: lancer `ANALYZE chat_message;` après le build initial. `SET ivfflat.probes = 10;` peut être positionné par le service au moment de la requête `recall_history`.

**Alternatives considérées**:
- HNSW : meilleure qualité mais build et écriture plus lents — migration cible post-MVP.
- Pas d'index : > 1 s pour 50k vecteurs — viole NFR-002.

## R3 — Estimation tokens

**Decision**: Approximation `n_caractères / 4`.

**Rationale**: Aucune dépendance externe. L'erreur < 15 % sur du français/anglais est suffisante pour décider d'une compaction (le budget 2 000 tokens reste très en dessous de la fenêtre dure du modèle).

**Alternatives considérées**:
- `tiktoken` : ajout dépendance, gain marginal.
- API tokenizer : surcoût réseau à chaque tour.

## R4 — Stratégie de compaction (déterministe)

**Decision**: Trois passes successives tant que `estimate_tokens(bundle) > budget` :
1. Tronquer toutes les `description` projets : 200 → 100 → 50 caractères.
2. Réduire le nombre de projets : 10 → 7 → 5 → 3.
3. Raccourcir la fenêtre messages : 15 → 12 → 10 → 8 → 5 (jamais < 5).

**Rationale**: Préserve l'information factuelle critique (nom, statut, montants, secteur) et la conversation immédiate. La description est la donnée la plus prosaïque et la plus compressible.

**Alternatives considérées**:
- Compaction par LLM : trop coûteux et non déterministe pour MVP.
- Suppression du profil : briserait US1.

## R5 — Périmètre du recall_history

**Decision**: Restriction au thread courant uniquement en MVP (FR-012).

**Rationale**: Évite la pollution cross-thread. Performance garantie par filtre `thread_id = :tid` qui réduit drastiquement le set candidat avant le scan vectoriel.

**Alternatives considérées**:
- Cross-thread : risque de bruit important, reportable post-MVP.

## R6 — Embedding des messages payload tool

**Decision**: Embedder un texte composite `"{label} — {description?}"` extrait du `payload_json` (clés `label`, `title`), pas le JSON brut. Si aucune clé pertinente, fallback sur le `content` texte.

**Rationale**: Un JSON brut de visualisation (F16) ou d'action (F15) contient beaucoup de bruit structurel qui pollue la similarité sémantique.

**Alternatives considérées**:
- Embedder le JSON brut sérialisé : pollution sémantique.
- Ne pas embedder les messages tool : perte d'information.

## R7 — Sync édition manuelle ↔ contexte (FR-009)

**Decision**: Pas de cache. Lecture systématique du profil entreprise (F11) et des projets (F12) à chaque appel de `build_context()`.

**Rationale**: La PME édite puis envoie un message dans la seconde — un cache TTL créerait des cas stale incompréhensibles. Le coût (2 SELECT additionnels par tour) est négligeable face à la latence d'un appel LLM (~1 s).

**Alternatives considérées**:
- Cache TTL 5 s : risque stale.
- Cache invalidé par événement : sur-ingénierie MVP.

## R8 — Gating du tool recall_history

**Decision**: Le tool est exposé au sélecteur F14 uniquement si `count(messages_du_thread) > 15`.

**Rationale**: En dessous, les 15 derniers messages couvrent toute la conversation — `recall_history` serait redondant. Le sélecteur F14 (`app/orchestrator/tool_selector.py`) accepte déjà une liste dynamique de tools.

**Alternatives considérées**:
- Toujours exposé : pollue le prompt outils.
- Seuil 30 : trop tardif.

## R9 — Format du system message injecté

**Decision**: Markdown léger, sections `# Profil entreprise`, `# Projets actifs`, `# Conversation récente`, ajouté en tête de la conversation OpenRouter (rôle `system`). Sections optionnelles (omises si vides).

**Rationale**: Les modèles ouverts (minimax-m2.7) suivent bien la structure markdown. Lisible humainement pour le debug.

**Alternatives considérées**:
- JSON structuré : plus difficile à raisonner pour le LLM.
- Prose narrative : moins compressible.

## R10 — Échec embedding lors de la persistance

**Decision**: Le BackgroundTask F13 actuel (`app/chat/embedding_task.py`) catch déjà toutes les exceptions et logge un warning sans relever. F18 ne modifie pas ce comportement. Le re-essai automatique reste hors-scope MVP.

**Rationale**: Architecture déjà conforme à FR-007. Sur-ingénierie évitée (perte tolérée < 1 % en cas d'incident Voyage).

**Alternatives considérées**:
- Queue Redis + worker : hors invariants Module 0.
- Recalcul synchrone bloquant : viole FR-007.
