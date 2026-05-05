# Contract — Backend Recompute Endpoint (F47)

**Route** : `POST /me/carbon/{year}/recompute`
**Méthode** : `POST`
**Auth** : `Depends(get_current_pme)` — JWT requis ; `account_id` extrait pour RLS.
**Tags OpenAPI** : `carbon`
**Status** : nouveau (livré par F47).

## Path parameters

| Nom | Type | Contraintes |
|---|---|---|
| `year` | `int` | `2000 ≤ year ≤ 2100` ; hors borne → 422 |

## Request body

Aucun body. Le service rejoue le `source_data_json` du dernier calcul de l'année avec les facteurs **actuellement actifs** (`get_facteur(code, pays_iso2, at=date(year, 12, 31))`).

## Response — `200 OK` — `CarbonRecomputeResponse`

```jsonc
{
  "id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b301",
  "year": 2026,
  "total_tco2e": "12.510000",
  "by_scope_kgco2e": { "1": "3210.500", "2": "5800.100", "3": "3499.400" },
  "by_category_kgco2e": { "combustion_fixe": "...", "electricite": "..." },
  "breakdown": [ /* CarbonBreakdownLineOut[] */ ],
  "factor_versions": [ /* {factor_id, version, valid_from, source_id}[] */ ],
  "previous_footprint_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b201"
}
```

## Erreurs

| Code | Body | Quand |
|---|---|---|
| 401 | unauthorized | JWT manquant |
| 403 | no_account | Utilisateur sans `account_id` |
| 404 | `{"code":"footprint_not_found"}` | Aucune empreinte pour `(account_id, year)` |
| 404 | `{"code":"factor_not_found"}` | Un facteur du source_data n'a plus de version active à `at=year-12-31` |
| 422 | Pydantic standard | `year` hors borne |
| 429 | Rate-limited | > 1 recompute / 5 s par tenant (SlowAPI) |

## Effets de bord

- Crée **une nouvelle row** `carbon_footprint` (jamais d'UPDATE/DELETE) avec `version = previous.version + 1` et `computed_at = now()`.
- Insère 1 `audit_event` :
  - `entity = "carbon_footprint"`
  - `field = "recompute"`
  - `source_of_change = MANUAL`
  - `old = { footprint_id: <previous>, total_tco2e: <previous> }`
  - `new = { footprint_id: <new>, total_tco2e: <new> }`

## Tests (`backend/tests/carbon/test_recompute_endpoint.py`)

1. Année sans empreinte → 404 `footprint_not_found`.
2. Année avec empreinte → 200 + nouvelle row créée + `version` incrémenté + `previous_footprint_id` correctement renseigné.
3. Facteur révisé entre les deux calculs → relookup utilise la nouvelle version, `total_tco2e` change, `factor_versions_json` reflète la nouvelle version.
4. Facteur révoqué sans remplaçant → 404 `factor_not_found`.
5. Cross-tenant → 404 (tenant masking).
6. JWT manquant → 401.
7. Audit insertion vérifiée (`source_of_change = manual`, `old`/`new` corrects).
