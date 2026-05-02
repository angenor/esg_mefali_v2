# F29 - Credit Scoring Collecte & Algo - manual tests

## Prealables

- `.venv` activee, Postgres up (`docker compose up -d postgres`).
- `alembic upgrade head` (migration 0019 inclut credit_data + credit_score).
- PME loggee + entreprise rattachee (F11) + consentements F05 actifs (`mobile_money` pour CSV upload, `exploitation_photos` si kind=photos).

## Scenarios

### S1 - Collecte declarative

```bash
curl -X POST http://localhost:8000/me/credit-data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"declaratif","payload":{"paiements_reguliers":true,"diversification_clients":7,"nb_odd_alignes":3}}'
```

Attendu : 200, `id` UUID, `kind=declaratif`, `payload_json` echo, `uploaded_at` ISO.

### S2 - Upload CSV Mobile Money

CSV minimal (`mm.csv`) :

```
date_iso,amount_xof,direction,counterparty
2026-04-01,150000,in,client_a
2026-04-15,80000,out,fournisseur
2026-05-02,200000,in,client_b
2026-05-20,50000,out,
```

```bash
curl -X POST http://localhost:8000/me/credit-data/mobile-money \
  -H "Authorization: Bearer $TOKEN" \
  -F statement=@mm.csv
```

Attendu : 200, `payload_json.indicators.nb_transactions=4`, `monthly_mean_xof=240000`.

### S3 - Recompute score

```bash
curl -X POST http://localhost:8000/me/credit-score/recompute \
  -H "Authorization: Bearer $TOKEN"
```

Attendu : 200, scores `solvabilite/impact_vert/combine` dans [0,100], `methodologie_version=1`, liste `facteurs` non vide.

### S4 - Lecture dernier score

```bash
curl http://localhost:8000/me/credit-score \
  -H "Authorization: Bearer $TOKEN"
```

Attendu : 200 si score persiste, 404 sinon.

### S5 - Methodologie publique

```bash
curl http://localhost:8000/methodologie/credit-scoring
curl http://localhost:8000/methodologie/credit-scoring?version=1
```

Attendu : 200 sans auth, JSON avec `version`, `alpha`, `beta`, `factors`.

### S6 - Refus consentement

PME sans consentement `mobile_money` actif :

```bash
curl -X POST http://localhost:8000/me/credit-data/mobile-money \
  -H "Authorization: Bearer $TOKEN" \
  -F statement=@mm.csv
```

Attendu : 403 `{"error":"consent_required","kind":"mobile_money"}`.

### S7 - CSV trop volumineux

Fichier > 5 MB ou > 10 000 lignes -> 413 `statement_too_large`.

### S8 - CSV invalide

Header sans `direction` -> 400 `statement_invalid` (message `colonnes manquantes`).

## Verifications complementaires

- Audit log : `SELECT * FROM audit_log WHERE entity_type IN ('credit_data','credit_score') ORDER BY timestamp DESC LIMIT 5;`
- Append-only `credit_score` : recompute deux fois et verifier `SELECT count(*) FROM credit_score WHERE entreprise_id=...` augmente.
- Advisory lock : deux recompute simultanes -> executes en serie.
- RLS : un autre account_id ne voit pas les lignes.

## Resultats automatises

- `pytest tests/credit/test_engine.py tests/credit/test_csv_parser.py` : 21 PASS.
- `pytest tests/credit tests/carbon` : 48 PASS (pas de regression F28).
- `ruff check app/credit tests/credit alembic/versions/0019_f29_credit.py` : All checks passed.
- Couverture `app/credit` : engine 98%, csv_parser 90%. Service/router/schemas non couverts par integration en MVP (DEFERRED).

## DEFERRED (hors MVP)

- Tests integration avec auth + DB seedee.
- Page Vue `/profil/credit-score` et `/methodologie/credit-scoring`.
- Mappers CSV Wave / Orange Money / MTN / Free Money.
- Skill LLM `skill_credit_score` orchestration.
- Analyse photos via LLM multimodal.
- Scraping social / Google Business.
- API live Mobile Money.
