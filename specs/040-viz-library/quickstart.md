# Quickstart — F40 Visualization Library

**Branch** : `040-viz-library` | **Date** : 2026-05-03

Ce guide permet de lancer la feature en local et de vérifier les User Stories en quelques minutes.

## 1. Prérequis

Toutes les dépendances nécessaires sont déjà déclarées dans `frontend/package.json` (chart.js, mermaid, leaflet, vue-virtual-scroller, dompurify, axe-core, @floating-ui/vue, pinia). Aucune commande `pnpm add` n'est requise pour cette feature.

```bash
make setup       # si pas déjà fait
make db-up       # postgres pour /api/sources/:id
make backend     # FastAPI sur :8010
make frontend    # Nuxt sur :3001
```

## 2. Vérifier la branche

```bash
git status
# attendu : on branch 040-viz-library
```

## 3. Lancer la showcase

Une fois `make frontend` démarré :

- Ouvrir <http://localhost:3001/dev/viz-showcase>
- Cette route est **dev-only** : guard `process.env.NODE_ENV !== 'production'` ; elle renvoie 404 en prod.

La page rend chacun des 14 composants `<Viz*>` avec mock data. Aucun message d'erreur ne doit apparaître dans la console.

## 4. Vérifier les User Stories en moins de 5 minutes

| US | Vérification |
|----|--------------|
| US1 KPI + source pin | Cliquer le pin du `<VizKPICard>` "Score E : 72/100" → popover s'ouvre avec titre / URL / pilier / valid_from. |
| US2 Charts | Vérifier rendu Line / Area / Bar / Stacked / Radar / Pie / Donut sans erreur ; basculer le toggle `loading` / `empty` côté showcase. |
| US3 Mermaid | Vérifier rendu d'un flowchart valide ; vérifier que le bloc invalide affiche le source brut sans crash. |
| US4 DataTable virtualisée | Scroller la table 1000 lignes — fluide. Vérifier tri colonne `money` (montants formatés `Intl.NumberFormat fr-FR`). |
| US5 Source pin universel | Vérifier la même icône / popover sur KPI, ligne de table et chart. |
| US6 Gauge | `<VizGaugeChart :value="68">` doit pointer dans la zone orange. |
| US7 Map Leaflet | 50 pins clusterisés ; zoom max plafonné à 5. |

## 5. Lancer les tests

```bash
cd frontend
pnpm vitest run app/components/viz
pnpm vitest run app/composables/__tests__/useChartTheme.test.ts
pnpm vitest run app/stores/__tests__/sources.test.ts
pnpm vitest run app/utils/__tests__/moneyFormat.test.ts
pnpm vitest run app/utils/__tests__/mermaidSanitize.test.ts
pnpm vitest run app/components/viz/__tests__/a11y.showcase.test.ts
```

Tous doivent passer ; couverture des fichiers `viz/` ≥ 80 %.

## 6. Audit accessibilité ad-hoc

Dans la showcase, ouvrir DevTools → onglet Accessibilité ou exécuter axe DevTools : aucune violation `serious` / `critical` attendue (FR-019, SC-011).

## 7. Vérifier le bundle

```bash
cd frontend
pnpm build
```

Inspecter `dist/_nuxt/` : aucun nom de chunk principal ne doit contenir `chart`, `mermaid` ou `leaflet`. Ces libs apparaissent dans des chunks **asynchrones séparés** (SC-007).

## 8. Vérifier les invariants P10 / P5

```bash
# I1 : aucun input/submit dans les composants viz (P10)
grep -rE "<input|<button[^>]*type=\"submit\"|@click\.prevent" frontend/app/components/viz
# attendu : aucun résultat

# I2 : aucune valeur monétaire en number brut
grep -rE "amount:\s*[0-9]" frontend/app/components/viz
# attendu : aucun résultat (seuls des string sont autorisés pour amount)
```

## 9. Branchement avec F39 (bottom sheet)

Aucun couplage direct : F40 = display-only dans la bulle ; F39 gère les interactions. Si une bulle expose un bouton "Modifier", c'est le runtime LLM (F39) qui ouvre le bottom sheet correspondant — pas F40.

## 10. Dépendance F03 (résolution sources)

Si `/api/sources/{id}` n'existe pas encore en backend :

1. Activer le mode mock dans le store :
   ```ts
   // frontend/app/stores/sources.ts
   const MOCK = import.meta.env.DEV && import.meta.env.VITE_VIZ_SOURCES_MOCK === 'true'
   ```
2. Ouvrir une issue tracée vers F03 pour livrer l'endpoint réel.
3. Le contrat attendu est dans `specs/040-viz-library/contracts/sources-resolve.openapi.yaml`.
