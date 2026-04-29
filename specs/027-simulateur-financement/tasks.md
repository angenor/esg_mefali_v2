# Tasks: F27 — Simulateur de Financement

**Branch**: `027-simulateur-financement` | **Plan**: [plan.md](./plan.md)

## TDD ordering

Chaque US suit RED -> GREEN -> REFACTOR. Tests d'abord.

## T-001 — Schemas Pydantic [P1, US1, US2, US3]

- Créer `backend/app/simulation/__init__.py`, `schemas.py`.
- `SimulationHypotheses` (frozen, extra=forbid) : `taux_interet_pct: Decimal | None`, `duree_mois: int | None`, `garantie_pct: Decimal | None`.
- `SimulationResult` (frozen) : voir spec §6.
- `SimulationRequest`, `ComparatorRequest`.

## T-002 — Calculator primitives [P1, US1, US2, US3]

- Tests unitaires `test_calculator.py` :
  - `convert_to_xof(money)` : XOF->XOF identique, EUR->XOF via peg, autre->None.
  - `interets_simples(principal, taux_pct, duree_mois)` : 0 si taux=0, math correcte sur 7 ans.
  - `compute_pct_of(money, pct)` : applique pct sur amount.
  - `extract_pct(json, *keys)` : retourne Decimal ou None.
- Implémentation `calculator.py`.

## T-003 — Service simulate [P1, US1, US2]

- Tests `test_service.py` :
  - Cas subvention -> cout_total=0, interets=0.
  - Cas prêt simple -> cout_total = marge+frais+interets, sources cumulées.
  - Cas equity -> dilution_warning=true.
  - Projet inconnu -> ProjetNotFound. Offre inconnue -> OffreNotFound.
- Implémentation `service.py` avec SQL `_load_projet` (réutilise pattern F25) et `_load_offre_full`.

## T-004 — Conversion XOF/EUR + change risk [P1, US3]

- Tests : Offre EUR -> equivalent_xof OK, change_risk=false. Offre USD -> change_risk=true, equivalent_xof=None, unknown_fields contient 'fx_rate'.
- Implémentation dans `service.py`.

## T-005 — Comparator [P1, US6]

- Tests : 3 offres -> 3 rows triés par cout_total asc. Validation 2 <= len(offre_ids) <= 5. Doublons rejetés.
- Implémentation `service.compare(...)`.

## T-006 — Router HTTP [P1, US1, US6]

- Tests `test_router.py` :
  - POST `/me/simulations` 200 + JSON valide.
  - POST avec UUID inconnu -> 404.
  - POST `/me/simulations/comparator` 200 avec 3 offres.
  - Validation longueur offre_ids.
- Implémentation `router.py` + enregistrement dans `app/main.py`.

## T-FINAL — Lint, coverage, manual tests

- `pytest backend/tests/simulation -v --cov=app/simulation --cov-report=term-missing` >= 80 %.
- `ruff check backend/app/simulation backend/tests/simulation`.
- Manual tests log dans `.cc-runtime/logs/manual-tests-27.md`.
- Re-vérification constitution post-impl.

## Hors scope (DEFERRED)

- US4 impact CO2e — F28.
- US5 timeline frontend.
- US7 tool LLM `simulate_financing`.
- Frontend Nuxt.
