---
description: "Task list for F03 — Source & Sourçage Anti-Hallucination"
---

# Tasks: Source & Sourçage Anti-Hallucination

**Input**: Design documents from `/specs/003-source-anti-hallucination/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, contracts/llm_tools.md, contracts/SourceCite.props.md

**Tests**: TDD activé — chaque story embarque ses tests unitaires + intégration. Eval set 20 cas pour US3.

**Organization**: Groupées par user story pour livraison incrémentale (MVP = US1+US2+US3).

## Format: `[ID] [P?] [Story] Description`

- **[P]** : peut s'exécuter en parallèle (fichiers indépendants)
- **[Story]** : US1..US6 selon spec.md
- Chemins absolus depuis racine repo

## Path Conventions

Web app : `backend/`, `frontend/` à la racine du repo.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pré-requis projet pour cette feature.

- [X] T001 Vérifier que `backend/.venv` est actif et que `pgvector/pgvector:pg16` tourne via `docker compose ps` ; à défaut, lancer `docker compose up -d postgres`
- [X] T002 [P] Ajouter `cachetools>=5.3` à `backend/requirements.txt` et `pip install -r backend/requirements.txt`
- [X] T003 [P] Créer le squelette de répertoires backend : `backend/app/services/llm_tools/`, `backend/app/services/llm_validation/`, `backend/app/utils/`, `backend/app/prompts/`, `backend/tests/eval/`
- [X] T004 [P] Créer le squelette de répertoires frontend : `frontend/app/components/source/`, `frontend/app/composables/`, `frontend/app/pages/demo/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schéma DB, RLS, vues, audit hooks. **Bloque toutes les user stories.**

- [X] T005 Créer la migration Alembic `backend/alembic/versions/003_source_table_and_unsourced_log.py` avec : enum `source_verification_status`, table `source` (cf. data-model §2), table `unsourced_claim_log` (cf. §3), trigger BEFORE UPDATE de double-validation (FR-013), trigger d'incrément `status_version`, indexes GIN tsvector + IVFFlat embedding + status + publisher
- [X] T006 [P] Dans la même migration : créer les vues `v_indicateur_verified`, `v_critere_verified`, `v_formule_verified`, `v_seuil_verified`, `v_facteur_emission_verified`, `v_document_requis_verified`, `v_referentiel_verified` (cf. data-model §4) ; pour les tables catalogue déjà existantes, `ALTER TABLE` ajout `source_id uuid NOT NULL REFERENCES source(id) ON DELETE RESTRICT` (échec contrôlé documenté si données présentes non backfillées)
- [X] T007 Activer RLS sur `unsourced_claim_log` : politique `USING (account_id = current_setting('app.account_id')::uuid)`, GRANT INSERT/SELECT à `app_user`, REVOKE UPDATE/DELETE
- [X] T008 [P] Créer `backend/app/models/source.py` (SQLAlchemy 2 mapped_column, enum, embedding `Vector(1024)`, generated tsv) et `backend/app/models/unsourced_claim_log.py`
- [X] T009 [P] Créer `backend/app/schemas/source.py` (Pydantic v2 strict : `SourceRead`, `SourceVerificationStatus`, `SourceList`, `UnsourcedClaimAggRow`)
- [X] T010 [P] Créer `backend/app/prompts/system_anti_hallucination.md` reprenant le bloc d'instructions non-négociables Module 0.1 (FR-012)
- [X] T011 Exécuter `alembic upgrade head` puis `pytest backend/tests/unit/test_migration_smoke.py` pour valider la migration
- [X] T012 [P] Hook d'audit : insérer dans `audit_log` (table existante ou stub) à chaque transition de statut Source ; isoler dans `backend/app/services/source_audit.py` pour consommation propre par F04

**Checkpoint**: Schéma + RLS + vues prêts. Les 3 user stories P1 peuvent démarrer en parallèle.

---

## Phase 3: User Story 1 — Entité Source de premier rang avec FK obligatoire (Priority: P1) 🎯 MVP

**Goal**: Persistance Source + workflow `pending → verified` avec double validation et embedding ; FK NOT NULL prouvée par tests.

**Independent Test**: Lancer `pytest backend/tests/integration/test_source_lifecycle.py` ; tous les scénarios US1 (1-4) passent.

