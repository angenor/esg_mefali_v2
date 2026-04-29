# Tasks — F07 Catalog Sources Management

**Feature**: 007-catalog-sources-management
**Branch**: `007-catalog-sources-management`
**Inputs**: plan.md, research.md, data-model.md, contracts/admin-sources.openapi.yaml, contracts/public-sources.openapi.yaml, quickstart.md
**TDD**: tests d'abord, puis implémentation. Coverage cible ≥ 80%.

## Statut d'exécution (2026-04-29)

**Implémenté (P1 partiel — MVP minimal)** :
- Phase 1 setup : T001 (migration 0007_sources_canonical_url), T002, T003, T004, T005 (déjà présents), T006 [DEFERRED frontend]
- Phase 2 foundational : T010 (migration partielle, search_vector différé), T012/T013 (canonicalize 13 tests), T015/T016 (http_probe 5 tests), T017 (schemas), T019/T020 (permissions 2 tests)
- US1 : T031 (create_source 4 tests integration), T032 (audit log inscrit), T033 (service.create_source), T034/T035 (router POST/GET admin/sources, 6 tests HTTP)

**Tests** : 30 nouveaux tests F07 (20 unit + 4 service + 6 router) ; total 332 passed / 5 skipped ; coverage globale 86.56 %, F07 module 86 %.

**[DEFERRED] — seconde passe d'implémentation** :
- T011 (test migration up/down dédié)
- T014 (backfill canonical_url Python — palliatif via trigger SQL)
- T018 (types TS frontend)
- T021/T022/T023 (repository.list_paginated, recherche tsvector + unaccent, find_duplicate par repo)
- T030 (test contract OpenAPI snapshot)
- T036–T040 (frontend US1 : composable, SourceForm, DuplicateBanner, page new)
- T050–T059 (US2 : verify, mark-outdated, update versioning, delete, frontend)
- T070–T076 (US3 : list filtrable + recherche + frontend)
- T080–T086 (US4 : impact analysis + frontend)
- T100–T105 (US5 : page publique — P2)
- T120–T123 (US6 : unsourced claims — P3)
- T140–T147 (Phase 9 polish)

Justification : la session a livré un MVP minimal testé (création + canonicalisation + détection doublon + audit + permissions cross-admin) avec coverage > 80 %, sans régression F01–F06. La suite (workflow verify, listing, impact, frontend) est indépendante et peut être reprise en une seconde passe sans risque sur l'existant.

---

Légende des annotations :
- `[P]` parallélisable (fichier différent, indépendant des tâches incomplètes).
- `[US1]..[US6]` rattaché à un user story du spec.
- Aucun label de story = Setup, Foundational, ou Polish.

---

## Phase 1 — Setup

- [ ] T001 Vérifier l'extension Postgres `unaccent` disponible et la déclarer dans la migration cible (backend/alembic/versions/007_xxx_sources_indices_canonical.py — squelette vide à créer)
- [ ] T002 [P] Créer le module backend `backend/app/catalog/sources/__init__.py` (package vide pour structure)
- [ ] T003 [P] Créer le dossier de tests `backend/app/tests/catalog/sources/{unit,integration,contract}/__init__.py`
- [ ] T004 [P] Ajouter `httpx[http2]` au `backend/requirements.txt` si non présent (HEAD probe FR-007)
- [ ] T005 [P] Vérifier que `pytest-asyncio` et `pytest-cov` sont dans `backend/requirements.txt` ; sinon les ajouter
- [ ] T006 [P] Préparer le dossier frontend `frontend/app/pages/admin/sources/` et `frontend/app/components/admin/sources/` (création vide pour la structure)

## Phase 2 — Foundational (blocking)

### Migration & schéma

