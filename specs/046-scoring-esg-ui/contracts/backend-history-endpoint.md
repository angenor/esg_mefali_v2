# Contract — Backend History Endpoint (F46)

**Route** : `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}/history`
**Méthode** : `GET`
**Auth** : `Depends(get_current_pme)` — JWT requis ; `account_id` extrait pour RLS.
**Tags OpenAPI** : `scoring`
**Status** : nouveau (livré par F46).

## Path parameters

| Nom | Type | Contraintes |
|---|---|---|
| `entity_type` | `Literal["entreprise", "projet"]` | autres → 404 |
| `entity_id` | `uuid.UUID` | doit appartenir au tenant courant ; sinon 404 |
| `referentiel_code` | `str` | code catalogue F09 ; inconnu → 404 |

## Query parameters

| Nom | Type | Default | Contraintes |
|---|---|---|---|
| `limit` | `int` | `12` | `1 ≤ limit ≤ 50` ; hors borne → 422 |

## Response — `200 OK` — `ScoreHistoryOut`

```jsonc
{
  "entity_type": "entreprise",
  "entity_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b001",
  "referentiel_code": "BOAD",
  "entries": [
    {
      "score_calculation_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b101",
      "computed_at": "2026-05-04T12:30:00Z",
      "score_global": 67.4,
      "referentiel_version": 3
    },
    {
      "score_calculation_id": "f8e0c2c4-1e5b-4a9a-9a2e-91c2cbe9b100",
      "computed_at": "2026-05-02T08:15:00Z",
      "score_global": 64.1,
      "referentiel_version": 3
    }
  ]
}
```

- `entries` est trié `computed_at DESC`.
- `entries` peut être vide (`[]`) si aucun calcul existant pour ce `(entity, referentiel)` — pas un 404.
- `score_global` peut être `null` si l'engine F23 a renvoyé `None` (calcul incomplet sans valeur agrégée).

## Errors

| Status | Cas |
|---|---|
| `401 Unauthorized` | JWT manquant/invalide |
| `403 Forbidden` | utilisateur sans `account_id` |
| `404 Not Found` | `entity_type` inconnu, `entity_id` hors tenant, ou `referentiel_code` inconnu/non publié |
| `422 Unprocessable Entity` | `limit` hors `[1, 50]` |

## Implementation notes

- **Service** : `app.scoring.service.list_history(db, *, account_id, entity_type, entity_id, referentiel_code, limit)`.
  - Résolution `referentiel_code → referentiel_id` via la même requête que `get_latest_score_detail`.
  - `SELECT id, computed_at, score_global, referentiel_version FROM score_calculation WHERE account_id = :acc AND entity_type = :etype AND entity_id = :eid AND referentiel_id = :rid ORDER BY computed_at DESC LIMIT :limit`.
  - Pas d'écriture dans `audit_log` (lecture pure).
- **Router** : `app.scoring.router.list_score_history` ajouté juste après `get_score_detail`.
- **Schéma** : voir `data-model.md` §1.
- **Test** : `backend/tests/scoring/test_history_endpoint.py` (6 cas — voir plan.md §Testing).
- **OpenAPI** : la route est automatiquement publiée via FastAPI ; vérifier que le swagger affiche le tag `scoring` et le schéma `ScoreHistoryOut`.

## Frontend consumption

Le composable `useScoringHistory(refCode)` appelle :

```ts
const { data } = await $api.get<ScoreHistoryOut>(
  `/me/scoring/${entityType}/${entityId}/${refCode}/history`,
  { params: { limit: 12 } },
)
```

et mappe `data.entries` → `ScoreHistoryEntryVM[]` (voir `data-model.md` §2.3).
