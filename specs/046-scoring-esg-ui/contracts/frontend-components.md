# Contract — Frontend Components (F46)

Props/events/slots de chaque composant nouveau dans `frontend/app/components/scoring/*`. Tous les libellés exposés à l'utilisateur passent par `useT()` (i18n FR par défaut).

---

## `<ReferentielTabs>`

**Props** :

| Nom | Type | Default | Notes |
|---|---|---|---|
| `availableCodes` | `string[]` | — | issus de `summariesByRef` |
| `currentCode` | `string` | — | référentiel sélectionné |
| `disabled` | `boolean` | `false` | `true` en mode snapshot ou pendant un recompute |

**Events** :

- `select(code: string)` — émis au clic ; le parent met à jour l'URL via `setCurrentReferentiel`.

**A11y** : rôle ARIA `tablist` ; chaque pill `role="tab"` + `aria-selected`.

---

## `<ScoreOverview>`

**Props** :

| Nom | Type | Default | Notes |
|---|---|---|---|
| `summary` | `ScoreSummaryVM \| null` | — | `null` → skeleton |
| `loading` | `boolean` | `false` | |
| `isSnapshot` | `boolean` | `false` | affiche bandeau snapshot |

**Slots** : `extra` (pour `<RecalcButton>` et `<CompareButton>`).

**Comportement** :

- Affiche `score_global` en `tabular-nums` taille XL.
- Rend `<VizRadarChart>` si `≤ 6` axes ; sinon `<VizBarChart>` vertical.
- Affiche `coverage_ratio` en %, `computed_at` formatée FR, `referentiel_version` en pastille.
- Inclut un tableau `sr-only` listant chaque axe et son score (a11y).

---

## `<PillarAccordion>`

**Props** :

| Nom | Type | Default | Notes |
|---|---|---|---|
| `buckets` | `PillarBucketVM[]` | — | issus de `mapIndicateursByPillar` |
| `defaultOpen` | `PillarCode[]` | `['E','S','G']` | piliers ouverts au mount |
| `disableEdit` | `boolean` | `false` | `true` en mode snapshot |

**Events** :

- `openIndicateur(row: PillarRowVM)` — délègue au parent qui ouvre `<IndicateurDrawer>`.

**Comportement** : utilise `<details>` natif HTML (a11y, pas de JS pour ouvrir/fermer). Si `bucket.rows.length > 30`, n'affiche que les 30 premiers + bouton « Voir les N restants ».

---

## `<IndicateurRow>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `row` | `PillarRowVM` | — |
| `disableEdit` | `boolean` | `false` |

**Events** :

- `open(row)` — clic sur la ligne ouvre le drawer.

**Comportement** :

- Affiche `indicateurCode` (lookup label via `useT`), `scoreContribution` ou — , `weight`.
- Si `status === 'missing'` : badge gris « À renseigner ».
- Si `isSourceRevoked` : `<RevokedSourceBadge>` + valeur grisée.
- Sinon : `<VizSourcePin sourceId={sourceId}>`.
- Si `!isEditable` : icône info + tooltip « Édition disponible via le chat ».

---

## `<IndicateurDrawer>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `row` | `PillarRowVM \| null` | — |
| `referentielCode` | `string` | — |
| `open` | `boolean` | `false` |
| `disableEdit` | `boolean` | `false` |

**Events** :

- `close()`
- `edit(row)` — délègue à `useIndicateurEdit.openFor(row)`.

**Comportement** :

- Slide-in droite (480 px desktop, 80 % tablette, plein écran mobile) via `<UiPopover side="right">` ou un wrapper dédié.
- Affiche : nom (label i18n), définition (catalogue F09 — fetch lazy), valeur courante, unité, formule (texte si fournie), liste des sources cliquables, `<VizLineChart>` 12 mois (rendu uniquement si `open === true` — performance R9).
- `<VizLineChart>` : data = `historyByRef[ref]` filtré au scope de l'indicateur (au MVP : on affiche l'historique global du référentiel ; le détail par-indicateur n'est pas exposé par le backend → graphique générique du référentiel ; documenté dans `quickstart.md`).
- Boutons : « Modifier » (désactivé si `disableEdit || !row.isEditable`), « Fermer ».

---

## `<MissingIndicatorsList>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `missing` | `MissingIndicatorVM[]` | — |
| `referentielCode` | `string` | — |

**Events** :

- `complete(indicateurCode)` — ouvre le chat contextuel via `useChatEventBus.emit('open_chat_for_indicateur', {indicateur_code, referentiel_code})`.

