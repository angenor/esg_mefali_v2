# Tasks — F18 Mémoire Contextuelle LLM

**Date**: 2026-04-29
**Feature dir**: `specs/018-llm-memory-context/`
**Approche** : TDD strict, MVP minimal vert. P1 obligatoire (US1, US2, US3, US5, US6). P2 (US4 recall_history) à livrer si le budget restant le permet.

## Phase 1 — Setup

- [ ] T001 Créer le sous-package `backend/app/chat/memory/__init__.py` (export public : `build_context`, `ContextBundle`, `RecallHistoryArgs`, `execute_recall_history`).
- [ ] T002 Créer le miroir tests `backend/tests/chat/memory/__init__.py` (vide) et `backend/tests/chat/memory/conftest.py` (fixtures pour account/thread/messages/profil/projets si non couvert par les fixtures globales existantes).
- [ ] T003 Ajouter dans `backend/app/config.py` la lecture de l'env var `CONTEXT_TOKEN_BUDGET` (entier, défaut 2000) — exposé comme constante module.

## Phase 2 — Foundational (bloquant pour tous les US)

- [ ] T004 Créer la migration alembic `backend/alembic/versions/0013_f18_chat_message_embedding_index.py` qui exécute `CREATE INDEX IF NOT EXISTS idx_chat_message_embedding ON chat_message USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);` en upgrade et `DROP INDEX IF EXISTS idx_chat_message_embedding;` en downgrade. Référence parent : `0012_f12_projets_documents`.
- [ ] T005 Étendre `backend/app/chat/repository.py` avec `list_recent_messages(db, *, thread_id, account_id, limit=15) -> list[dict]` (DESC sur created_at, exclut role='system' et deleted_at, retourné en chronologique ASC après reverse).
- [ ] T006 Étendre `backend/app/chat/repository.py` avec `count_messages_in_thread(db, *, thread_id, account_id) -> int` (compte les messages user/assistant non supprimés).

## Phase 3 — User Story 5 (P1) : Embeddings calculés à la persistance

**Goal**: Garantir que chaque message persisté reçoit un embedding 1024-dim, et que le content embeddé pour les payloads tool est le label/title plutôt que le JSON brut.

**Independent test**: Persister un message avec `payload_json={"label":"Graphique CA"}` et vérifier que la fonction d'extraction retourne "Graphique CA" pour l'embedding.

- [ ] T007 [US5] Écrire `backend/tests/chat/memory/test_embedding_text.py` (TDD RED) : tests pour `extract_embedding_text(content, payload_json)` — content brut si pas de payload, label si payload.label, title si payload.title, fallback content si payload sans label/title.
- [ ] T008 [P] [US5] Implémenter `extract_embedding_text(content: str, payload_json: dict | None) -> str` dans `backend/app/chat/memory/compactors.py` (fonction utilitaire pure) — passer T007 au vert.
- [ ] T009 [US5] Modifier `backend/app/chat/embedding_task.py` : importer `extract_embedding_text`, l'utiliser pour calculer le texte à embedder à partir de `content + payload_json` (signature étendue : `compute_and_store_embedding(message_id, content, payload_json=None)`).
- [ ] T010 [US5] Mettre à jour les call-sites dans `backend/app/chat/api.py` (ou `service.py`) pour passer `payload_json` au BackgroundTask `compute_and_store_embedding`.
- [ ] T011 [US5] Écrire `backend/tests/chat/memory/test_embedding_integration.py` : test qui persiste un message avec payload, mock `embed`, vérifie que le texte appelé est le label.

## Phase 4 — User Story 2 + 3 (P1) : Compactors + budget tokens

**Goal**: Fournir les compacteurs de profil/projets, l'estimation de tokens et la stratégie de réduction sous budget. Couvre l'extraction de la fenêtre 15 messages.

**Independent test**: Charger un dict profil avec champs sensibles + 25 projets et vérifier que `compact_profile`/`compact_projets` produit la sortie attendue (whitelist appliquée, projets actifs ≤ 10, descriptions tronquées).

