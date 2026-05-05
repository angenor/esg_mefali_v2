# Contract — Sync chat ↔ profil via EventBus front

## 1. Producteur : `useChatToolBridge` (F41)

À la fin du rendu d'un tool result mutation, le pont chat émet l'évènement suivant sur le bus :

```ts
type EntityUpdatedEvent = {
  type: 'entity_updated'
  entity: 'entreprise' | 'projet'
  entity_id: string  // id de l'entité ; pour entreprise, vaut account_id
  fields_changed: string[]  // noms canoniques côté backend (ex. ['raison_sociale'])
  source: 'llm'  // toujours llm pour ce canal — utile pour le flash UI
  origin_request_id?: string  // permet de filtrer les self-echoes éventuels
}
```

## 2. Consommateurs F43

### 2.1 `useEntrepriseProfile`
- Souscrit aux events `entity === 'entreprise'`.
- Action :
  1. Si `fields_changed` ne contient **aucun** champ en cours d'édition local non sauvegardé → `loadAll()` silencieux + flash « Mis à jour par le chat » (toast 2 s, non bloquant).
  2. Sinon → ouvre `ConflictDialog` avec `your` = valeur locale en attente, `current` = valeur fraîchement re-fetchée pour ce champ.

### 2.2 `useProjet(id)`
- Souscrit aux events `entity === 'projet' && entity_id === id`.
- Mêmes règles que 2.1.

### 2.3 `useProjetsStore`
- Souscrit aux events `entity === 'projet'` quel que soit l'`entity_id` (création, update générique).
- Si `entity_id` absent de `byId` → `loadList()` (cas création par chat).

## 3. SSE backend (hors MVP F43)

Routes existantes mais non consommées :
- `GET /me/entreprise/events`
- `GET /me/projets/events`

Justification du non-usage MVP : un seul onglet utilisateur actif suffit dans 95 % des cas usage cibles ; le canal `useChatEventBus` est synchrone et plus simple à tester. Réouvrable en post-MVP si la télémétrie révèle un besoin multi-onglets / collab.

## 4. Garanties et anti-boucles

- **Anti-boucle** : la mutation déclenchée par `patchField` côté UI ne reçoit pas d'event `entity_updated` du chat (le chat n'est pas le mutateur). Si un futur SSE backend rediffusait ces évènements, le filtre `origin_request_id` permettrait d'ignorer ses propres requêtes.
- **Délai cible** : 95 % des events propagés en < 2 s (mesuré du tool result rendering au flash UI). Cf. SC-003.
- **Ordering** : si deux events sur le même champ arrivent dans le désordre, le plus récent (timestamp ou version) gagne (re-fetch toujours basé sur le dernier état serveur).

## 5. Tests

- Test unitaire `useChatEventBus.test.ts` : déjà couvert F41.
- Tests d'intégration F43 :
  - `useEntrepriseProfile.test.ts` mock l'event bus → vérifie le flash et l'absence d'écrasement.
  - `e2e/profil-conflict-chat-sync.spec.ts` : ouvre la page profil, simule (via `page.evaluate`) un event `entity_updated`, attend le flash en moins de 2 s.
