# Contract — Backend Index Endpoint (F47)

**Route** : `GET /me/carbon`
**Méthode** : `GET`
**Auth** : `Depends(get_current_pme)` — JWT requis ; `account_id` extrait pour RLS.
**Tags OpenAPI** : `carbon`
**Status** : nouveau (livré par F47).

## Path / Query parameters

Aucun paramètre obligatoire.

| Nom | Type | Default | Contraintes |
|---|---|---|---|
| `limit_years` | `int` (query) | `10` | `1 ≤ limit_years ≤ 20` ; hors borne → 422 |

## Response — `200 OK` — `CarbonIndexOut`

```jsonc
{
  "entries": [
    {
      "footprint_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b201",
      "year": 2026,
      "total_tco2e": "12.402450",
      "computed_at": "2026-05-04T12:30:00Z",
      "version": 3
    },
    {
      "footprint_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b101",
      "year": 2025,
      "total_tco2e": "13.870120",
      "computed_at": "2025-12-15T09:11:00Z",
      "version": 2
    }
  ]
}
```

**Tri** : `year` desc. Pour chaque `year`, l'entrée retournée est la **plus récente** (`computed_at` max).

## Erreurs

| Code | Body | Quand |
|---|---|---|
| 401 | `{"detail":{"code":"unauthorized","message":"..."}}` | JWT manquant / invalide |
| 403 | `{"detail":{"code":"no_account","message":"Compte PME non rattache."}}` | Utilisateur sans `account_id` |
| 422 | Pydantic standard | `limit_years` hors borne |

## Comportement

- Aucune empreinte pour le tenant → `200 { "entries": [] }` (pas 404).
- Cross-tenant : invisible par construction (RLS via `account_id`).
- Pas d'effet de bord, pas d'audit (lecture seule).

## Tests (`backend/tests/carbon/test_index_endpoint.py`)

1. Compte sans empreinte → 200 + `entries: []`.
2. Compte avec 3 empreintes (2024, 2025, 2026) → 3 entrées triées desc par year.
3. Compte avec 2 calculs sur 2025 (versions 1 et 2) → seule la `version: 2` (`computed_at` max) retournée.
4. Cross-tenant : tenant A appelle, tenant B a 5 empreintes → `entries: []` chez A.
5. JWT manquant → 401.
6. `limit_years=2` avec 5 années en base → 2 dernières seulement (2026, 2025).