- [ ] T012 [US2] Écrire `backend/tests/chat/memory/test_compactors.py` (TDD RED) couvrant :
  - `compact_profile`: whitelist appliquée, exclusion `password`/`token`/PII, troncature description à 200 chars.
  - `compact_projets`: filtre `statut NOT IN {cloture, annule}`, limite `max_n=10`, troncature description configurable, préservation Money.
  - `estimate_tokens`: `len(text) // 4` avec tests aux frontières (string vide, ASCII, accents).
  - `fit_to_budget`: bundle au-dessus du budget → applique passes 1 (descriptions 200/100/50), 2 (projets 10/7/5/3), 3 (messages 15/12/10/8/5) jusqu'à passer sous budget ou plancher atteint.
- [ ] T013 [P] [US2] Implémenter `compact_profile(entreprise: dict) -> dict | None` dans `backend/app/chat/memory/compactors.py` (whitelist explicite + truncate desc). Retourne None si profil vide.
- [ ] T014 [P] [US2] Implémenter `compact_projets(projets: list[dict], max_n: int = 10, desc_limit: int = 200) -> list[dict]` dans `backend/app/chat/memory/compactors.py`.
- [ ] T015 [P] [US2] Implémenter `estimate_tokens(text: str) -> int` (= `len(text) // 4`) dans `backend/app/chat/memory/compactors.py`.
- [ ] T016 [US2] Implémenter `fit_to_budget(bundle, budget) -> ContextBundle` dans `backend/app/chat/memory/compactors.py` — applique R4 (3 passes déterministes), retourne nouveau bundle immuable.
- [ ] T017 [US3] Vérifier que `test_compactors.py` couvre la troncature messages (15 → 5 plancher).

## Phase 5 — User Story 1 + 6 (P1) : Context builder

**Goal**: Assembler le `ContextBundle` à chaque tour, avec lecture sans cache du profil et des projets. Format markdown lisible. Injection en system message.

**Independent test**: Créer un compte+thread, persister un profil et 3 projets, builder le contexte, vérifier le rendu markdown et la fraîcheur après modification du profil.

- [ ] T018 [US1] Écrire `backend/tests/chat/memory/test_context_builder.py` (TDD RED) couvrant :
  - `test_build_context_basic`: profil + 3 projets actifs + 5 messages → bundle non vide.
  - `test_build_context_empty_profile`: profil vide → `profile_section is None`.
  - `test_build_context_no_active_projects`: 0 projet actif → `projects_section is None`.
  - `test_build_context_window_15`: 20 messages → exactement 15, ordre chronologique.
  - `test_build_context_budget_compaction`: 25 projets desc 2000 chars → `estimated_tokens <= budget`.
  - `test_build_context_expose_recall_flag`: 16 vs 15 messages.
  - `test_build_context_no_sensitive_fields`: champ `password` dans le profil → absent du rendu.
  - `test_build_context_freshness` (US6): mutation profil entre deux appels → reflétée immédiatement.
- [ ] T019 [P] [US1] Définir les dataclasses `ChatMessageView` et `ContextBundle` (frozen=True) dans `backend/app/chat/memory/context_builder.py` avec méthode `to_system_message()`.
- [ ] T020 [US1] Implémenter `build_context(db, *, account_id, thread_id, token_budget=None) -> ContextBundle` dans `backend/app/chat/memory/context_builder.py` — orchestrer lecture F11/F12/F13 (via repos), compaction, fit_to_budget, calcul flag `expose_recall_history`.
- [ ] T021 [US1] Ajouter dans `context_builder.py` les helpers privés `_render_profile_section(profile_dict) -> str | None` et `_render_projects_section(projects_list) -> str | None` (markdown FR, Money formaté `{amount} {currency}`).
- [ ] T022 [US6] Vérifier `test_build_context_freshness` (déjà en T018) — confirmer aucune lecture cachée (chaque call refait les 2 SELECT F11/F12).

## Phase 6 — User Story 4 (P2) : Tool recall_history

**Goal**: Exposer le tool `recall_history` au LLM avec recherche pgvector intra-thread, exclusion des 15 derniers messages, isolation par compte.

**Independent test**: Sur thread de 50 messages avec 5 mentions « biogaz Sénégal » enterrées, invoquer `execute_recall_history(query="biogaz Sénégal")` → ≤ 5 hits ordonnés par similarité, hors top 15.