- [ ] T010 Écrire la migration Alembic `backend/alembic/versions/007_xxx_sources_indices_canonical.py` : `CREATE EXTENSION IF NOT EXISTS unaccent`, ajout `source.canonical_url TEXT`, backfill SQL temporaire `canonical_url = url`, puis `ALTER COLUMN canonical_url SET NOT NULL`, contrainte CHECK double-validation, index unique `ux_source_canonical_url_page`, colonne générée `search_vector`, index GIN `idx_source_search_vector`, indices secondaires `idx_source_verification_status` et `idx_source_publisher`.
- [ ] T011 Test migration : `backend/app/tests/catalog/sources/integration/test_migration_007.py` — applique upgrade puis downgrade sur DB de test, vérifie présence/absence des index et de la contrainte CHECK.

### Utilitaires partagés (TDD)

- [ ] T012 [P] Test unitaire `backend/app/tests/catalog/sources/unit/test_canonicalize.py` : table de cas (https forcé, lower-case host, retrait `www.`, retrait slash final, retrait params tracking, conservation `#page=`, idempotence, root `/` conservée).
- [ ] T013 Implémenter `backend/app/catalog/sources/canonicalize.py` jusqu'à passer T012.
- [ ] T014 Backfill `canonical_url` dans la migration en réutilisant `canonicalize_url` via callback Alembic Python op (`op.execute` + UDF) ou script Python post-upgrade. Tester en T011.
- [ ] T015 [P] Test unitaire `backend/app/tests/catalog/sources/unit/test_http_probe.py` : mock `httpx.AsyncClient` (success 200, 404, timeout, exception réseau), vérifie shape `{ok, status, error}`.
- [ ] T016 Implémenter `backend/app/catalog/sources/http_probe.py` jusqu'à passer T015.

### Schémas Pydantic et types frontend

- [ ] T017 [P] Implémenter `backend/app/catalog/sources/schemas.py` : `SourceCreate`, `SourceUpdate`, `SourceRead`, `SourceCreated` (avec `head_warning`), `SourceUpdated` (avec `version_bumped`), `SourceListItem`, `SourceListResponse`, `ImpactResponse`, `ImpactCategoryList`, `UnsourcedClaimsResponse`, `DuplicateConflict` ; `model_config = ConfigDict(extra='forbid')`.
- [ ] T018 [P] Générer types TS frontend via `openapi-typescript` depuis `specs/007-catalog-sources-management/contracts/admin-sources.openapi.yaml` vers `frontend/app/types/admin-sources.d.ts` ; et `public-sources.openapi.yaml` vers `frontend/app/types/public-sources.d.ts`.

### Permissions

- [ ] T019 [P] Test unitaire `backend/app/tests/catalog/sources/unit/test_permissions.py` : `assert_admin` requis ; `assert_can_verify(source, actor)` lève 409 si `captured_by == actor`.
- [ ] T020 Implémenter `backend/app/catalog/sources/permissions.py` jusqu'à passer T019.

### Repository & search

- [ ] T021 Implémenter `backend/app/catalog/sources/repository.py` (SQLAlchemy 2 async) : `list_paginated(filters, q, page, page_size, sort)`, `get(id)`, `create(payload, captured_by)`, `update(id, patch, expected_etag)`, `soft_delete(id)`, `find_duplicate(canonical_url, page)`, `count_dependents(id)`. Utilise `tsvector` + `ts_rank_cd` + `unaccent` pour `q`.
- [ ] T022 [P] Test integration `backend/app/tests/catalog/sources/integration/test_search.py` : couvre tolérance accents, pertinence, pagination, tri.
- [ ] T023 Test integration `backend/app/tests/catalog/sources/integration/test_repository_duplicates.py` : `find_duplicate` matche par canonical_url + page.

---

## Phase 3 — User Story 1 : Saisir une nouvelle Source (P1)

**Story goal** : un admin peut créer une source via API/UI avec canonicalisation, HEAD probe non bloquant, détection de doublon, audit log, statut `pending`.

**Independent test** : POST `/admin/sources` avec payload valide → 201 + source retournée + audit log inscrit ; doublon → 409 ; URL invalide → 422.

### Tests (TDD, écrire AVANT impl)

