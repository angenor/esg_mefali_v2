# Quickstart — F31 Plan d'Action MVP

**Feature**: 031-plan-action-rappels-bibliotheque
**Date**: 2026-04-29

## Objectif

Valider en local que :

1. La migration Alembic crée les tables `action_plan` et `action_step` avec RLS active.
2. `POST /me/action-plan/generate?horizon=12` produit un plan basé sur le dernier `ScoreCalculation` (F23) de la PME.
3. `GET /me/action-plan` renvoie le plan courant.
4. `PATCH /me/action-plan/steps/{id}` met à jour `status` et `responsible_user_id`.
5. RLS bloque tout accès cross-tenant (404).

## Pré-requis

- Backend lancé en local (`.venv` Python 3.11, FastAPI, Postgres dockerisé via `docker compose up postgres`).
- Une PME seed (`account` + `account_user` rôle `pme`) avec au moins un `ScoreCalculation` produit par F23.
- Token JWT PME en variable `$TOKEN` (utiliser le helper de dev existant).

## Étape 1 — Migration

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic current
# attendu : 0021_f31_action_plan
```

Vérifier les politiques RLS :

```sql
SELECT tablename, policyname FROM pg_policies
 WHERE tablename IN ('action_plan','action_step');
-- attendu : action_plan_isolation, action_step_isolation
```

## Étape 2 — Génération

```bash
curl -i -X POST "http://localhost:8000/me/action-plan/generate?horizon=12" \
  -H "Authorization: Bearer $TOKEN"
```

Attendu : `201 Created` avec un body de la forme :

```json
{
  "id": "00000000-0000-0000-0000-000000000010",
  "account_id": "00000000-0000-0000-0000-000000000001",
  "horizon_months": 12,
  "version": 1,
  "score_calculation_id": "00000000-0000-0000-0000-000000000002",
  "generated_at": "2026-04-29T10:00:00Z",
  "steps": [
    {
      "id": "00000000-0000-0000-0000-000000000020",
      "plan_id": "00000000-0000-0000-0000-000000000010",
      "title": "Combler l'indicateur ESG-E1 (Émissions GES Scope 1)",
      "category": "carbone",
      "priority": "haute",
      "horizon_at": "2026-08-29",
      "status": "todo"
    }
  ]
}
```

Cas d'erreur :

- Sans `ScoreCalculation` : `422` `{"detail":"Aucun score ESG disponible..."}`.
- `horizon=8` : `422` (FastAPI valide enum {6,12,24}).

## Étape 3 — Lecture

```bash
curl -i -X GET http://localhost:8000/me/action-plan \
  -H "Authorization: Bearer $TOKEN"
```

Attendu : `200 OK` avec les étapes triées par priorité décroissante puis `horizon_at` croissant.

## Étape 4 — Mise à jour d'une étape

```bash
STEP_ID="00000000-0000-0000-0000-000000000020"
curl -i -X PATCH "http://localhost:8000/me/action-plan/steps/$STEP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"doing"}'
```

Attendu : `200 OK`, body avec `status: "doing"`. Vérifier dans `audit_log` qu'une ligne `update` apparaît :

```sql
SELECT id, table_name, action, source_of_change, created_at
  FROM audit_log
 WHERE table_name = 'action_step'
 ORDER BY created_at DESC LIMIT 5;
```

## Étape 5 — RLS cross-tenant

Avec un autre token `$TOKEN_B` (compte différent) :

```bash
curl -i -X PATCH "http://localhost:8000/me/action-plan/steps/$STEP_ID" \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"status":"done"}'
```

Attendu : `404 Not Found`.

## Étape 6 — Régénération

```bash
curl -X POST "http://localhost:8000/me/action-plan/generate?horizon=12" \
  -H "Authorization: Bearer $TOKEN"
# version doit passer à 2
```

Vérifier en SQL :

```sql
SELECT version, generated_at FROM action_plan
 WHERE account_id = current_setting('app.current_account_id')::uuid
 ORDER BY version DESC;
-- attendu : 2 lignes (versions 1 et 2)
```

## Tests automatisés

```bash
cd backend
.venv/bin/pytest tests/unit/action_plan tests/integration/action_plan tests/contract/action_plan -v --cov=app/action_plan --cov-report=term-missing
```

Attendu : couverture ≥ 80 %, tous tests verts.
