# Contract — `GET /me/credit-score/history`

## Purpose

Retourner les N derniers calculs de score crédit pour l'entreprise courante (mode lecture seule). Alimente l'historique (US7, FR-011) et le delta vs N-1 (US1).

## Request

`GET /me/credit-score/history?limit={N}&entreprise_id={uuid}`

| Param | In | Type | Required | Default | Description |
|--|--|--|--|--|--|
| `limit` | query | int | non | `6` | `[1..24]`, retourne 422 hors borne |
| `entreprise_id` | query | UUID | non | dérivé de l'utilisateur | override admin/multi-entreprise (héritage F29) |

**Auth** : `Depends(get_current_pme)`.

## Response 200

```json
{
  "items": [
    {
      "id": "f1c4...",
      "combine": 72,
      "solvabilite": 68,
      "impact_vert": 78,
      "subscores": {
        "solidite_financiere": 70,
        "performance_operationnelle": 80,
        "engagement_esg": 65,
        "gouvernance": 75
      },
      "methodologie_version": 3,
      "computed_at": "2026-04-01T10:30:00Z",
      "coherence_warning": false
    }
  ]
}
```

Schéma : `ScoreHistoryOut` (cf. `data-model.md`). Tri desc par `computed_at`. Liste vide acceptable (200 + `{items: []}`).

## Response errors

| Code | Cas | Body |
|--|--|--|
| 401 | JWT manquant/invalide | `{detail: "Not authenticated"}` |
| 422 | `limit` hors `[1..24]` | `{detail: [{loc: ["query","limit"], msg: ...}]}` |
| 422 | `entreprise_id` non rattachée | `{detail: {code: "entreprise_required", ...}}` |

**Pas de 404** pour « pas de calcul » — retourne `{items: []}`.

## RLS

Filtre SQL `WHERE account_id = current_account_id`. Cross-tenant → liste vide silencieusement (cohérent avec P2 « 404 ou rien », ici « rien » car endpoint de liste).

## Audit

Lecture pure — pas d'audit.

## Tests pytest associés

`backend/tests/credit/test_history_endpoint.py` (6 cas : empty, ≤limit, >limit avec défaut, >limit avec param, cross-tenant, JWT manquant).