- [ ] T030 [P] [US1] Test contract `backend/app/tests/catalog/sources/contract/test_openapi_admin.py::test_post_create_matches_schema` (snapshot vs `admin-sources.openapi.yaml`).
- [ ] T031 [P] [US1] Test integration `backend/app/tests/catalog/sources/integration/test_create_source.py` : create OK → 201 ; sans titre → 422 ; URL avec `?utm_source=x` → stocke canonical_url sans utm ; HEAD 404 → réponse contient `head_warning`; doublon (même canonical_url + page) → 409 avec `existing_id`.
- [ ] T032 [P] [US1] Test integration audit : T031 vérifie qu'une entrée `audit_log` est créée avec `action='source.create'`, `actor`=user, `source_of_change='admin'`.

### Implémentation backend

- [ ] T033 [US1] Implémenter `backend/app/catalog/sources/service.py::create_source(payload, actor)` : canonicalise URL, détecte doublon, lance HEAD probe (timeout 5s) en tâche concurrente non bloquante, persiste via repository, inscrit audit, retourne `SourceCreated` avec `head_warning`.
- [ ] T034 [US1] Ajouter route POST dans `backend/app/catalog/sources/router.py` (`/admin/sources`), branchée sur le service ; appliquer `Depends(assert_admin)`.
- [ ] T035 [US1] Enregistrer le router dans `backend/app/main.py` (ou dans le registry F06 si pertinent), prefix `/api`.

### Implémentation frontend

- [ ] T036 [P] [US1] Implémenter `frontend/app/composables/useAdminSources.ts` (méthodes `create`, `getById`, `list`, etc.).
- [ ] T037 [P] [US1] Implémenter `frontend/app/components/admin/sources/SourceForm.vue` (champs + validation, bouton submit, gestion erreur 409 doublon → bannière `DuplicateBanner.vue`).
- [ ] T038 [P] [US1] Implémenter `frontend/app/components/admin/sources/DuplicateBanner.vue` (CTA "Réutiliser cette source" → redirige vers `/admin/sources/{existing_id}`).
- [ ] T039 [US1] Implémenter `frontend/app/pages/admin/sources/new.vue` (utilise `SourceForm`, redirige vers `/admin/sources/{id}` après création).
- [ ] T040 [P] [US1] Test unit Vitest `frontend/tests/unit/components/admin/sources/SourceForm.test.ts` (rendu + validation + erreur 409 → bannière).

**Checkpoint US1** : un admin peut saisir une source de bout en bout, en `pending`. Indépendamment livrable.

---

## Phase 4 — User Story 2 : Workflow de double vérification (P1)

**Story goal** : seul un admin différent du créateur peut valider ; serveur strict ; supprimer si non référencée ; mark-outdated possible.

**Independent test** : POST `/admin/sources/{id}/verify` par créateur → 409 ; par autre admin → 200 et statut `verified` ; DELETE non orphan → 409 ; mark-outdated → 200 et statut `outdated`.

### Tests

- [ ] T050 [P] [US2] Test integration `backend/app/tests/catalog/sources/integration/test_verify_workflow.py` : refus auto-validation, succès cross-admin, audit log `source.verify`, transition impossible si déjà `verified`.
- [ ] T051 [P] [US2] Test integration `backend/app/tests/catalog/sources/integration/test_mark_outdated.py` : transition `verified→outdated`, audit log, snapshots de candidatures inchangés (vérifier table `candidature_snapshot`).
- [ ] T052 [P] [US2] Test integration `backend/app/tests/catalog/sources/integration/test_delete_orphan.py` : delete orphan OK, delete non orphan → 409 ; delete `verified` non orphan → 409.
- [ ] T053 [P] [US2] Test integration `backend/app/tests/catalog/sources/integration/test_update_versioning.py` : modification `notes` → `version_bumped=false` ; modification `url` → `version_bumped=true` + nouvelle ligne `source_version` (F04).

### Implémentation backend