- [X] T013 [US1] Implémenter `backend/app/services/source_service.py` : `create_pending(...)`, `verify(source_id, verifier_id)`, `mark_outdated(source_id)`, `reject(source_id, reason)` ; appelle `embedding_service.compute()` lors de `verify()` (transactionnel, échec propre si Voyage indisponible — FR-016)
- [X] T014 [P] [US1] Tests unitaires `backend/tests/unit/test_source_service.py` : double validation refusée, embedding requis pour `verified`, transitions interdites tracées
- [X] T015 [P] [US1] Tests intégration `backend/tests/integration/test_source_lifecycle.py` : insertion catalogue sans `source_id` échoue ; objet lié à source `pending` masqué par vue `v_indicateur_verified` ; suppression refusée ON DELETE RESTRICT (FR-014)
- [X] T016 [US1] Implémenter route `GET /sources/{id}` (lecture publique unitaire) dans `backend/app/api/routes/sources.py` (cf. contracts/openapi.yaml)
- [X] T017 [US1] Implémenter route `GET /sources?q=&publisher=&status=&limit=&offset=` (admin only, RBAC F02) dans `backend/app/api/routes/sources.py`
- [X] T018 [P] [US1] Tests intégration `backend/tests/integration/test_sources_routes.py` : 200 admin, 403 PME sur la liste, 200 lecture unitaire publique, 404 non trouvé
- [X] T019 [US1] Brancher le router `sources` dans `backend/app/main.py`

**Checkpoint US1**: Schéma + workflow + endpoints publics OK. SC-001 partiellement vérifié (vues filtrent).

---

## Phase 4: User Story 2 — Tools backend cite_source / search_source / flag_unsourced (Priority: P1)

**Goal**: 3 handlers prêts à être exposés en function-calling OpenRouter, avec schémas Pydantic stricts.

**Independent Test**: `pytest backend/tests/unit/test_llm_tools.py backend/tests/integration/test_llm_tools_routes.py` — tous scénarios US2 passent.

- [X] T020 [P] [US2] Implémenter `backend/app/services/llm_tools/cite_source.py` : `CiteSourceInput`, handler retournant `Source` si `verified` sinon `ToolError(code='not_verified'|'not_found')` (cf. contracts/llm_tools.md)
- [X] T021 [P] [US2] Implémenter `backend/app/services/llm_tools/search_source.py` : full-text + vectoriel hybride (R1) ; appelle `embedding_service.compute(query, input_type='query')` ; fusion `0.5*rank_text + 0.5*(1 - cos_distance)` ; renvoie uniquement `verified`
- [X] T022 [P] [US2] Implémenter `backend/app/services/llm_tools/flag_unsourced.py` : insert dans `unsourced_claim_log` avec `account_id` lu via `current_setting('app.account_id')`, `user_id` nullable (FR-007 clarifié)
- [X] T023 [P] [US2] Tests unitaires `backend/tests/unit/test_llm_tools.py` : schémas Pydantic `extra='forbid'` rejettent inputs malformés ; `cite_source` refuse non-verified ; `search_source` exclut non-verified ; `flag_unsourced` retourne id
- [X] T024 [US2] Exposer les 3 handlers en HTTP interne `POST /internal/llm-tools/{name}` (consommé par Phase 3 LangGraph) dans `backend/app/api/routes/llm_tools.py`
- [X] T025 [P] [US2] Tests intégration `backend/tests/integration/test_llm_tools_routes.py` : 200 valid, 422 input malformé, 422 source non verified
- [X] T026 [US2] Génération de la définition function-calling OpenRouter (`tool_specs.json`) dans `backend/app/services/llm_tools/__init__.py` (utilisée plus tard par Phase 3)

**Checkpoint US2**: Tools opérationnels et testés ; Phase 3 (F14) pourra les consommer sans modifier le backend.

---

## Phase 5: User Story 3 — Middleware d'anti-hallucination des messages LLM (Priority: P1)

**Goal**: Garde finale qui rejette toute sortie LLM contenant un chiffre ESG sans tool-call `cite_source` valide.

**Independent Test**: `pytest backend/tests/integration/test_middleware_retry.py` + `python -m app.eval.run_anti_hallucination tests/eval/llm_anti_hallucination_set.json` → 100% des cas non sourcés rejetés (SC-002).

