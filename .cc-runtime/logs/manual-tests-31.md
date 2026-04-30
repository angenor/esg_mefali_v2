# F31 — Tests manuels

**Feature**: 031-plan-action-rappels-bibliotheque
**Date**: 2026-04-29
**Quickstart**: [specs/031-plan-action-rappels-bibliotheque/quickstart.md](../../specs/031-plan-action-rappels-bibliotheque/quickstart.md)

## État

- Tests automatisés (unit + contract) : **60 passed, 0 failed**, couverture **97 %** sur `app/action_plan/`.
- Tests d'intégration DB live : **DEFERRED** — la base de dev locale ne contient pas le schéma F01-F30 attendu (tables d'un autre projet). Les tests `tests/integration/action_plan/test_*.py` ne sont donc pas livrés (T012, T018-T020). À ajouter dès qu'une base seed F30 sera disponible (CI ou docker-compose propre).

## Smoke commands à dérouler en local (quand DB seed F30 dispo)

- [ ] `alembic upgrade head` — la révision `0021_f31_action_plan` doit s'appliquer.
- [ ] `psql -c "SELECT tablename FROM pg_policies WHERE tablename IN ('action_plan','action_step');"` — `tenant_isolation` x2.
- [ ] `curl -X POST '…/me/action-plan/generate?horizon=12' -H 'Bearer …'` → 201.
- [ ] `curl -X GET '…/me/action-plan' -H 'Bearer …'` → 200.
- [ ] `curl -X PATCH '…/me/action-plan/steps/<id>' -d '{"status":"doing"}'` → 200 + ligne audit_log.
- [ ] Avec un autre token (compte B) : PATCH étape compte A → 404.

## Notes

- Pre-existing DB issue: `account_user`, `score_calculation`, etc. absents de la DB locale → tests d'intégration ne peuvent tourner localement. Bug d'environnement, **pas** de régression F31.
- Les routes sont wirées : `app.openapi()` expose bien `/me/action-plan/generate`, `/me/action-plan`, `/me/action-plan/steps/{step_id}` (vérifié par `test_openapi_contract.py`).
- 468 tests unit non-F31 passent : aucune régression introduite.
