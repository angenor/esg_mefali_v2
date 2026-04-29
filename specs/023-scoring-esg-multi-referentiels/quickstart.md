# Quickstart — F23 Scoring ESG MVP

**Feature** : 023-scoring-esg-multi-referentiels
**Date** : 2026-04-29

## Pré-requis

- Backend `.venv` activé, Postgres dockerisé up.
- Migrations F09 + F11/F12 appliquées (`alembic upgrade head`).
- Au moins un référentiel publié (`status='published'`) avec au moins un indicateur publié lié.

## Étape 1 — Appliquer la migration F23

```bash
cd backend
alembic upgrade head    # applique 0016_f23_score_calculation
```

## Étape 2 — Seed de test (optionnel pour démo)

```python
# scripts/seed_f23_demo.py (pseudo)
ref_id = create_referentiel(code="TEST_REF", name="Demo", version=1, status="published")
ind_e = create_indicateur(code="DEMO_E1", pillar="E", value_type="numeric", status="published")
ind_s = create_indicateur(code="DEMO_S1", pillar="S", value_type="boolean", status="published")
link(ref_id, ind_e, weight=1.0, source_id=src_id, seuil_min=0, seuil_max=100)
link(ref_id, ind_s, weight=2.0, source_id=src_id)
```

`VALUE_SOURCE_MAP` doit contenir `DEMO_E1` et `DEMO_S1` pour que le calcul couvre les indicateurs (sinon ils remontent en `value_source_unmapped`).

## Étape 3 — Authentification PME

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d '{"email":"pme@test.local","password":"..."}' \
  -H "Content-Type: application/json" | jq -r .access_token)
ENT_ID=11111111-1111-1111-1111-111111111111
```

## Étape 4 — Recalculer un score

```bash
curl -X POST "http://localhost:8000/me/scoring/entreprise/${ENT_ID}/recompute?referentiel=TEST_REF" \
  -H "Authorization: Bearer $TOKEN"
```

Réponse attendue (201) :
```json
{
  "referentiel_code": "TEST_REF",
  "referentiel_version": 1,
  "score_global": 72.50,
  "scores_by_pillar": { "E": 70.0, "S": 100.0, "G": null },
  "coverage_ratio": 1.0,
  "computed_at": "2026-04-29T12:00:00Z",
  "indicateurs_couverts": [],
  "indicateurs_manquants": [],
  "sources_used": []
}
```

## Étape 5 — Lire les scores

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/me/scoring/entreprise/${ENT_ID}"
```

## Étape 6 — Détail d'un score

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/me/scoring/entreprise/${ENT_ID}/TEST_REF"
```

## Tests

```bash
cd backend
pytest tests/scoring -v --cov=app.scoring --cov-report=term-missing
```

Cible couverture ≥ 80 %.
