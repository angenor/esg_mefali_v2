# Contract — Chat EventBus sync (F45)

Contrat des événements échangés entre la page `/plan-action` et le composable global `useChatEventBus` (F41).

## Vue d'ensemble

Trois flux :

1. **Chat → page** : le LLM ou un agent backend modifie une étape ou régénère le plan ; la page rafraîchit la donnée.
2. **Page → autres surfaces** : une mutation locale (cocher, éditer, régénérer) est diffusée au chat ouvert et au dashboard F44.
3. **Aucune** mutation directe entre composants UI sans passer par le store + bus (source unique de vérité).

## Événements consommés (Chat → plan-action)

### `entity_updated` avec `entity_type = 'action_step'`

**Émis par** : F41 chat orchestrator quand un tool call (ex. `complete_action_step`) modifie une étape.

**Payload** :

```ts
{ entity_type: 'action_step', entity_id: string /* UUID step */ }
```

**Effet côté plan-action** :
- `useActionPlanStore.invalidateStep(entity_id)` :
  1. Re-fetch `GET /me/action-plan` (le backend ne supporte pas le filtre par step_id, on récupère le plan complet).
  2. Remplace **uniquement** `plan.steps[entity_id]` dans le store ; les autres steps restent identitaires (même référence) pour éviter une re-render globale.
  3. Réinitialise `stepStates[entity_id]` (efface overlay, loading, error).

**Performance** : 1 fetch HTTP, < 10 KB JSON. La granularité « ne re-rend qu'une card » est garantie par la stratégie de mutation immutable du store (Pinia).

### `entity_updated` avec `entity_type = 'action_plan'`

**Émis par** : F41 quand un tool call régénère le plan (`regenerate_action_plan`).

**Payload** :

```ts
{ entity_type: 'action_plan', entity_id: string /* UUID plan */ }
```

**Effet** : `useActionPlanStore.fetchPlan(force=true)`. Remplace tout le plan (steps + version + horizon_months) ; vide `pendingMutations` et `stepStates` (cohérent avec la sémantique de versioning).

## Événements émis (plan-action → autres surfaces)

### `action_step:locally_updated`

**Émis quand** : la PME coche une étape (`useActionStepToggle`) **ou** valide le bottom sheet d'édition. Émis **après** la confirmation backend (200 OK), **pas** sur l'optimistic.

**Payload** :

```ts
{
  step_id: string,
  patch: { status?: StepStatus, responsible_user_id?: string | null }
}
```

**Consommateurs prévus** :
- F41 chat : invalide son contexte LLM (cohérent P8) — si une bulle assistant venait de mentionner cette étape, son rendu est marqué « obsolète ».
- F44 dashboard `CardActionPlan` : déjà couvert par le partage du store ; cet event est une garantie supplémentaire pour les cas où la card serait montée dans un onglet séparé.

### `action_plan:regenerated`

**Émis quand** : la régénération aboutit (201 Created côté backend).

**Payload** :

```ts
{ plan_id: string, version: number }
```

**Consommateurs prévus** :
- F41 chat : reset complet du contexte plan d'action.
- F44 dashboard : invalidation `next_actions` du summary (déjà géré par F44 via son propre listener `entity_updated{action_plan}`).

## Événements **non** émis

- Pas d'event sur changement de filtres URL ou d'horizon view → purement UI local.
- Pas d'event sur ouverture/fermeture du bottom sheet d'édition.
- Pas d'event sur les mutations optimistes en vol (seul le succès final est diffusé).

## Garanties

| Garantie | Mécanisme |
|---|---|
| Idempotence à la réception | Re-fetch ciblé remplace par la valeur backend ; deux events identiques = même résultat |
| Pas de boucle de feedback | Une mutation locale n'écoute pas son propre echo : le store ignore un `entity_updated` reçu < 500 ms après une émission locale pour le même `step_id` |
| Ordre relatif | Sans garantie globale ; le **store** est la source de vérité, pas la séquence d'events |
| Désouscription | `onBeforeUnmount` désouscrit pour éviter les fuites mémoire entre navigations |

## Test contractuel

Un test E2E `plan-action-chat-sync.spec.ts` simule l'émission d'`entity_updated{action_step}` via un appel direct à `useChatEventBus.emit()` depuis la console (ou via un hook de test), et vérifie que la card cible se rafraîchit en moins d'une seconde.

Un test unit `useActionPlan.test.ts` mocke `useChatEventBus` et vérifie les invalidations ciblées.
