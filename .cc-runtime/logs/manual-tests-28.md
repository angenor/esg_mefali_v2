# F28 - Manual tests log

## Automated tests

- `pytest tests/carbon/` -> 27 passed (engine 100%, plan 100%, schemas 100%, service 100%, router 40% ; total app/carbon 85.22%).
- Regression smoke : `pytest tests/simulation/ tests/scoring/` -> 114 passed.
- `ruff check app/carbon/ tests/carbon/` -> All checks passed.

## Manual scenarios (a executer en environnement DB-up post-merge)

1. Migration : `alembic upgrade head` -> verifier creation `carbon_footprint` (RLS, index `ix_carbon_footprint_lookup`).
2. POST `/me/carbon/compute` body
   `{"year":2024,"source_data":[{"code":"ELEC_CIV","quantity":"1500","country":"CI"},{"code":"DIESEL","quantity":"100"}]}`
   -> 200 avec `total_tco2e > 0`, `breakdown[].factor_source_id` non vide, audit log ecrit.
3. GET `/me/carbon/2024` -> 200 + meme footprint.
4. GET `/me/carbon/2024/reduction-plan` -> >= 3 actions priorisees par impact desc.
5. POST avec code introuvable -> 404 `factor_not_found`.
6. RLS : autre PME ne voit pas le footprint d'un autre account_id.

## Deferred (post-MVP)

- Frontend Vue `/profil/carbone`.
- US1 questionnaire conversationnel complet via skill.
- US4 viz F15/F16 (`show_kpi_card`, `show_pie_chart`, `show_bar_chart`, `show_line_chart`).
- US6 objectifs / US7 tool LLM `compute_carbon_footprint`.
- Table `action_reduction` seedee + sources liees.
- Comparaison sectorielle anonymisee.
- Scope 3 exhaustif (achats amont/aval).
- Seed des facteurs UEMOA mix electrique 8 pays.
