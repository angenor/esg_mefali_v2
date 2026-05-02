# Manual tests F32 — Dashboard PME (MVP backend agrégateur)

Date : 2026-04-30
Branche : `032-dashboard-pme-rapports`

## Scope livré

- `GET /me/dashboard/summary` — agrégat lecture seule (scores, carbone,
  credit_score, candidatures, rapports, attestations, next_actions).
- `GET /me/data/export` — export JSON complet du compte PME.
- Audit `dashboard_view` / `data_export` (best-effort, ne casse pas la requête).

## Tests automatisés

```
$ pytest tests/dashboard/ --cov=app/dashboard --cov-report=term-missing
37 passed
```

| Module | Couverture |
|--------|-----------|
| `app/dashboard/__init__.py` | 100 % |
| `app/dashboard/router.py` | 100 % |
| `app/dashboard/schemas.py` | 100 % |
| `app/dashboard/service.py` | 100 % |
| **TOTAL** | **100 %** |

Tests intégration (`tests/integration/dashboard/`) écrits, gated par
`@requires_db` ; ils s'exécutent quand Postgres est migré. Le DB local de cette
machine a un état alembic stale `10c0pydantic_validation` non lié à F32, donc
les tests integration F32 et d'autres tests integration existants (consent,
etc.) sont skippés pareillement — pas de régression introduite par F32.

## Non-régression

Sweep `pytest tests/scoring tests/attestations tests/rapports tests/carbon
tests/credit tests/simulation tests/projets tests/entreprise tests/services
tests/unit tests/api tests/orchestrator tests/tools tests/test_health.py
tests/test_schema.py --no-cov` : **1073 passed, 6 failed (pré-existants,
migration smoke tests sur DB locale unmigrated), 31 skipped**.

Aucune régression sur F01-F31 introduite par F32.

## Lint

```
$ ruff check app/dashboard tests/dashboard tests/integration/dashboard
All checks passed!
```

## Run 2026-05-02 — agent (smoke routes)

- [x] `GET /me/dashboard/summary` → **200** : scores (TEST_REF), carbon, candidatures, attestations, next_actions OK.
- [x] `GET /me/data/export` → **200** après fix.

### Fix appliqué

`backend/app/dashboard/service.py` — `build_export()` lisait `SELECT id, type FROM account`
mais la table `account` n'a pas de colonne `type` (schéma : id, name, created_at, updated_at).
Remplacé par `SELECT id, name`. Provoquait `psycopg.errors.UndefinedColumn` → 500.

## Hors-scope (DEFERRED)

- US2 graphes 12 mois.
- US4 carte Leaflet intermédiaires.
- US7 endpoint historique audit log dédié (couvert par F04 `/me/audit-log`).
- US8 multi-utilisateurs (invitation, listing, révocation).
- US9 commentaires sur projets/candidatures.
- Frontend Vue (`pages/dashboard/*`, `components/dashboard/*`).
- Page `/dashboard/exports` listing fichiers téléchargeables.
