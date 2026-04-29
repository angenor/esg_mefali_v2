# Implementation Plan: F27 — Simulateur de Financement

**Branch**: `027-simulateur-financement` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Service de simulation financière qui combine les frais offre + frais intermédiaire + frais fonds (cumulés depuis F08), produit un `SimulationResult` Pydantic, et expose deux endpoints PME RLS-actés. Aucune table nouvelle (FR-008). Conversion FCFA-EUR utilisant la constante `PEG_FCFA_EUR` (`app/core/currencies.py`).

## Technical context

- **Language**: Python 3.11
- **Framework**: FastAPI + SQLAlchemy 2.x (raw `text()` queries, conformes au pattern F25)
- **Schemas**: Pydantic v2 immutable (`frozen=True`)
- **Tests**: pytest + pytest-asyncio + httpx
- **Pas de migration Alembic**.
- **Pas de Redis** : pas de cache.
- **RLS** : déléguée à la session SQL initialisée par `get_db` + `current_user`.

## Architecture

```
backend/app/simulation/
├── __init__.py
├── schemas.py         # SimulationResult, SimulationHypotheses, ComparatorRequest
├── service.py         # simulate(...) + compare(...)
├── calculator.py      # primitives pures : interets_simples, montant_eligible, peg_xof_eur
└── router.py          # POST /me/simulations, /me/simulations/comparator

backend/tests/simulation/
├── __init__.py
├── test_calculator.py     # tests unitaires purs (pas de DB)
├── test_service.py        # tests service avec DB fixture
└── test_router.py         # tests intégration httpx
```

## Méthodologie de calcul (P1, documentée)

1. **Montant éligible** = `min(projet.montant_recherche, fonds.plafond_money)` (clipping plancher si applicable). Si devises différentes, conversion via peg fixe (XOF ↔ EUR uniquement) — sinon `unknown_fields += ["fx_rate"]`.
2. **Marge intermédiaire** = `intermediaire.frais_json.marge_pct * montant_eligible`. Si `marge_pct` absent → `unknown_fields += ["marge_intermediaire"]`.
3. **Frais de dossier** = `offre.frais_specifiques.frais_dossier_pct * montant_eligible` ou montant fixe si `frais_dossier_montant` (Money). Fallback fonds.
4. **Garantie exigée** (informative, hors coût) = `offre.frais_specifiques.garantie_pct * montant_eligible`.
5. **Intérêts cumulés** (intérêts simples MVP, NFR doc) = `taux_interet_pct/100 * montant_eligible * duree_mois/12`. Si `instrument='subvention'` → 0. Si `instrument='equity'` → 0 + `dilution_warning=true`.
6. **Coût total** = `marge + frais_dossier + interets_cumules`. Garantie n'est PAS un coût (mobilisation), juste informative.
7. **Coût total pct** = `cout_total / montant_eligible * 100`.
8. **Equivalent XOF** : si devise = EUR → multiplier par `PEG_FCFA_EUR`. Si XOF → identique. Sinon `change_risk=true` + `change_rate_unknown=true`.

## Endpoints

```
POST /me/simulations
Body: { projet_id: UUID, offre_id: UUID, hypotheses?: SimulationHypotheses }
→ 200 SimulationResult
→ 404 ProjetNotFound | OffreNotFound

POST /me/simulations/comparator
Body: { projet_id: UUID, offre_ids: list[UUID] (2..5) }
→ 200 ComparatorResult { rows: [SimulationResult, ...] tri par cout_total asc }
```

## Constitution gates

Pré-implémentation : tous OK (voir spec §7).
Post-implémentation : à re-vérifier dans tasks T-FINAL.

## Phases

- **Phase 0** (research) : terminée — pattern F25 réutilisé.
- **Phase 1** (design) : ce plan + schemas Pydantic figés.
- **Phase 2** (tasks) : voir [tasks.md](./tasks.md).
- **Phase 3** (impl) : TDD strict, RED → GREEN → REFACTOR.

## Risques

- **Frais hétérogènes** : `frais_json` peut contenir clés variables. → Helper `_extract_pct(json, key)` tolérant + `unknown_fields`.
- **Devises exotiques** : pas de FxService en place. → P1 limité à XOF/EUR via peg ; autres devises → flag.
- **Performance** : simple SELECT + calcul Python pur → bien < 200 ms.
