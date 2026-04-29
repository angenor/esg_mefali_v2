# Tasks F28 — Empreinte Carbone (MVP)

**Branch**: `028-empreinte-carbone-complete`

Modules MVP (5 livrés, reste DEFERRED) :

1. **T01** — Modèle SQLAlchemy `CarbonFootprint` + migration Alembic 028.
2. **T02** — `engine.py` : `compute_line`, `compute_total` (pures).
3. **T03** — `service.py` : `CarbonService.compute_footprint`, `get_latest`, lookup F09 + record_audit + persistance.
4. **T04** — `plan.py` : bibliothèque inline + `generate_plan(breakdown, year)` >= 3 actions.
5. **T05** — `router.py` + schemas Pydantic + montage `app/main.py`.
6. **T06** — Tests unit (engine, plan) + intégration (router happy path + RLS).

## Tâches DEFERRED

- Frontend Vue `/profil/carbone`.
- US1 questionnaire conversationnel complet (skill).
- US4 viz F15/F16.
- US6 objectifs / US7 tool LLM.
- Table `action_reduction` seedée.
- Comparaison sectorielle.
- Scope 3 exhaustif.