- [ ] T054 [US2] Étendre `backend/app/catalog/sources/service.py` : `verify(id, actor)`, `mark_outdated(id, actor)`, `update(id, patch, actor)` (avec détection delta champs critiques + appel helper F04 `versioning.bump_source_version`), `delete(id, actor)`.
- [ ] T055 [US2] Ajouter routes POST `/admin/sources/{id}/verify`, POST `/admin/sources/{id}/mark-outdated`, PATCH `/admin/sources/{id}`, DELETE `/admin/sources/{id}` dans `router.py`.
- [ ] T056 [US2] Brancher chaque mutation à `audit.record(...)` (F04) avec `before/after` capturés avant/après transaction.

### Implémentation frontend

- [ ] T057 [P] [US2] Implémenter `frontend/app/pages/admin/sources/[id]/index.vue` : affichage source + bouton "Valider" (désactivé si `captured_by == currentUser`), "Marquer obsolète", "Supprimer" (désactivé si dépendants), formulaire d'édition.
- [ ] T058 [P] [US2] Implémenter store `frontend/app/stores/adminSources.ts` (actions verify/markOutdated/update/delete).
- [ ] T059 [P] [US2] Test E2E Playwright `frontend/tests/e2e/admin-sources.spec.ts::verify_workflow` : Admin A crée, A ne peut valider, B valide, A et B voient `verified`, B marque outdated.

**Checkpoint US2** : workflow de double validation complet et auditable.

---

## Phase 5 — User Story 3 : Liste filtrable et recherche (P1)

**Story goal** : liste paginée 25/50/100 avec filtres (statut, publisher, date range, capté par moi) et recherche full-text accent-insensitive < 1s pour 5000 sources.

**Independent test** : GET `/admin/sources?q=...&status=pending&page_size=25` retourne items pertinents ; tri par colonnes ; pagination correcte.

### Tests

- [ ] T070 [P] [US3] Test integration `backend/app/tests/catalog/sources/integration/test_list_filters.py` : filtres (statut multi, publisher, date_from/to, captured_by_me), tri toutes colonnes, pagination.
- [ ] T071 [P] [US3] Test perf `backend/app/tests/catalog/sources/integration/test_list_perf.py` : seed 5000 sources, mesure < 1s pour première page (skip si CI lent, marquer `@pytest.mark.perf`).

### Implémentation backend

- [ ] T072 [US3] Ajouter route GET `/admin/sources` dans `router.py`, mapper paramètres → `repository.list_paginated`.

### Implémentation frontend

- [ ] T073 [P] [US3] Implémenter `frontend/app/components/admin/sources/SourceFilters.vue` (multi-select statut, autocomplete publisher, date range, toggle "capté par moi").
- [ ] T074 [P] [US3] Implémenter `frontend/app/components/admin/sources/SourceTable.vue` (tri par colonnes, pagination 25/50/100, lazy favicon).
- [ ] T075 [US3] Implémenter `frontend/app/pages/admin/sources/index.vue` (compose filters + table + barre recherche + bouton "+ Nouvelle source").
- [ ] T076 [P] [US3] Test unit Vitest pour `SourceFilters.vue` et `SourceTable.vue`.

**Checkpoint US3** : navigation rapide sur 5000 sources.

---

## Phase 6 — User Story 4 : Impact analysis (P1)

**Story goal** : compteurs agrégés < 500ms ; expansion lazy par catégorie ; aide à décision avant modification ou outdated.

**Independent test** : GET `/admin/sources/{id}/impact` retourne `counters` complet ; GET `/impact/{category}` paginé.

### Tests

- [ ] T080 [P] [US4] Test integration `backend/app/tests/catalog/sources/integration/test_impact.py` : seed FK depuis indicateurs/critères/formules/facteurs/documents/référentiels/skills/candidatures ; vérifie tous compteurs ; perf < 500ms ; `has_published_dependents`, `can_delete`, `can_mark_outdated` corrects.
- [ ] T081 [P] [US4] Test integration `test_impact_expansion.py` : pagination par catégorie.

### Implémentation backend