- [X] T027 [US3] Implémenter `backend/app/services/llm_validation/heuristics.py` : regex chiffre+unité ESG (R6) + dictionnaire mots-clés ; fonction `detect_esg_claims(message: str) -> DetectionResult`
- [X] T028 [P] [US3] Tests unitaires `backend/tests/unit/test_heuristics.py` : 12+ cas (positifs et négatifs) couvrant tCO2e, FCFA, EUR, %, kWh, "seuil", "critère", "formule", chiffre narratif sans unité (négatif)
- [X] T029 [P] [US3] Implémenter `backend/app/services/llm_validation/decision_cache.py` : `TTLCache(maxsize=10000, ttl=300)` ; clé `sha256(message + sorted(cited_ids) + max(status_versions))` ; fonction d'invalidation explicite
- [X] T030 [P] [US3] Tests unitaires `backend/tests/unit/test_decision_cache.py` : hit, miss, expiration, invalidation par bump de `status_version`
- [X] T031 [US3] Implémenter `backend/app/services/llm_validation/middleware.py` : `validate_llm_output(message_json) -> LLMValidationDecision` ; lit `tool_calls` JSON natifs OpenAI-compatible (clarification 2) ; vérifie chaque `cite_source` pointe sur source `verified` ; gère retry max 2 ; renvoie échappatoire au-delà
- [X] T032 [P] [US3] Tests intégration `backend/tests/integration/test_middleware_retry.py` : scénarios 1-5 spec.md (rejet sans citation, accept avec verified, rejet pending/outdated, échappatoire après 2 retries, hit cache)
- [X] T033 [P] [US3] Construire `backend/tests/eval/llm_anti_hallucination_set.json` (20 cas représentatifs — 10 négatifs à rejeter, 10 positifs à accepter)
- [X] T034 [US3] Implémenter le runner d'eval `backend/app/eval/run_anti_hallucination.py` (CLI `python -m app.eval.run_anti_hallucination <set.json>`)
- [X] T035 [US3] Brancher le middleware dans la pipeline LLM côté backend (point d'extension consommé par F14, exposé via fonction `apply_to_llm_response()` dans `backend/app/services/llm_validation/__init__.py`)

**Checkpoint US3**: Garde anti-hallucination opérationnelle. SC-002 ✓. **MVP atteint à ce point.**

---

## Phase 6: User Story 4 — Composant UI Source cliquable (Priority: P2)

**Goal**: `<SourceCite>` Vue + bottom sheet listant les sources.

**Independent Test**: `pnpm test SourceCite.spec.ts` + ouvrir `http://localhost:3000/demo/source-cite-demo` ; les 3 états visuels sont rendus (SC-003).

- [X] T036 [P] [US4] Créer `frontend/app/composables/useSourceFetch.ts` : `useSourceFetch(id: string)` → `Source | null` via `GET /sources/{id}`, gestion loading/error
- [X] T037 [P] [US4] Implémenter `frontend/app/components/source/SourceCite.vue` selon contracts/SourceCite.props.md (props, events, picto, clic ouvre bottom sheet)
- [X] T038 [P] [US4] Implémenter `frontend/app/components/source/SourceListBottomSheet.vue` (gsap slide-up, focus trap, badges Vérifiée/Non vérifiée/Obsolète, lien externe target=_blank rel=noopener) — pattern UI bottom sheet (P10)
- [X] T039 [US4] Créer la page démo `frontend/app/pages/demo/source-cite-demo.vue` rendant 3 instances (verified, pending, outdated)
- [X] T040 [P] [US4] Tests Vitest `frontend/tests/unit/SourceCite.spec.ts` : rendu picto, ouverture bottom sheet au clic, badges selon statut
- [X] T041 [P] [US4] Test E2E Playwright `frontend/tests/e2e/source-cite.spec.ts` : ouverture bottom sheet, vérification des 3 badges, clic lien externe ouvre dans nouvel onglet

**Checkpoint US4**: SC-003 ✓.

---

## Phase 7: User Story 5 — Annexe Sources auto-générée (Priority: P2)

**Goal**: Utilitaire backend `build_sources_appendix(ids) -> markdown`.

**Independent Test**: `pytest backend/tests/unit/test_sources_appendix.py` — 10/3 doublons ramenés à 7 entrées, exclusion `pending`/`rejected`.

- [X] T042 [US5] Implémenter `backend/app/utils/sources_appendix.py` : `build_sources_appendix(source_ids: list[UUID]) -> str` (markdown dédoublonné, trié par publisher puis date_publi desc, exclut non-verified, marque `[source incomplète]` si champ critique manquant) + helper `to_pdf_section(md: str)`
- [X] T043 [P] [US5] Tests unitaires `backend/tests/unit/test_sources_appendix.py` : dédoublonnage, exclusion non-verified, formatage markdown stable, source incomplète marquée

**Checkpoint US5**: SC-004 ✓.

---

## Phase 8: User Story 6 — Tableau de bord admin claims non sourcés (Priority: P3)

**Goal**: `GET /admin/unsourced-claims` agrégé sous RLS.

**Independent Test**: `pytest backend/tests/integration/test_admin_unsourced_routes.py` + `test_rls_unsourced.py`.

- [X] T044 [US6] Implémenter route `GET /admin/unsourced-claims?days=30&limit=50` dans `backend/app/api/routes/admin_unsourced.py` (RBAC admin, RLS appliquée par `app.account_id`)
- [X] T045 [P] [US6] Tests intégration `backend/tests/integration/test_admin_unsourced_routes.py` : agrégation correcte (5 entrées dont 3 normalisées identiques → 3 lignes), pagination, ordre par fréquence desc
- [X] T046 [P] [US6] Tests RLS `backend/tests/integration/test_rls_unsourced.py` : admin tenant A ne voit pas claims tenant B (404 / liste vide)

**Checkpoint US6**: SC-008 ✓.

---

## Phase 9: Polish & Cross-Cutting

- [X] T047 [P] Performance smoke test `backend/tests/perf/test_search_source_p95.py` : seed 5000 sources verified, 1000 appels `search_source`, assert p95 < 200ms (SC-005)
- [X] T048 [P] Performance smoke test `backend/tests/perf/test_middleware_p95.py` : 500 messages, assert latence p95 ajoutée < 50ms (SC-006)
- [X] T049 [P] Audit SQL automatisé `backend/scripts/audit_unsourced_catalog.sql` : requête qui retourne 0 ligne si aucun objet exposé sans source verified (SC-001)
- [X] T050 [P] Audit hebdomadaire double-validation `backend/scripts/audit_double_validation.sql` (SC-007)
- [X] T051 Mettre à jour `CLAUDE.md` (déjà pointé par `/speckit-plan` vers ce plan) — ajouter une note dans `docs_et_brouillons/features/00-INDEX.md` que F03 est "ready_for_implement"
- [X] T052 [P] Documentation README de la feature dans `specs/003-source-anti-hallucination/quickstart.md` (déjà créée — vérifier les commandes après implémentation)
- [X] T053 Lancer `pytest backend/tests -q --cov=backend/app --cov-report=term-missing` ; viser couverture ≥ 80% sur `services/source_service.py`, `services/llm_tools/*`, `services/llm_validation/*`, `utils/sources_appendix.py`

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → { Phase 3 (US1), Phase 4 (US2), Phase 5 (US3) en parallèle }
                                          → { Phase 6 (US4), Phase 7 (US5), Phase 8 (US6) en parallèle après US1+US2 }
                                          → Phase 9 (Polish)

Détail :
- US3 (T031) consomme SourceService.cite_source via la table source (US1) ⇒ démarrer T031 après T013.
- US4 (T036) appelle GET /sources/{id} (US1 T016) ⇒ démarrer après T016.
- US5 (T042) lit la table source ⇒ après T013.
- US6 (T044) lit unsourced_claim_log alimenté par US2 (T022) ⇒ après T022.
```

## Parallel execution examples

- **Sprint 1 (Foundational)** : T005 puis en parallèle T006, T008, T009, T010, T012.
- **Sprint 2 (P1 stories)** : équipe A sur T013→T019 (US1), équipe B sur T020→T026 (US2), équipe C sur T027→T035 (US3) après que T013 soit mergé.
- **Sprint 3 (P2 stories)** : T036→T041 (US4) et T042→T043 (US5) en parallèle.
- **Sprint 4 (P3 + polish)** : T044→T046 (US6) puis T047→T053 (perf + audits).

## MVP scope

**MVP** = Phases 1, 2, 3 (US1), 4 (US2), 5 (US3). Livre l'invariant Module 0 vérifié end-to-end côté backend, prêt à être branché par F14 (LangGraph).

US4 (UI), US5 (annexe rapport) et US6 (dashboard admin) sont **post-MVP** mais inclus dans cette feature pour livrer la promesse complète.
