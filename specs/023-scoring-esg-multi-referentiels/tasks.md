# Tasks — F23 Scoring ESG MVP

**Feature** : 023-scoring-esg-multi-referentiels
**Date** : 2026-04-29
**Branch** : `023-scoring-esg-multi-referentiels`

Légende :
- `[P]` task can run in parallel with other [P] tasks within the same phase.
- TDD : tests first (RED) → implémentation (GREEN) → refactor.

## Phase A — Setup

- [ ] **T001** Créer la structure dossier `backend/app/scoring/` avec `__init__.py`.
- [ ] **T002** [P] Créer `backend/tests/scoring/__init__.py` + `backend/tests/scoring/conftest.py` (fixtures référentiel test + entreprise minimale).

## Phase B — Migration & modèle (DB)

- [ ] **T010** Écrire la migration Alembic `backend/alembic/versions/0016_f23_score_calculation.py` (table + index + RLS policies).
- [ ] **T011** Modèle SQLAlchemy `backend/app/models/score_calculation.py` (mappé sur la table).
- [ ] **T012** Test d'intégration : la migration upgrade/downgrade proprement (smoke test via fixture).

## Phase C — Engine de calcul (TDD core)

- [ ] **T020** [P] **TEST** `tests/scoring/test_normalizer.py` :
  - numeric avec seuils → linéaire bornée
  - numeric sans seuils → clamp 0-100
  - boolean → 0/100
  - enum ordonnée → index/(len-1)*100
  - text/json → renvoie None + reason
  - invalid_value (enum hors valeurs) → None + reason
- [ ] **T021** [P] **TEST** `tests/scoring/test_value_source.py` :
  - lookup OK → valeur lue depuis `EntrepriseRow`
  - code inconnu → None + reason `value_source_unmapped`
  - valeur None → None + reason `value_absent`
- [ ] **T022** [P] **TEST** `tests/scoring/test_engine.py` :
  - 3 indicateurs couverts → score = somme pondérée renormalisée
  - 1 indicateur couvert + 2 manquants → score basé sur 1 seul
  - 0 indicateur couvert → score_global = None, scores_by_pillar = {}
  - poids total = 0 → score = None
  - déterminisme : 2 calculs identiques → même score
- [ ] **T023** Implémenter `backend/app/scoring/normalizer.py` pour passer T020.
- [ ] **T024** Implémenter `backend/app/scoring/value_source.py` (avec `VALUE_SOURCE_MAP` couvrant ~5 indicateurs `EntrepriseRow`) pour passer T021.
- [ ] **T025** Implémenter `backend/app/scoring/engine.py` (`compute_score(...)` + `WeightedSumFormula`) pour passer T022.

## Phase D — Service & persistance

- [ ] **T030** [P] **TEST** `tests/scoring/test_service.py` :
  - charge un référentiel publié + ses indicateurs
  - 404 si référentiel `draft` ou inconnu
  - persiste un `score_calculation` après calcul
  - audit log appelé une fois (mock `record_audit`)
- [ ] **T031** Implémenter `backend/app/scoring/service.py` : `compute_and_persist(db, account_id, entity_type, entity_id, referentiel_code, user_id)`.
- [ ] **T032** Implémenter `backend/app/scoring/schemas.py` (Pydantic `ScoreSummary`, `ScoreDetail`, `CoveredIndicator`, `MissingIndicator`).

## Phase E — Endpoints REST

- [ ] **T040** **TEST** `tests/scoring/test_router.py` :
  - `POST /me/scoring/entreprise/{id}/recompute?referentiel=TEST_REF` → 201 + détail
  - `GET /me/scoring/entreprise/{id}` → 200 liste
  - `GET /me/scoring/entreprise/{id}/TEST_REF` → 200 détail
  - 404 référentiel inconnu
  - 404 cross-tenant (entité d'un autre compte)
  - 401 sans auth
- [ ] **T041** Implémenter `backend/app/scoring/router.py` (3 routes, `Depends(get_current_pme)`).
- [ ] **T042** Enregistrer le router dans `backend/app/main.py` (`app.include_router(scoring_router)`).

## Phase F — Lint & coverage

- [ ] **T050** `ruff check backend/app/scoring/ backend/tests/scoring/` — 0 erreur.
- [ ] **T051** `pytest tests/scoring -v --cov=app.scoring --cov-report=term-missing` — couverture ≥ 80 %.
- [ ] **T052** Tests F01-F22 toujours verts (`pytest -q` global).

## Phase G — Documentation manuelle

- [ ] **T060** Renseigner `.cc-runtime/logs/manual-tests-23.md` avec scénarios curl + résultat attendu.

## Out of scope (pas dans cette branche)

- US3 endpoint `/me/scoring/offre/{offre_id}` (activation contextuelle fonds + intermédiaire) — F25.
- US5 benchmark sectoriel.
- US6 historique time-series.
- Recalcul auto debounced via hook F11/F12 save.
- Frontend Vue page `/profil/scoring`.
