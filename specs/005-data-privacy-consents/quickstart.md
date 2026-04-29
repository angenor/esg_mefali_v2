# Quickstart F05 — Data Privacy & Consents

## Prérequis
- F01 (tables fondations + Money type) appliqué.
- F02 (auth + RLS + middleware `app.current_account_id`).
- F03 (sources + middleware validation LLM).
- F04 (audit_log append-only, helpers `record_audit`, `publish_new_version`, trigger `audit_log_immutable`).
- Postgres 16 + pgvector dockerisé.
- `.env` avec `EXCHANGERATE_API_KEY`, `PURGE_PSEUDONYM_PEPPER`, `FX_DEFAULT_DISPLAY_CURRENCY=XOF`, `FX_STALE_ALERT_DAYS=7`.

## Bootstrap backend
```bash
cd backend && source .venv/bin/activate
alembic upgrade head           # applique migrations 005a-h
uvicorn app.main:app --reload  # démarre FastAPI + APScheduler
```

## Bootstrap frontend
```bash
cd frontend && pnpm install && pnpm dev
```

## Vérifications manuelles

### Page Mes données
1. Login PME → `GET /me/donnees/summary` retourne agrégats.
2. `GET /me/donnees/export` télécharge un ZIP. Ouvrir : présence de `manifest.json`, `entities/*.json`, dossier `files/`. Vérifier hashes SHA-256.

### Suppression différée
1. `POST /me/donnees/delete` → 202 + `effective_at = now+30d`.
2. `DELETE /me/donnees/delete` → 200, status `cancelled`.
3. Forcer le job : `python -m app.jobs.purge_pending_deletions --run-now` (mode test).
4. Lancer script de vérification : `python scripts/verify_purge.py <account_id>` → 0 ligne tenant-scoped restante, audit_log porte `anon_<hash>`.

### Consentements
1. `GET /me/consentements` → essentiels seulement actifs.
2. `POST /me/consentements/mobile_money {given:true}` → entrée audit `manual`.
3. Endpoint protégé `@requires_consent('mobile_money')` désactivé → 403 `{error:'consent_required',kind:'mobile_money'}`.

### Politique versionnée
1. Admin : publish v1.0.0 (`is_major=true`).
2. PME login → middleware redirige `/me/policy-reaccept`. Bottom sheet `PolicyReacceptSheet` affiché.
3. Accepter → `POST /me/policy-acceptance` → entry `consent_acceptance`.

### Devises
1. `POST /fx/convert {money:{amount:"1000",currency:"XOF"},to:"EUR"}` → ~1.524 EUR (peg).
2. `to:"USD"` → valeur cohérente (snapshot).
3. Couper exchangerate-api.com (env override) → job échoue, ligne `scheduled_job_run.status=failed`, conversion utilise dernier taux connu.

### Bottom sheets
- Toggle consent → `ConsentToggleSheet` glisse depuis le bas.
- Confirm delete → `DeletionConfirmSheet`.
- Ré-acceptation → `PolicyReacceptSheet` bloquante.

## Tests
```bash
# backend
pytest tests/unit/test_money.py
pytest tests/unit/test_pseudonymize.py
pytest tests/integration/test_purge_flow.py
pytest tests/integration/test_export_zip.py
pytest tests/contract/test_privacy_api.py
# frontend
pnpm test
pnpm exec playwright test e2e/privacy.spec.ts
```

## Hooks de fin
- Vérifier `scheduled_job_run` quotidiennement.
- Surveiller `consecutive_failed_days` pour `refresh_fx_rates`.
