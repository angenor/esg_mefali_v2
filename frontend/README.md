# Frontend — ESG Mefali

Nuxt 4 + Vue 3 + Tailwind v4. Voir `../CLAUDE.md` pour la stack globale et les commandes.

## Visualization Library — F40

Composants `<Viz*>` **display-only** consommés par les bulles assistant. Aucune
interaction modifiant l'état — tout input vit dans F39 (bottom sheet).

### Composants

| Composant | Rôle |
|---|---|
| `VizSourcePin` | Pin universel, ouvre une popover (titre/url/pillar/valid_from). Fail-silent en 404. |
| `VizKPICard` | KPI avec valeur tabular-nums, delta coloré + signe, source pin. |
| `VizLineChart` / `VizAreaChart` | Lignes + variante avec fill — chart.js lazy. |
| `VizBarChart` / `VizStackedBarChart` | Barres simples ou empilées. |
| `VizRadarChart` | Radar 6 axes max (warning au-delà). |
| `VizGaugeChart` | Jauge 0-100 (zones rouge ≤33 / orange ≤69 / vert ≥70 + icône doublure). |
| `VizPieChart` / `VizDonutChart` | Camembert / donut. |
| `VizMermaidRenderer` | SVG sanitisé via DOMPurify + fallback `<pre>` si parse fail. |
| `VizDataTable` | Table typée — virtualisation > 100 lignes ou pagination optionnelle. |
| `VizLeafletMap` | Carte OSM, zoom max 5, attribution. |
| `VizLoadingState` / `VizEmptyState` | États génériques partagés. |

### Routes & dev tools

- `/dev/viz-showcase` (dev-only) : rend tous les composants avec toggles
  `loading` / `empty` / `paginate`.
- Toggle `loading` ou `empty` met les composants dans l'état correspondant.
- Tests a11y : `app/components/viz/__tests__/a11y.showcase.test.ts` (axe-core).

### Conventions

- **Lazy-load** : chart.js / mermaid / leaflet sont chargés uniquement quand
  un `<Viz*>` est monté, dans `<ClientOnly>` (SSR-safe).
- **Money typé** : `MoneyValue = { amount: string; currency: ISO4217 }`. Le
  formatage passe exclusivement par `app/utils/moneyFormat.ts`. **Aucun `float`** (P5).
- **Sources** : tout `source_id` est résolu via `useSourcesStore()` (cache
  TTL 5 min, dédoublonnage des appels en vol). Single source of truth = backend
  `/api/sources/{id}`.
- **A11y WCAG 2.1 AA** : `role="img"` sur les canvas, `aria-label` synthétique,
  description longue via `longDescription` (`<span class="sr-only">`).
- **Reduced motion** : toutes les animations sont coupées sous
  `prefers-reduced-motion: reduce` via `useChartTheme()` / `useReducedMotion()`.

### Dépendance backend

L'endpoint `GET /api/sources/{source_id}` (F03) est requis. En dev, le store
accepte un fetcher injectable via `__setSourcesFetcher()` (utilisé par les tests).

### Bundle

Vérifier que chart.js / mermaid / leaflet sont bien des chunks asynchrones :

```bash
pnpm build
ls dist/_nuxt/ | grep -E "(chart|mermaid|leaflet)"
```

Aucun de ces fichiers ne doit apparaître dans `entry.*.js`.

## Quickstart F52 — Notifications, Paramètres, Exports

Pages livrées avec la feature 052 :

| Route | Rôle |
|---|---|
| `/notifications` | Centre paginé (filtres `unread_only`, `kinds[]`, `from`, `to`), drawer détail, mark-all-read optimiste, mise à jour SSE temps réel, état vide. |
| `/parametres/profil` | Nom, photo, langue, e-mail (re-vérification). |
| `/parametres/notifications` | Toggles email + in-app par kind (cf. F38). |
| `/parametres/consents` | RGPD : retrait avec audit + e-mail de confirmation. |
| `/parametres/securite` | Sessions actives + révocation, statut extension. |
| `/parametres/donnees` | Export RGPD complet (`POST /me/exports {type:"rgpd_full"}`). |
| `/parametres/suppression` | Zone dangereuse : suppression compte J+30, annulable. |
| `/dashboard/exports` | Historique exports (PDF/JSON), création async, bascule e-mail > 100 Mo. |

### Bottom-sheets (P10)

Toute saisie sensible passe par un **bottom-sheet** :

- `EmailChangeBottomSheet`, `PasswordChangeBottomSheet`,
- `ConsentWithdrawBottomSheet`, `SessionRevokeBottomSheet`,
- `AccountDeletionBottomSheet`, `NewExportBottomSheet`.

### Stores Pinia

`notifications`, `notificationPreferences`, `consents`, `sessions`,
`accountDeletion`, `exports` — tous SSR-safe.

### Composables

`useNotificationsFilters` (sync query string), `useNotificationsStream`
(SSE `notification.created`/`bulk_read`/`read`), `useEmailChangeFlow`,
`useAccountDeletion`, `useExtensionStatus` (refresh + forcePing fallback web).

### Tests

```bash
# Unit/composants
cd frontend && pnpm vitest run app/stores/__tests__ app/composables/__tests__ app/components/notifications/__tests__ app/components/parametres/__tests__

# E2E
pnpm playwright test e2e/052/notifications-mark-all-read.spec.ts
pnpm playwright test e2e/052/account-deletion-30d.spec.ts
pnpm playwright test e2e/052/email-change-reverif.spec.ts
pnpm playwright test e2e/052/exports-history.spec.ts
pnpm playwright test e2e/052/a11y.spec.ts
```

Variables `E2E_PME_EMAIL` / `E2E_PME_PASSWORD` requises ; les tests sont
skippés proprement quand elles sont absentes.
