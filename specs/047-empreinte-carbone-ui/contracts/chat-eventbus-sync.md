# Contract — Chat ↔ Carbone EventBus sync (F47)

**Module** : `frontend/app/composables/useChatEventBus.ts` (existant, F41) consommé par `useCarbon`.

## Évènements émis par F47

### `entity_updated`

Émis après chaque succès de `editLine`, `recompute`, ou de fin de wizard.

```ts
{
  type: "entity_updated",
  entity: "carbon_footprint",
  account_id: string,
  year: number,
  footprint_id: string,        // nouvelle row carbon_footprint
  edited_line_code?: string,   // présent si edit-line
  trigger: "manual" | "wizard" | "recompute",
}
```

### `context_invalidated`

Émis en complément lors de toute écriture humaine (P8).

```ts
{
  type: "context_invalidated",
  entity: "carbon_footprint",
  account_id: string,
}
```

## Évènements écoutés par F47

### `entity_updated{entity:"carbon_footprint"}`

Origine typique : un tool LLM `update_carbon_data` côté chat a inséré ou modifié des lignes.

**Action `useCarbon`** :
1. Si `payload.year === store.selectedYear` → invalider `store.footprints[year]` et refetch.
2. Mettre à jour `store.index` :
   - Si `year` déjà présent → remplacer l'entrée par la nouvelle (footprint_id, total, computed_at).
   - Sinon → insérer en tête, retrier desc par year.
3. Recalculer `coverage` (dérivée pure).
4. Si un `EditLineDrawer` est ouvert sur la ligne `edited_line_code` → afficher un toast « Cette ligne vient d'être mise à jour par l'assistant. Vos modifications l'écraseront. »

### `entity_updated{entity:"source"}`

Origine typique : une `Source` est passée de `pending` à `verified` (ou inverse, `revoked`).

**Action `useCarbon`** :
1. Si la `Source` est référencée par une ligne du `footprints[selectedYear]` → invalider la `<FactorSourcePopover>` correspondante et rafraîchir le badge `<RevokedSourceBadge>`.
2. Pas de refetch global.

## Garanties

- Les événements F47 sont **idempotents** : recevoir deux fois la même mutation ne casse pas l'état (le store remplace par footprint_id).
- L'EventBus utilise `BroadcastChannel` (multi-onglet) — déjà fourni par F41.
- Pas de dépendance directe entre `pages/carbone` et `pages/chat` ; tout passe par l'EventBus.

## Tests vitest

- `useCarbon.test.ts` :
  - reçoit `entity_updated{carbon_footprint, year=selectedYear}` → refetch est appelé.
  - reçoit `entity_updated{carbon_footprint, year=autre}` → seul `index` est mis à jour, pas de refetch du footprint courant.
  - reçoit `entity_updated{source, source_id=X}` où X est référencé par une ligne → la ligne est marquée pour rafraîchissement.

- E2E `carbone.spec.ts` (scénario `l`) :
  - Ouvrir `/carbone` dans onglet A.
  - Onglet B : émettre via console `useChatEventBus().emit("entity_updated", { entity: "carbon_footprint", year: 2026, ... })`.
  - Onglet A : KPI total et ligne mis à jour < 1 s sans rechargement.