- [ ] T023 [US4] Écrire `backend/tests/chat/memory/test_recall_history.py` (TDD RED) couvrant les 8 scénarios du contrat (`contracts/recall_history.md` section "Tests obligatoires") + gating (>15 messages).
- [ ] T024 [P] [US4] Définir `RecallHistoryArgs(BaseModel)` et `RecallHit(BaseModel)` (avec `model_config = ConfigDict(extra='forbid')`) dans `backend/app/chat/memory/recall_history_tool.py`.
- [ ] T025 [US4] Implémenter `execute_recall_history(db, *, account_id, thread_id, args) -> list[RecallHit]` dans `recall_history_tool.py` — court-circuit query<3 chars, embedding via Voyage, requête SQL paramétrée pgvector, snippet via `extract_embedding_text`.
- [ ] T026 [US4] Enregistrer le tool dans `backend/app/orchestrator/tool_registry.py` via `tool(name="recall_history", ...)` à l'import du module `recall_history_tool`.
- [ ] T027 [US4] Étendre `backend/app/orchestrator/tool_selector.py` pour accepter un flag `expose_recall_history` (ou méthode équivalente) et inclure/exclure `recall_history` selon `count_messages_in_thread > 15`.
- [ ] T028 [US4] Tests d'intégration de gating dans `test_recall_history.py::test_gating_below_threshold` et `test_gating_above_threshold`.

## Phase 7 — Polish & Cross-Cutting

- [ ] T029 Brancher `build_context()` dans le flow d'orchestration LLM (caller existant F14) : `backend/app/orchestrator/` ou `backend/app/chat/service.py` selon où la conversation OpenRouter est composée — ajouter le system message en tête.
- [ ] T030 Documenter dans `backend/app/chat/memory/__init__.py` le contrat public (docstring module) et exporter les noms publics via `__all__`.
- [ ] T031 Lint final : `cd backend && ruff check app/chat/memory/ tests/chat/memory/` doit passer.
- [ ] T032 Couverture finale : `cd backend && pytest -q --cov=app/chat/memory tests/chat/memory/` doit afficher ≥ 80 % sur le sous-package F18.
- [ ] T033 Compléter `.cc-runtime/logs/manual-tests-18.md` avec les résultats du smoke test quickstart (sortie de `bundle.to_system_message()` sur compte de test).

## Dépendances entre phases

```
Phase 1 → Phase 2 → Phase 3 (US5)
                    │
                    ↓
                  Phase 4 (US2+US3) → Phase 5 (US1+US6)
                                              │
                                              ↓
                                        Phase 6 (US4) [optional]
                                              │
                                              ↓
                                        Phase 7 (Polish)
```

- US5 (embeddings) doit précéder US4 (recall_history en a besoin).
- US2/US3 (compactors) précèdent US1/US6 (context_builder en dépend).
- US4 dépend de Phase 4 (extract_embedding_text déjà en place).
- Phase 7 (T029 branchement) attend que `build_context` soit vert.

## Parallélisation possible

- Au sein de Phase 4 : T013, T014, T015 sont [P] (fonctions pures indépendantes — si même fichier, exécution séquentielle).
- Au sein de Phase 5 : T019 [P] indépendant de T020.
- Au sein de Phase 6 : T024 [P] indépendant de T025.

## MVP minimal vert (scope obligatoire)

Phases 1 → 2 → 3 → 4 → 5 → 7 (sans Phase 6).
Livre US1 + US2 + US3 + US5 + US6 (tous P1).
US4 (recall_history) est livré seulement si Phase 6 tient dans le budget — fallback : marquer **[DEFERRED]** dans le rapport et créer une issue de suivi.

## Independent test criteria par story

| Story | Critère d'acceptation isolé |
|---|---|
| US1 | Profil édité → injecté dans bundle au tour suivant |
| US2 | Bundle compacté ≤ 2000 tokens sur fixture 25 projets |
| US3 | 15 derniers messages présents en ordre chrono |
| US4 | recall_history retrouve un hit sur thread 50 msgs en < 200 ms |
| US5 | Message persisté → embedding 1024 dim non nul |
| US6 | 2 build_context successifs avec mutation profil entre les deux → 2ᵉ reflète la mutation |
