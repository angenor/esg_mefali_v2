# Contract — Extension `CreditScoreOut.subscores`

## Purpose

Exposer 4 sous-scores normalisés (`solidite_financiere`, `performance_operationnelle`, `engagement_esg`, `gouvernance`) sur les réponses `GET /me/credit-score` et `POST /me/credit-score/recompute`, dérivés des `facteurs` existants. Alimente US2 (décomposition) et le tri/filtrage des recommandations (US4).

## Schéma

Champ ajouté à `CreditScoreOut` (Pydantic v2, `extra='forbid'` préservé) :

```python
subscores: dict[str, int | None] | None = None
```

- **Clés autorisées** (closed enum *de fait*, validé par contrat de service) : `"solidite_financiere"`, `"performance_operationnelle"`, `"engagement_esg"`, `"gouvernance"`.
- **Valeur** : entier `[0..100]` ou `None` (bucket vide).
- **Optionnel** : `null` ou absent → pas de sous-scores calculés (méthodologie ancienne).

Rétrocompat : les clients ne lisant pas `subscores` ne sont pas affectés (champ additif).

## Calcul

`backend/app/credit/service.py::compute_subscores(facteurs)` :

1. Charger le mapping `FACTOR_TO_BUCKET` depuis `subscore_mapping.py`.
2. Pour chaque bucket :
   - Récupérer les `facteurs` du bucket (`factor_name in bucket`).
   - Si vide → bucket vaut `None`.
   - Sinon → moyenne pondérée : `Σ (contribution_normalisée * weight_in_bucket) / Σ weight_in_bucket`, normalisée 0-100, arrondie à l'entier.

`recompute_score` et `get_latest_score` injectent `subscores` dans le retour.

## Seuils de classification (contrat partagé front/back)

Les seuils de classification du `combine` (Insuffisant/À améliorer/Bon/Excellent) sont :

| Bucket | Plage | Borne inférieure inclusive |
|--|--|--|
| Insuffisant | 0-39 | oui |
| À améliorer | 40-59 | oui |
| Bon | 60-79 | oui |
| Excellent | 80-100 | oui |

**Implémentation** : côté front uniquement (`frontend/app/lib/classifyCreditScore.ts`). Le backend ne sérialise ni `bucket` ni `label`. Toute évolution future qui les serait amenée à exposer côté backend devra respecter ces seuils — documenté ici comme single source of truth pour la classification.

## Validation

| Cas | Comportement |
|--|--|
| Tous les buckets ont des facteurs | `subscores = {bucket: int, …}` |
| Aucun facteur du bucket | `subscores[bucket] = None` |
| Aucun facteur du tout (méthodologie vide) | `subscores = None` |
| Méthodologie change de noms de facteurs | facteurs non mappés → ignorés (dégradation silencieuse, cas test `test_subscores_extension.py` cas 3) |

## Tests pytest associés

`backend/tests/credit/test_subscores_extension.py` (5 cas, cf. plan.md).
