# Contract — Frontend Components (F47)

**Module** : `frontend/app/components/carbone/*` + `frontend/app/pages/carbone/index.vue`.

## Page `pages/carbone/index.vue`

**Layout** :

```
┌──────────────────────────────────────────────────────────────────┐
│ AppShell (F38)                                                   │
│  ┌─────────────────────────────────────────────────────┐         │
│  │ Header : Empreinte carbone — Année [select]          │         │
│  ├─────────────────────────────────────────────────────┤         │
│  │ <RecalcStrip year=... />  (bouton + horodatage)      │         │
│  ├─────────────────────────────────────────────────────┤         │
│  │ <LowCoverageBanner v-if coverage.isLow />           │         │
│  ├─────────────────────────────────────────────────────┤         │
│  │ Grid 3 col desktop / 1 col mobile :                  │         │
│  │   <CarbonOverview /> | <ScopeDonut /> | <EvolutionLineChart />│
│  ├─────────────────────────────────────────────────────┤         │
│  │ <FactorReferentielSwitch />  (P2 disabled)           │         │
│  ├─────────────────────────────────────────────────────┤         │
│  │ <ScopeAccordion scope="1" />                         │         │
│  │ <ScopeAccordion scope="2" />                         │         │
│  │ <ScopeAccordion scope="3" />                         │         │
│  ├─────────────────────────────────────────────────────┤         │
│  │ <ExportPdfButton /> (P2)                             │         │
│  └─────────────────────────────────────────────────────┘         │
│                                                                  │
│ Si pas d'empreinte : <EmptyStateWizard /> remplace tout ce qui   │
│ précède la rangée d'export.                                      │
└──────────────────────────────────────────────────────────────────┘
```

**Props** : aucune (page racine).
**Setup** : `const { footprint, index, coverage, loading, error } = useCarbon()`. Sélection d'année synchronisée avec la query `?year=`.

## `<CarbonOverview>`

| Prop | Type | Rôle |
|---|---|---|
| `footprint` | `CarbonFootprint` | empreinte courante |
| `previousYearFootprint` | `CarbonFootprint \| null` | pour delta |
| `coverage` | `CoverageSnapshot` | KPI couverture % |

**Affiche** : KPI total `tCO2e` (2 décimales `tabular-nums`), delta % vs N-1 (avec signe et couleur ; `—` si null), couverture % avec barre de progression.

## `<ScopeDonut>`

| Prop | Type | Rôle |
|---|---|---|
| `byScope` | `{ "1": string; "2": string; "3": string }` | kgCO2e par scope |

**Wrap** `<VizDonutChart>` (F40). Légende interactive (clic = isole un scope). Accessibilité héritée de F40.

## `<EvolutionLineChart>`

| Prop | Type | Rôle |
|---|---|---|
| `index` | `CarbonIndexEntry[]` | une entrée par année (max 5 affichées) |
| `currentYear` | `number` | année mise en évidence |

**Wrap** `<VizLineChart>` (F40). 1 série totale `tCO2e` + 3 séries (S1/S2/S3) si l'on dispose des `byScope` (lazy fetch des footprints détaillés au besoin).

## `<ScopeAccordion>`

| Prop | Type | Rôle |
|---|---|---|
| `scope` | `"1" \| "2" \| "3"` | scope à afficher |
| `breakdown` | `ScopeBreakdown` | extrait du `GroupedBreakdown` |

**Affiche** : header (libellé + total kgCO2e + couverture postes `n/m`) + liste de `<EmissionLine>` regroupées par poste. Mention « market vs location-based » sur le scope 2 (infobulle).

## `<EmissionLine>`

| Prop | Type | Rôle |
|---|---|---|
| `line` | `CarbonBreakdownLine` | ligne d'activité |
| `postLabel` | `string` | libellé i18n du poste |

**Affiche** : `quantity unit` | `factorValue kgCO2e/unit (vN, valid_from)` | `kgCO2e` total | `<FactorSourcePopover>` | bouton « Modifier ».

Si `sourceId === null` → badge « Source manquante ».
Si la `Source` (chargée à la demande) est `revoked` → badge `<RevokedSourceBadge>` + valeur grisée.

## `<FactorSourcePopover>`

| Prop | Type | Rôle |
|---|---|---|
| `factorId` | `string` | UUID du facteur |
| `factorVersion` | `number` | version |
| `factorSourceId` | `string` | UUID de la `Source` du facteur |

**Wrap** `<UiPopover>` + `<VizSourcePin>`. Au clic, fetch `Source` lazy.

## `<RecalcStrip>`

| Prop | Type | Rôle |
|---|---|---|
| `year` | `number` | année à recalculer |
| `lastComputedAt` | `string` | horodatage |
| `loading` | `boolean` | spinner |

**Action** : clic → `useCarbon().recompute(year)`.

## `<EditLineDrawer>`

Composant orchestrateur (pas d'UI propre — délègue au bottom sheet).

| Prop | Type | Rôle |
|---|---|---|
| `year` | `number` | |
| `line` | `CarbonBreakdownLine \| null` | si `null`, mode « ajout d'un poste » |
| `posteCode` | `CarbonPosteCode` | pour mode ajout |

**Action** : `useCarbonEdit().openDrawer({ year, line, posteCode })` ouvre `<ChatBottomSheet>` avec un schéma `ask_form` à 3 champs (`quantity`, `unit_or_country`, `source_id`). Validation côté UI avant `POST .../edit-line`.

## `<LowCoverageBanner>`

| Prop | Type | Rôle |
|---|---|---|
| `coverage` | `CoverageSnapshot` | |

**Affiche** : `<UiBanner variant="warning">` avec texte i18n + CTA « Compléter ». Visible uniquement si `coverage.isLow`.

## `<EmptyStateWizard>`

| Prop | Type | Rôle |
|---|---|---|
| `year` | `number` | année à initialiser |

**Action** : déclenche `useCarbonWizard().start(year)`. UI : grand call-to-action centré « Calculez votre première empreinte en 5 minutes » + 3 cartes (énergie / déplacements / achats) + bouton « Commencer ». Le bouton ouvre `<ChatBottomSheet>` en mode `show_form` séquentiel (3 étapes). Bouton « Répondre librement » disponible (P10).

## `<FactorReferentielSwitch>` (P2)

| Prop | Type | Rôle |
|---|---|---|
| `disabled` | `boolean` | toujours `true` au MVP |

**Affiche** : switch ADEME / IPCC + badge « Estimation, pas référence officielle » + infobulle « Comparateur IPCC à venir ».

## `<ExportPdfButton>` (P2)

| Prop | Type | Rôle |
|---|---|---|
| `year` | `number` | |

**Affiche** : bouton « Exporter PDF » → délègue à F51 (composant placeholder au MVP F47).
