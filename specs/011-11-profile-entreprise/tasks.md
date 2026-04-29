# Tasks: F11 — Profil Entreprise

**Branch**: `011-11-profile-entreprise`

## Phase 0 — Setup

- [ ] T001 — Migration alembic `0010_f11_entreprise_enrich.py` : ajouter colonnes (secteur_code, secteur_label, localisation_siege_pays_iso2, localisation_siege_ville, zones_operation_pays_iso2[], gouvernance_json), contrainte UNIQUE account_id, index secteur_code.

## Phase 1 — Backend US1+US2+US3 (P1)

### Tests d'abord (RED)

- [ ] T010 — `tests/unit/entreprise/test_schemas.py` : Pydantic schemas IN/OUT — bornes effectifs 0–10000, devises {XOF, EUR, USD}, ISO2 UEMOA/CEDEAO valid/invalid.
- [ ] T011 — `tests/unit/entreprise/test_taxonomy.py` : liste sectors ≥ 30 entrées, codes uniques, label fr non vide.
- [ ] T012 — `tests/unit/entreprise/test_completeness.py` : 0% si vide ; 100% si tous champs requis remplis ; matrice features→champs déclarative.
- [ ] T013 — `tests/unit/entreprise/test_provenance.py` : agrégation audit_log → dernière mutation par champ.
- [ ] T020 — `tests/integration/entreprise/test_entreprise_get.py` : GET /me/entreprise renvoie 200 même profil vierge ; 401 sans token.
- [ ] T021 — `tests/integration/entreprise/test_entreprise_patch.py` : PATCH met à jour secteur/effectifs/CA, version++, audit_log écrit avec source_of_change=manual.
- [ ] T022 — `tests/integration/entreprise/test_entreprise_put_ifmatch.py` : PUT avec If-Match correct → 200 ; If-Match stale → 409 body {current_version, your_version}.
- [ ] T023 — `tests/integration/entreprise/test_entreprise_completeness.py` : completeness retourne percentage ∈ [0,100] et missing_required_for_features.
- [ ] T024 — `tests/integration/entreprise/test_entreprise_sectors.py` : GET /me/entreprise/sectors renvoie ≥ 30 secteurs ; 401 sans token.
- [ ] T025 — `tests/integration/entreprise/test_entreprise_rls.py` : un user d'un autre account ne peut ni lire ni écrire l'entreprise d'autrui (RLS).
- [ ] T026 — `tests/integration/entreprise/test_entreprise_audit.py` : chaque champ modifié → un enregistrement audit_log distinct.

### Implémentation (GREEN)

- [ ] T030 — `app/models/entreprise.py` : ORM SQLAlchemy.
- [ ] T031 — `app/entreprise/taxonomy.py` : SECTORS (~50 codes) + UEMOA_CEDEAO_ISO2.
- [ ] T032 — `app/entreprise/schemas.py` : Pydantic v2 (EntrepriseRead, EntrepriseFieldMeta, EntreprisePatchIn, EntreprisePutIn, MoneyIn, ConflictOut).
- [ ] T033 — `app/entreprise/completeness.py` : config matrice + calcul.
- [ ] T034 — `app/entreprise/provenance.py` : query audit_log → dict {field: meta}.
- [ ] T035 — `app/entreprise/service.py` : get_or_provision_entreprise, update_partial (transactionnel + audit + version++), put_full.
- [ ] T036 — `app/entreprise/events.py` : pub/sub asyncio in-process + SSE generator.
- [ ] T037 — `app/api/routes/entreprise.py` : routes FastAPI.
- [ ] T038 — `app/main.py` : enregistrer router AVANT le wildcard `/admin/{entity}/{id}` (route distincte de toute façon).

## Phase 2 — US5 complétude (P2)

- (couvert par T012 + T023 + T033 + endpoint T037)

## Phase 3 — US6 multi-utilisateurs (P3)

- (couvert par T022 — If-Match + 409)

## Phase 4 — Frontend (DEFERRED)

- [DEFERRED] T100 — Page Nuxt `/profil/entreprise` (US1 UI).
- [DEFERRED] T101 — Composables `useEntreprise`, `useEntrepriseEvents` (SSE), `useEntrepriseCompleteness`.
- [DEFERRED] T102 — Composants form-builder par section (bottom sheet mobile).
- [DEFERRED] T103 — Tests Vitest/Playwright.

Raison du report: scope backend P1+P2+P3 prioritaire pour invariants Module 0 ; frontend non bloquant pour intégration F12+/F13+.

## Tests manuels (à jouer hors session)

Référence: `.cc-runtime/logs/manual-tests-11.md`.
