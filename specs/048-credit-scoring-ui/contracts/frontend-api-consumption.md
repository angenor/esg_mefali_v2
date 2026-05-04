# Contract — Frontend API consumption (F48)

## Endpoints consommés

| Méthode | Endpoint | Origine | Usage F48 |
|--|--|--|--|
| GET | `/me/credit-score` | F29 | score courant + facteurs + subscores (extension F48) |
| GET | `/me/credit-score/history?limit=6` | **F48** (nouveau) | historique 6 derniers calculs (US7) |
| GET | `/me/credit-score/eligibility` | **F48** (nouveau) | badges éligibilité (US3) |
| GET | `/me/credit-score/recommendations?limit=5` | **F48** (nouveau) | recommandations actionnables (US4) |
| POST | `/me/credit-data` | F29 | saisie déclarative financière (bottom sheet, wizard) |
| POST | `/me/credit-score/recompute` | F29 | recalcul après saisie ou recalcul manuel (US6) |
| GET | `/methodologie/credit-scoring` | F29 (public) | lien « Méthodologie » footer (P1) |

## Format des saisies financières (R-07, P5)

Le `payload` de `POST /me/credit-data` (kind=`declaratif`) envoyé par F48 :

```json
{
  "kind": "declaratif",
  "payload": {
    "chiffre_affaires": {"amount": "12500000", "currency": "XOF"},
    "ebe": {"amount": "850000", "currency": "XOF"},
    "dette": {"amount": "3200000", "currency": "XOF"},
    "fonds_propres": {"amount": "5400000", "currency": "XOF"}
  }
}
```

- `amount` est une **string** = `Decimal.toString()` côté UI (jamais de `number`).
- `currency` ∈ {`XOF`, `EUR`, `USD`}. Conversion via peg fixe FCFA-EUR ou `fx_rate` USD est gérée côté backend.

## Pipeline post-saisie

1. UI ouvre `<ChatBottomSheet ask_form>` multi-étapes via `useCreditEdit`.
2. À la soumission finale → `POST /me/credit-data`.
3. Si F29 ne déclenche pas le recompute automatiquement → UI appelle `POST /me/credit-score/recompute`.
4. Réponse `CreditScoreOut` (avec `subscores`) → store mis à jour → `animateGaugeTransition(prev, next)` → toast « +N points » → émission EventBus `entity_updated{credit_data, credit_score}`.
5. `useCreditEligibility.refresh()` + `useCreditHistory.refresh()` + `useCreditRecommendations.refresh()` invalident leur cache et refetch.

## Gestion des erreurs

| Cas | Comportement UI |
|--|--|
| 500 sur `recompute` | toast erreur FR explicite + gauge **reste sur valeur précédente** (pas d'état intermédiaire — edge case spec) |
| 422 sur `credit-data` | message d'erreur FR sous le champ concerné dans le bottom sheet, autres champs préservés |
| 401 (JWT expiré) | redirection login (pattern auth global) |
| 404 sur `recompute` (rare) | message « Aucune donnée crédit n'a encore été enregistrée » + CTA « Lancer le wizard » |
| Réseau down | toast « Backend indisponible » + bouton « Réessayer » |

## i18n

Toutes les chaînes vivent dans `frontend/app/locales/fr.ts` sous `credit_score.*`. Anglais reporté post-MVP (la spec impose FR par défaut).
