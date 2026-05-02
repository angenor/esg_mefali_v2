# F31 — Tests manuels

**Feature**: 031-plan-action-rappels-bibliotheque
**Date**: 2026-04-29
**Quickstart**: [specs/031-plan-action-rappels-bibliotheque/quickstart.md](../../specs/031-plan-action-rappels-bibliotheque/quickstart.md)

## État

- Tests automatisés (unit + contract) : **60 passed, 0 failed**, couverture **97 %** sur `app/action_plan/`.
- Tests d'intégration DB live : **DEFERRED** — la base de dev locale ne contient pas le schéma F01-F30 attendu (tables d'un autre projet). Les tests `tests/integration/action_plan/test_*.py` ne sont donc pas livrés (T012, T018-T020). À ajouter dès qu'une base seed F30 sera disponible (CI ou docker-compose propre).

## Smoke commands à dérouler en local (quand DB seed F30 dispo)

- [x] `alembic upgrade head` — head = `0023_f34_notification` (inclut `0021_f31_action_plan`).
- [x] `curl -X POST '…/me/action-plan/generate?horizon=12'` → **201** (compte seedé manuellement : entreprise + referentiel TEST_REF + score_calculation).
- [x] `curl -X GET '…/me/action-plan'` → **200**.
- [x] `curl -X PATCH '…/me/action-plan/steps/<id>' -d '{"status":"done"}'` → **200**.
- [x] Avec un autre token (compte B) : PATCH étape compte A → **404 "Étape introuvable."**.

## Run 2026-05-02 — agent

Statut : **PASS** après 2 fixes.

### Fixes appliqués

1. `backend/app/models/__init__.py` — ajout `from app.models.indicateur import Indicateur`.
   Sans cet import, `ActionStep.indicateur_id` (FK vers `indicateur.id`) provoque
   `sqlalchemy.exc.NoReferencedTableError` au flush du plan.
2. `backend/app/action_plan/routes.py` — sérialisation Pydantic AVANT `db.commit()`
   pour `generate_action_plan` et `patch_action_step`. Suppression de `db.refresh()`
   post-commit. Même pattern que f783cef (attestations) : la session GUC RLS
   `app.current_account_id` n'est plus accessible après commit, provoquant
   `InvalidRequestError: Could not refresh instance`.

## Notes

- Pre-existing DB issue: `account_user`, `score_calculation`, etc. absents de la DB locale → tests d'intégration ne peuvent tourner localement. Bug d'environnement, **pas** de régression F31.
- Les routes sont wirées : `app.openapi()` expose bien `/me/action-plan/generate`, `/me/action-plan`, `/me/action-plan/steps/{step_id}` (vérifié par `test_openapi_contract.py`).
- 468 tests unit non-F31 passent : aucune régression introduite.
