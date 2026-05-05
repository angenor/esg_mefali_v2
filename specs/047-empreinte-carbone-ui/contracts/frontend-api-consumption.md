# Contract — Frontend API consumption (F47)

**Module** : `frontend/app/services/api/carbon.ts`
**Consommé par** : `useCarbonStore`, `useCarbon`, `useCarbonHistory`, `useCarbonEdit`, `useCarbonWizard`.

## Méthodes exposées

```ts
export interface CarbonApi {
  fetchIndex(opts?: { limitYears?: number }): Promise<CarbonIndexEntry[]>
  fetchFootprint(year: number): Promise<CarbonFootprint>
  recompute(year: number): Promise<CarbonRecomputeResponse>
  editLine(year: number, payload: CarbonEditLineRequest): Promise<CarbonEditLineResponse>
  computeInitial(year: number, sourceData: CarbonSourceItem[]): Promise<CarbonFootprint>  // appelle POST /me/carbon/compute (existant)
}
```

| Méthode | Endpoint | Notes |
|---|---|---|
| `fetchIndex` | `GET /me/carbon?limit_years=...` | Vide → `[]`. TTL store 60 s. |
| `fetchFootprint` | `GET /me/carbon/{year}` | 404 → store enregistre `null` pour cette année (déclenche empty-state ou wizard). |
| `recompute` | `POST /me/carbon/{year}/recompute` | Appelé par `RecalcStrip`. |
| `editLine` | `POST /me/carbon/{year}/edit-line` | Appelé par `EditLineDrawer` après soumission du bottom sheet. |
| `computeInitial` | `POST /me/carbon/compute` (existant F28) | Appelé par `useCarbonWizard` à la fin du pas 3. |

## Conversion des `Decimal`

Toutes les valeurs `Decimal` sérialisées en `string` côté backend sont conservées en `string` dans les types TS et converties en `Decimal` (via `decimal.js`) **uniquement** au moment de l'agrégation ou du formatage. Pas de conversion en `number` (P5).

## Gestion d'erreur

`fetchIndex`, `fetchFootprint`, `recompute`, `editLine`, `computeInitial` rejettent avec un objet `{ status: number, code: string, message: string }`. Le store catche et :
- 401 → reroute auth (`useAuth.requireLogin()`).
- 404 `footprint_not_found` (sur fetchFootprint) → marque l'année `null` (pas une erreur visible).
- 404 `factor_not_found` → toast français explicite.
- 400 `source_not_verified` → toast + revalidation côté EditLineDrawer.
- 429 → toast « Trop de recalculs. Veuillez patienter quelques secondes. »
- 5xx / network → toast générique + état précédent préservé.

## EventBus

À la résolution de `editLine` ou `recompute` :

```ts
useChatEventBus().emit("entity_updated", {
  entity: "carbon_footprint",
  account_id: currentAccountId,
  year,
  footprint_id: response.id,
})
useChatEventBus().emit("context_invalidated", {
  entity: "carbon_footprint",
  account_id: currentAccountId,
})
```

À la réception de `entity_updated{entity:"carbon_footprint", year}` :
- Invalider `footprints[year]` (refetch).
- Invalider `index` si `year` n'y est pas encore présent.