**Comportement** : caché si `missing.length === 0`.

---

## `<RecalcButton>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `referentielCode` | `string` | — |
| `disabled` | `boolean` | `false` |

**État interne** : `isRecomputing` (lié au store).
**Events** : aucun externe ; appelle `store.recompute(refCode)`.

---

## `<CompareButton>` + `<CompareDrawer>`

`<CompareButton>` : clic ouvre `<CompareDrawer>` (modal large).

`<CompareDrawer>` props :

| Nom | Type | Default |
|---|---|---|
| `availableSummaries` | `ScoreSummaryVM[]` | — |
| `defaultSelected` | `string[]` | `[currentRef]` |
| `open` | `boolean` | `false` |

**Events** : `close()`.
**Comportement** : checkbox liste (max 5 sélections), `<VizBarChart>` horizontal côte à côte par pilier, légende par référentiel (libellé + version). Aucune action de mutation.

---

## `<HistoryChart>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `entries` | `ScoreHistoryEntryVM[]` | — |
| `loading` | `boolean` | `false` |

**Events** : `select(entry)` — émis au clic d'un point ; le parent peut entrer en mode snapshot.

**Comportement** : `<VizLineChart>` ; tooltip au survol = `Date FR + score + version v.X`.

---

## `<SnapshotToggle>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `entries` | `ScoreHistoryEntryVM[]` | — |
| `active` | `boolean` | `false` |
| `frozenCalculationId` | `string \| null` | `null` |

**Events** :

- `enter(calcId: string)` — appelle `store.enterSnapshot(calcId)`.
- `exit()` — `store.exitSnapshot()`.

**Comportement** : `<UiSwitch>` + sélecteur calendrier (issu d'`<UiSelect>` listant les `entries` avec date FR). Quand `active`, bandeau « SNAPSHOT du JJ/MM/AAAA — version v.X » non dismissible en haut de la page.

---

## `<ExportPdfButton>` (P2)

**Props** :

| Nom | Type | Default |
|---|---|---|
| `referentielCode` | `string` | — |
| `frozenCalculationId` | `string \| null` | `null` |

**Comportement** : si feature flag `F51_PDF_EXPORT` désactivé → `<UiButton disabled tooltip="Disponible bientôt">`. Sinon, télécharge le PDF via l'endpoint F51.

---

## `<EmptyNoCalculation>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `referentielCode` | `string` | — |

**Events** : `start()` — déclenche `store.recompute(refCode)`.

**Comportement** : `<UiEmptyState>` avec illustration + titre « Lancez votre premier diagnostic » + bouton CTA.

---

## `<RevokedSourceBadge>`

**Props** :

| Nom | Type | Default |
|---|---|---|
| `sourceId` | `string` | — |

**Comportement** : `<UiBadge variant="warning">` + `<UiTooltip>` « Source révoquée — la valeur n'est plus probante ». Aucun event.

---

## Modifications de composants existants

### `frontend/app/components/dashboard/CardScoringSummary.vue` (F44)

**Avant** : fetch interne via `$fetch('/me/scoring/...')`.
**Après** : lit `useScoringStore` ; au mount, garantit que `summariesByRef[defaultRef]` est chargé. Le bouton « Voir le scoring complet » lie vers `/scoring`.

### `frontend/app/locales/fr.ts`

Ajout du namespace :

```ts
scoring: {
  pageTitle: 'Scoring ESG',
  pillars: { E: 'Environnement', S: 'Social', G: 'Gouvernance' },
  status: { covered: 'Renseigné', missing: 'À renseigner' },
  buttons: {
    recalc: 'Recalculer',
    compare: 'Comparer',
    edit: 'Modifier',
    export: 'Exporter PDF',
    complete: 'Compléter',
    startDiagnostic: 'Lancez votre premier diagnostic',
  },
  snapshot: {
    title: 'Snapshot du {date} — version v.{version}',
    enter: 'Voir snapshot',
    exit: 'Revenir à l\'état courant',
    cannotEdit: 'Mode snapshot — sortez du mode pour modifier',
  },
  errors: {
    unknownReferentiel: 'Référentiel inconnu — retour à la liste',
    revokedSource: 'Source révoquée — la valeur n\'est plus probante',
    notEditableHere: 'Cet indicateur ne peut pas être édité directement ici. Ouvrez la conversation pour le compléter.',
    recomputeFailed: 'Le recalcul a échoué : {reason}',
  },
  empty: {
    noCalculation: 'Aucun calcul de score pour ce référentiel.',
    noMissing: 'Tous les indicateurs sont renseignés.',
  },
},
```