- [ ] T082 [US4] Implémenter `backend/app/catalog/sources/impact.py` : requête CTE multi-UNION pour compteurs ; requêtes paginées par catégorie via repositories existants F08+ (placeholder gracieux si table pas encore présente — utilisation conditionnelle via reflection ou flags `feature_available`).
- [ ] T083 [US4] Ajouter routes GET `/admin/sources/{id}/impact` et `/impact/{category}` dans `router.py`.

### Implémentation frontend

- [ ] T084 [P] [US4] Implémenter `frontend/app/components/admin/sources/SourceImpactPanel.vue` (compteurs + expansion accordéon par catégorie, chargement paginé).
- [ ] T085 [P] [US4] Implémenter `frontend/app/pages/admin/sources/[id]/impact.vue`.
- [ ] T086 [P] [US4] Test unit Vitest `SourceImpactPanel.test.ts`.

**Checkpoint US4** : visibilité d'impact avant toute modification critique.

---

## Phase 7 — User Story 5 : Page publique de lecture (P2)

**Story goal** : `GET /sources/{id}` rendu sans login, `noindex`, 404 sur `pending`.

**Independent test** : visiteur anonyme charge `/sources/{verified_id}` → 200 ; `/sources/{pending_id}` → 404 ; header `X-Robots-Tag: noindex, nofollow` présent.

### Tests

- [ ] T100 [P] [US5] Test integration `backend/app/tests/catalog/sources/integration/test_public_page.py` : 200 pour `verified` et `outdated`, 404 pour `pending`, header noindex présent, payload limité aux champs publics.
- [ ] T101 [P] [US5] Test E2E Playwright `frontend/tests/e2e/public-source.spec.ts` : visiteur sans cookie charge la page, voit titre/url/publisher, badge si `outdated`, balise `<meta name="robots" content="noindex,nofollow">`.

### Implémentation backend

- [ ] T102 [US5] Implémenter `backend/app/api/public_sources.py` : endpoint `GET /api/public/sources/{id}` filtre `verification_status IN ('verified','outdated')`, ajoute header `X-Robots-Tag: noindex, nofollow`.
- [ ] T103 [US5] Enregistrer le router dans `main.py`.

### Implémentation frontend

- [ ] T104 [P] [US5] Implémenter `frontend/app/composables/usePublicSource.ts`.
- [ ] T105 [US5] Implémenter `frontend/app/pages/sources/[id].vue` SSR : `useHead({ meta: [{ name:'robots', content:'noindex,nofollow' }] })`, fetch via composable, rendu sobre, lien externe vers URL canonique, badge si `outdated`.

**Checkpoint US5** : auditabilité externe.

---

## Phase 8 — User Story 6 : Sources non sourçables (P3)

**Story goal** : page admin agrégeant `flag_unsourced` (F03) avec compteur.

**Independent test** : GET `/admin/unsourced-claims` retourne items groupés par claim ; UI permet pré-remplir formulaire de création.

### Tests

- [ ] T120 [P] [US6] Test integration `backend/app/tests/catalog/sources/integration/test_unsourced_claims.py` : seed `unsourced_claim` ; agrégation OK ; tri par occurrences.

### Implémentation backend

- [ ] T121 [US6] Ajouter endpoint `GET /admin/unsourced-claims` dans `router.py` (utilise table F03).

### Implémentation frontend

- [ ] T122 [P] [US6] Implémenter `frontend/app/pages/admin/unsourced-claims.vue` (liste, tri, lien "Créer une nouvelle source à partir de ce claim" → `/admin/sources/new?claim=...`).
- [ ] T123 [P] [US6] Adapter `SourceForm.vue` pour pré-remplissage via query param `?claim=`.

**Checkpoint US6** : pilotage qualité sourcing.

---

## Phase 9 — Polish & Cross-Cutting

