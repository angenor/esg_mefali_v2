# Quickstart F10 — Support PME Admin & Métriques

## Pré-requis

- Branche `010-admin-support-pme-metrics` checkée out.
- F02, F04, F06 en place (auth+RLS, audit, back-office skeleton).
- Postgres 16 + pgvector running via `docker compose up -d db`.
- Backend `.venv` actif, frontend `pnpm install` fait.
- Variable d'env `RESEND_API_KEY` présente (sinon `EmailSender` tombe en mode `console` qui logue l'email).

## 1. Migrations DB

```bash
cd backend
. .venv/bin/activate
alembic upgrade head
```

Les 4 migrations attendues : `010_a_llm_usage_log`, `010_b_llm_pricing`, `010_c_email_delivery_log`, `010_d_attestation_revocation_columns`.

## 2. Seed grille tarifaire

```bash
python scripts/seed_llm_pricing.py
```

Insère une ligne pour `minimax-m2.7` avec `valid_from=2026-01-01`.

## 3. Lancer l'API

```bash
uvicorn app.main:app --reload --port 8000
```

## 4. Test US3 (reset password) en curl

```bash
TOKEN=<jwt_admin>
USER_ID=<user_pme_uuid>
curl -X POST http://localhost:8000/api/v1/admin/users/$USER_ID/reset-password \
  -H "Authorization: Bearer $TOKEN"
```

Attendu : `202` avec `email_delivery_id`. Vérifier en DB :

```sql
SELECT * FROM email_delivery_log ORDER BY created_at DESC LIMIT 1;
SELECT * FROM audit_log WHERE action='reset_password_request' ORDER BY created_at DESC LIMIT 2;
```

(2 lignes : côté admin + côté PME).

## 5. Test US1+US2 (consultation tracée)

```bash
curl http://localhost:8000/api/v1/admin/pme/$ACCOUNT_ID?section=projets \
  -H "Authorization: Bearer $TOKEN"
```

Vérifier :

```sql
SELECT * FROM audit_log
WHERE entity_type='admin_view' AND entity_id=$ACCOUNT_ID
ORDER BY created_at DESC LIMIT 1;
```

Doit contenir `section='projets'`, `source_of_change='admin'`, `actor_email=<email_admin>`.

## 6. Test US4 (révocation)

```bash
curl -X POST http://localhost:8000/api/v1/admin/attestations/$ATT_ID/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Donnée compromise — incident SEC-2026-01"}'
```

Vérifier `revoked_at`, `revoked_by`, `revoked_reason` sur la ligne, et qu'une seconde tentative renvoie 409.

## 7. Test US5 (dashboard)

```bash
curl http://localhost:8000/api/v1/admin/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"
```

Réponse < 1.5s. Deuxième appel < 60s ⇒ `cached=true`.

## 8. Frontend

```bash
cd frontend
pnpm dev
```

Ouvrir http://localhost:3000/admin/pme avec un compte admin → liste paginée.
Ouvrir http://localhost:3000/admin/dashboard → 5 blocs + chart.

## 9. Tests automatisés

```bash
cd backend && pytest tests/integration/admin -v
cd frontend && pnpm test:unit && pnpm test:e2e -- admin
```

## 10. Critères de succès

- Résolution "PME perdu mot de passe" en < 2 min (chrono manuel).
- 100 % des GET admin produisent audit_log (test automatisé).
- Dashboard < 1.5s P95.
- Révocation propagée < 60s.
