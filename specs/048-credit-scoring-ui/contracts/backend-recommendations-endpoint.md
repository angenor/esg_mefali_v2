# Contract — `GET /me/credit-score/recommendations`

## Purpose

Sélectionner les top-N actions du plan d'action (F45) qui maximisent l'amélioration du score crédit, ciblées sur les sous-scores les plus faibles. Alimente US4 (recommandations actionnables).

## Request

`GET /me/credit-score/recommendations?limit={N}&entreprise_id={uuid}`

| Param | In | Type | Required | Default | Description |
|--|--|--|--|--|--|
| `limit` | query | int | non | `5` | `[1..5]`, retourne 422 hors borne |
| `entreprise_id` | query | UUID | non | dérivé | override admin |

**Auth** : `Depends(get_current_pme)`.

## Response 200

```json
{
  "items": [
    {
      "step_id": "a1b2-…",
      "title": "Réduire la dette court terme",
      "description": "Renégocier les lignes ≤12 mois pour basculer sur des maturités ≥36 mois.",
      "target_subscore": "solidite_financiere",
      "estimated_credit_points_impact": 8
    },
    {
      "step_id": "c3d4-…",
      "title": "Documenter votre politique RSE",
      "description": null,
      "target_subscore": "engagement_esg",
      "estimated_credit_points_impact": 5
    }
  ],
  "selected_subscores": ["solidite_financiere", "engagement_esg"]
}
```

Schéma : `CreditRecommendationsOut` / `CreditRecommendationOut` (cf. `data-model.md`).

## Sélection (clarification Q1)

1. Filtrer les `action_item` du tenant tel que `target_subscore` ∈ {sous-scores du score courant les plus faibles}. Démarrer avec le bucket le plus faible ; si <`limit` actions, élargir au 2e plus faible, etc.
2. Filtrer `estimated_credit_points_impact > 0` (sinon non pertinent).
3. Trier desc par `estimated_credit_points_impact`.
4. Couper à `limit`.

`selected_subscores` informe l'UI des buckets effectivement retenus pour la sélection (utile pour affichage et debug).

## Dépendance F45

L'endpoint suppose que `action_item` (F45) expose :

- `target_subscore: 'solidite_financiere' | 'performance_operationnelle' | 'engagement_esg' | 'gouvernance' | null`
- `estimated_credit_points_impact: int | null`

**Si ces champs n'existent pas encore** : ils doivent être ajoutés à F45 en tant qu'extension non rétro-incompatible. À coordonner avec l'équipe F45 lors de l'implémentation. Le service F48 retourne `{items: [], selected_subscores: []}` graceful si aucune action ne porte ces champs (cas test `test_recommendations_endpoint.py` cas 6).

## Response errors

| Code | Cas | Body |
|--|--|--|
| 401 | JWT manquant | `{detail: "Not authenticated"}` |
| 422 | `limit` hors `[1..5]` | `{detail: [...]}` |
| 422 | `entreprise_id` non rattachée | `{detail: {code: "entreprise_required", ...}}` |

## RLS

Filtre SQL `WHERE action_item.account_id = current_account_id`.

## Audit

Lecture pure — pas d'audit.

## Tests pytest associés

`backend/tests/credit/test_recommendations_endpoint.py` (7 cas, cf. plan.md).