- [ ] T140 [P] Validation contract OpenAPI globale : `backend/app/tests/catalog/sources/contract/test_openapi_admin.py::test_full_schema_match` compare schémas FastAPI vs YAML.
- [ ] T141 [P] Vérifier coverage ≥ 80% via `pytest --cov=app/catalog/sources --cov-fail-under=80`.
- [ ] T142 [P] Ajouter script seed `backend/app/scripts/seed_sources_demo.py` (3 sources + 1 admin secondaire) — utilisé par quickstart.md.
- [ ] T143 [P] Mettre à jour `quickstart.md` si écart détecté pendant l'implémentation.
- [ ] T144 [P] Audit RLS : ajouter test `test_rls.py` pour confirmer que la table `source` ne filtre PAS par `account_id` (sources globales) tout en confirmant que les endpoints admin requièrent rôle Admin (F02).
- [ ] T145 [P] Lint & format : `ruff check`, `ruff format`, `mypy` sur `app/catalog/sources` ; `pnpm lint` sur frontend.
- [ ] T146 [P] Ajouter une E2E Playwright `admin-sources.spec.ts::full_lifecycle` couvrant US1+US2+US4+US5 dans un seul scenario.
- [ ] T147 Documenter les helpers F04 `versioning.bump_source_version` et `audit.record` dans le code (docstrings) et lier au plan.md.

---

## Dépendances et ordonnancement

- Phase 1 (T001–T006) : préalable à tout.
- Phase 2 (T010–T023) : bloquant pour toute story (migration, utilitaires, schémas, repository).
- US1 (T030–T040) dépend de Phase 2.
- US2 (T050–T059) dépend de Phase 2 + US1 (création nécessaire pour valider).
- US3 (T070–T076) dépend de Phase 2 (utilise `repository.list_paginated`).
- US4 (T080–T086) dépend de Phase 2 ; T082 utilise tables F08+ avec garde-fous (sinon valeurs zéro).
- US5 (T100–T105) dépend de Phase 2 + US2 (sources `verified` requises pour tests).
- US6 (T120–T123) dépend de Phase 2 (et accès table `unsourced_claim` F03).
- Phase 9 dépend de toutes les stories implémentées.

## Opportunités parallèles

- Tous les tests `[P]` d'une même story peuvent être écrits en parallèle.
- Les pages frontend `[P]` (T037, T038, T040 pour US1 ; T073, T074, T076 pour US3 ; etc.) sont parallélisables entre elles.
- US3, US4, US5, US6 peuvent être travaillés en parallèle après Phase 2 + US1 (US2 reste séquentielle pour ses dépendances métier).

## Stratégie d'implémentation

1. **MVP minimal** : Phase 1 + Phase 2 + US1 (≈ 23 tâches) → permet de saisir des sources `pending`.
2. **MVP P1 complet** : ajouter US2 + US3 + US4 (≈ 22 tâches supplémentaires) → workflow opérationnel pour 50 sources avec impact analysis.
3. **Itération suivante** : US5 (P2, ≈ 6 tâches) puis US6 (P3, ≈ 4 tâches).
4. **Finalisation** : Phase 9 polish (≈ 8 tâches).

Total : 64 tâches.

> Note implementation_strategy : tasks.md > 60 tâches. **Recommandation** : exécuter d'abord P1 (Setup + Foundational + US1 + US2 + US3 + US4 = ~52 tasks) pour livraison MVP, puis P2/US5 et P3/US6 dans une seconde passe d'implémentation. Ces deux dernières stories sont indépendantes et peuvent être différées sans bloquer la valeur métier de F07.

## Critères d'indépendance des stories (rappel)

- US1 → testable seul (créer source en `pending`).
- US2 → testable seul après US1 (workflow verify).
- US3 → testable seul (liste + recherche).
- US4 → testable seul (impact analysis).
- US5 → testable seul (page publique).
- US6 → testable seul (claims non sourcés).

## Validation Module 0

- ✅ Sourcing F03 : F07 gère l'entité Source elle-même.
- ✅ RLS F02 : endpoints admin protégés par rôle, page publique sans données tenant.
- ✅ Audit F04 : helper `audit.record` appelé sur toutes les mutations.
- ✅ Versioning F04 : `bump_source_version` sur changement de champs critiques.
- ✅ Money typé : non applicable.
- ✅ Bottom sheet : non applicable (back-office).
- ✅ Plateforme fermée : page publique en `noindex`, pas de sitemap MVP.
