# Contract — Chat ↔ Credit-score EventBus sync (F48)

## Bus : `useChatEventBus` (existant F41)

## Évènements consommés par F48

| Évènement | Payload | Action F48 |
|--|--|--|
| `entity_updated` | `{ entity: 'credit_data', id?: string }` | `useCreditEdit.refresh()` ; déclenche `useCreditScoreStore.refreshScore()` ; si recompute déjà fait côté backend, écouter aussi `credit_score` |
| `entity_updated` | `{ entity: 'credit_score', id: string, after: CreditScoreOut }` | `applyRecomputeResult(after)` → animation gauge + refresh éligibilité + refresh recommandations |
| `entity_updated` | `{ entity: 'plan_action_item', id?: string }` | `useCreditScoreStore.refreshRecommendations()` (les recommandations dépendent de F45) |

## Évènements émis par F48

| Origine F48 | Évènement | Payload | Récepteurs attendus |
|--|--|--|--|
| `useCreditEdit.submitFinal()` | `entity_updated` | `{ entity: 'credit_data', id }` | chat F41, dashboard F44 |
| Après `applyRecomputeResult` | `entity_updated` | `{ entity: 'credit_score', id, after }` | chat F41, dashboard F44, scoring F46 (cohérence cross-feature) |
| `useCreditWizard.submitFinal()` | `entity_updated` | `{ entity: 'credit_data', id }` puis `{ entity: 'credit_score', id, after }` | tous |

## Invalidations ciblées

L'objectif est de **ne pas faire de refresh global** : chaque event invalide uniquement ce qui est concerné.

```
entity_updated{credit_data}
  └─▶ refreshScore()     (backend recompute auto)
        └─▶ animateGaugeTransition + refreshEligibility() + refreshRecommendations()
        └─▶ refreshHistory() (nouvelle ligne historique)

entity_updated{credit_score}   (recompute manuel ou auto post-credit_data)
  └─▶ applyRecomputeResult(after) → animation
  └─▶ refreshEligibility() (les seuils dépendent du combine + subscores)
  └─▶ refreshRecommendations() (la sélection dépend des subscores)
  └─▶ refreshHistory()

entity_updated{plan_action_item}
  └─▶ refreshRecommendations()  (uniquement)
```

## Cohérence avec F46/F47

Les patterns sont strictement alignés :
- `useChatEventBus` existant (F41) — pas de nouveau bus.
- Mêmes noms d'events (`entity_updated`).
- Même discipline d'invalidation (ciblée, pas globale).

## Tests associés

- Frontend unit : `useCreditScore.test.ts` (cas réception `entity_updated{credit_data}` → refresh + animation), `useCreditEdit.test.ts` (cas émission après submit).
- E2E : `credit-score-chat-sync.spec.ts` (cas (m) du plan).
