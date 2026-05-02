# F46 — Scoring ESG visualisations UI (UI de F23)

**Phase** : D — Tableaux de bord & visualisations métier
**Modules brainstorm** : 3.0 scoring multi-référentiels
**Dépendances** : F36, F37, F38, F40, F23 backend, F09 référentiels
**Estimation** : 3.5 jours

## Contexte et objectif

Page **`/scoring`** : score ESG par référentiel (BOAD, CDP, GRI, ODD), drilldown indicateur, comparaison entre référentiels, source des données. Doit **rassurer par sa transparence** : chaque indicateur cliquable → source (P1), version référentiel (P4), date de calcul.

## User Stories

- **US1 Vue d'ensemble (P1)** — score global tabular-nums, `<VizRadarChart>` E/S/G, KPI couverture %, date dernier calcul. Sources cliquables F40.
- **US2 Sélecteur référentiel (P1)** — pills/tabs : BOAD-default, CDP, GRI, ODD-aligned, custom. `GET /me/scores?referentiel_code=...`.
- **US3 Comparaison multi-référentiels (P1)** — bouton "Comparer" → `<VizBarChart>` horizontal côte à côte.
- **US4 Drilldown par pillier (P1)** — accordion E/S/G : indicateurs avec score, statut (couvert/manquant), `(source)`. Click → drawer détail.
- **US5 Drawer détail indicateur (P1)** — slide-in droite : nom, définition, valeur, unité, formule, sources, historique 12 derniers points (`<VizLineChart>`), bouton "Modifier" → bottom sheet F39 `ask_number`.
- **US6 Indicateurs manquants (P1)** — section "À renseigner", CTA "Compléter" → ouvre chat F41 contexte.
- **US7 Recalcul (P1)** — `POST /me/score/calculate?referentiel_code=...` + spinner + nouveau résultat.
- **US8 Historique scores (P1)** — `<VizLineChart>` 12 derniers calculs, hover = date + valeur + version référentiel.
- **US9 Snapshot intangible (P1)** — toggle "Voir snapshot" → freeze view sur version donnée (P4 versioning).
- **US10 Export rapport scoring (P2)** — bouton "Exporter PDF" → F51.
- **US11 Sync chat (P1)** — `useChatEventBus` listen `entity_updated{indicateur,score_calculation}` → refresh.
- **US12 Empty state (P1)** — pas de calcul → "Lancez votre premier diagnostic" CTA.

## Exigences fonctionnelles

- **FR-001** : `pages/scoring/index.vue` + `pages/scoring/[referentiel_code].vue` + `components/scoring/{ReferentielTabs,PillarAccordion,IndicateurDrawer,RecalcButton}.vue`.
- **FR-002** : Pinia `useScoringStore` (scores by referentiel, indicators, history).
- **FR-003** : Drawer indicateur = `<UiModal>` ou `<UiPopover>` slide-in droite.
- **FR-004** : Modifier valeur via `<ChatBottomSheet ask_number>` (F39).
- **FR-005** : `<VizSourcePin>` F40 sur chaque indicateur (P1).
- **FR-006** : Snapshot = state read-only, pas de mutation possible.
- **FR-007** : Tabs URL persistées (`/scoring/boad`, `/scoring/cdp`).

## Exigences non-fonctionnelles

- **NFR-001** : LCP < 2 s (charts + 50+ indicateurs).
- **NFR-002** : Switch tab < 200 ms (cache pinia).
- **NFR-003** : Drilldown sans rechargement complet.

## Success Criteria

- **SC-001** : Radar 3 axes + score + sources cliquables.
- **SC-002** : Click indicateur "Émissions GES" → drawer historique 12 mois.
- **SC-003** : Modifier valeur via sheet → score recalculé auto (F23).
- **SC-004** : Comparer BOAD vs CDP → bar chart côte à côte.

## Hors-scope MVP

- Édition pondération (admin F09) → P2.
- Suggestion AI inline → couvert plan F45.
- Comparaison vs benchmark sectoriel → post-MVP.
- Heatmap → post-MVP.

## Risques et points de vigilance

- 50+ indicateurs : virtualisation accordion si > 30.
- Source révoquée : badge warning, valeur grisée.
- Snapshot mode : verrouiller mutations.
- Radar > 6 points : passer en bar vertical (lisibilité).
