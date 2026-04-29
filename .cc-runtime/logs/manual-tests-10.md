# Manual tests — F10 (Admin Support PME & Métriques)

Branche : `010-admin-support-pme-metrics`
Stratégie d'implémentation : MVP partiel (T001/T014/T015/T016/T017/cache T047 partiel + US1 + US2).
US3 / US4 / US5 (full) / US6 / migrations T005..T013 + frontend Vue / retry email / templates : **DEFERRED**.

## Scope livré

- Dossiers backend `app/admin/{routes,services}`, `app/email`, `app/llm` créés (T001).
- `require_admin` (alias F02) + whitelist mutations admin documentée (T014).
- `app.audit.admin_view.audit_admin_view` + enum `AdminViewSection` 7 valeurs, fail-closed (T015).
- `app.admin.services.pii_filter.mask_pii` (email/tel/IBAN/CIN) (T016).
- `EmailSender` Protocol + `ConsoleEmailSender` + stub `ResendEmailSender` (T017 partiel).
- `app.admin.services.dashboard_stats` : TTLCache 60s + invalidate (T047 primitive seulement).
- `GET /admin/pme` (US1) — liste paginée + recherche, admin-only.
- `GET /admin/pme/{account_id}?section=…` (US1+US2) — détail lecture seule + audit `admin_view` fail-closed.

## Tests manuels

### MT-01 — Liste PME admin

1. Connexion admin `POST /auth/login`.
2. `GET /admin/pme?limit=10` → 200, JSON `{ items: [...], total, limit, offset }`.
3. `GET /admin/pme?q=foo` → 200, filtrage ILIKE sur `name` + `account_user.email`.
4. PME (non-admin) accédant à `/admin/pme` → 403.

### MT-02 — Détail PME + audit_view

1. Créer 1 compte PME (via `/auth/register`).
2. Admin : `GET /admin/pme/{account_id}?section=projets` → 200, payload `{ account, section: "projets", overview, ... }`.
3. SQL : `SELECT count(*) FROM audit_log WHERE entity_type='admin_view' AND entity_id=:account_id AND field='section.projets' AND source_of_change='admin'` → ≥ 1.
4. `?section=hacked` → 422 (enum strict).
5. ID inconnu → 404.

### MT-03 — PII mask

1. `python -c "from app.admin.services.pii_filter import mask_pii; print(mask_pii('Contact john@x.com +212612345678'))"` → contient `[REDACTED]`.

## Régression F01–F09

`pytest --cov` : **444 passed, 5 skipped, coverage 83.56 %** (baseline F09 = 422 / 83.08 %).
`ruff check .` : All checks passed.

## Différé (DEFERRED — à instancier en F10.1+)

- T005..T013 : migrations `llm_usage_log`, `llm_pricing`, `email_delivery_log`, colonnes `attestation.revoked_*`, indexes pg_trgm + modèles SQLAlchemy.
- T018, T019 : retry email + templates Jinja.
- T020 : hook `log_llm_usage` branché dans `llm_client`.
- T026..T030 : composables / composants / pages / E2E Playwright frontend (Nuxt) — pas de couche Vue dans cette livraison.
- T031..T035 (US2 frontend widget + projection PME complète).
- T036..T040 (US3 reset password admin) ; T041..T045 (US4 revoke/regenerate attestation).
- T046..T049 (US5 dashboard agrégats SQL + front).
- T050 (US6 LLM usage chart).
- T051..T057 (cross-cutting whitelist guard, mask_pii sur attestation publique, perf P95, audit feed front).

Ces tâches dépendent en grande partie des features amont (F11 entreprise, F12 projets, F23 scoring, F30 attestation) qui n'existent pas encore — l'aggrégation détail (`projets`, `candidatures`, `scores`, `attestations`) renverra des listes vides tant que ces features ne sont pas livrées. La structure (sections enum + audit_admin_view + routes) est en place pour brancher ces données dès que les tables seront introduites.
