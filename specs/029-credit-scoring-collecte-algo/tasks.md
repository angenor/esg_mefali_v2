# Tasks F29 — Credit Scoring Collecte & Algo (MVP)

**Spec**: [spec.md](./spec.md) — **Plan**: [plan.md](./plan.md)

## Phase A — Modèles & migration

- **T001** — Modèles SQLAlchemy `app/models/credit_data.py` et `app/models/credit_score.py`.
- **T002** — Migration alembic `0019_f29_credit.py` : tables `credit_data`, `credit_score`, RLS, index.

## Phase B — Engine pur (TDD RED→GREEN)

- **T003** — `app/credit/engine.py` : `compute_factor`, `compute_solvabilite`, `compute_impact_vert`, `compute_combined`. Fonctions pures, pas de DB.
- **T004** — Tests `tests/unit/credit/test_engine.py` couvrant : facteurs nominaux, facteurs absents (value=null, contribution=0), bornes 0..100, coherence_warning, formules α/β.

## Phase C — Parser CSV

- **T005** — `app/credit/csv_parser.py` : lecture CSV générique normalisé (`date_iso`, `amount_xof`, `direction`, `counterparty?`), validation stricte, indicateurs dérivés.
- **T006** — Tests `tests/unit/credit/test_csv_parser.py` : OK nominal, colonne manquante (400), > 10 000 lignes (413), encodage invalide.

## Phase D — Service & seed méthodologie

- **T007** — `app/credit/methodology_seed.py` : seed idempotent du `Referentiel(kind='credit_scoring_methodology', version=1, status='published')` + critères (facteurs et poids) attachés à des sources F03 existantes (fail-closed si aucune source publiée).
- **T008** — `app/credit/service.py` : `submit_credit_data`, `submit_mobile_money_csv`, `recompute_score` (advisory lock + audit append-only), `get_latest_score`, `get_methodology(version?)`.

## Phase E — Endpoints

- **T009** — `app/credit/router.py` :
  - `POST /me/credit-data` (RequiresConsent gated par kind, payload Pydantic, audit),
  - `POST /me/credit-data/mobile-money` (UploadFile, taille ≤ 5 MB, ≤ 10 000 transactions, RequiresConsent MOBILE_MONEY),
  - `POST /me/credit-score/recompute` (advisory lock + audit, append-only),
  - `GET /me/credit-score` (404 si aucun),
  - `GET /methodologie/credit-scoring` (no-auth, paramètre `version` optionnel).
- **T010** — Wire-up dans `app/main.py` (`include_router(credit_router)`).

## Phase F — Tests intégration

- **T011** — `tests/integration/credit/test_router.py` : US1 (recompute → score), US2 (POST credit-data + CSV), US3 (méthodologie publique versionnée), 403 sans consentement Mobile Money, 413 dépassement, 404 GET sans score.

## Phase G — Docs & manual tests

- **T012** — `.cc-runtime/logs/manual-tests-29.md` : scénarios manuels, payload exemples, commandes curl.

## Quality Gate

- [ ] `pytest backend/tests/unit/credit backend/tests/integration/credit -q` vert.
- [ ] Couverture du package `app/credit` ≥ 80 %.
- [ ] `ruff check backend/app/credit backend/tests/unit/credit backend/tests/integration/credit` propre.
- [ ] `alembic upgrade head` réussi sur DB locale.
- [ ] Pas de régression sur F23 / F28 / F05 / F09.

## DEFERRED (hors MVP)

- Page Vue `/profil/credit-score` et `/methodologie/credit-scoring`.
- Mappers CSV Wave / Orange Money / MTN / Free Money.
- Skill LLM `skill_credit_score` orchestration (collecte par questions ask_*).
- Analyse photos via LLM multimodal.
- Scraping social / Google Business.
- API live Mobile Money.
