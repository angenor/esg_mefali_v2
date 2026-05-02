# F47 — Empreinte carbone UI (UI de F28)

**Phase** : D — Tableaux de bord & visualisations métier
**Modules brainstorm** : 3.2 empreinte carbone Scope 1/2/3
**Dépendances** : F36, F37, F38, F39, F40, F28 backend (carbon_footprint, facteur_emission)
**Estimation** : 3 jours

## Contexte et objectif

Page **`/carbone`** : la PME calcule, visualise et suit son empreinte CO2e par Scope (1, 2, 3) avec drilldown par poste. Calcul **traçable jusqu'au facteur d'émission** (P1 + P4).

Style : grands KPIs lisibles (`12.4 tCO2e`), donut Scope 1/2/3, line chart évolution annuelle, table détail triable.

## User Stories

- **US1 Vue synthèse (P1)** — KPI global `tCO2e`, donut Scope 1/2/3, KPI "vs N-1" delta %, couverture %.
- **US2 Drilldown Scope 1 (P1)** — combustion fixe / mobile / fugitives. Chaque ligne : valeur, unit, facteur (popover source F40).
- **US3 Drilldown Scope 2 (P1)** — électricité, vapeur, chaleur, froid. Mention market vs location-based.
- **US4 Drilldown Scope 3 (P1)** — 15 catégories GHG Protocol, MVP 5 : achats, transport amont, déchets, déplacements, transport aval.
- **US5 Saisie / modification (P1)** — bouton "Modifier" → `<ChatBottomSheet ask_number>` F39 (input + unit + source obligatoire).
- **US6 Évolution temporelle (P1)** — `<VizLineChart>` année courante vs N-1 par scope.
- **US7 Recalcul (P1)** — `POST /me/carbon/calculate`, spinner global.
- **US8 Comparateur facteurs (P2)** — switch ADEME 2024 / IPCC AR6, recalcule temps réel.
- **US9 Empty state (P1)** — wizard 3 étapes (énergie + déplacements + achats).
- **US10 Export bilan PDF (P2)** — F51.
- **US11 Sync chat (P1)** — `useChatEventBus` listen `entity_updated{carbon_footprint}` → refresh.

## Exigences fonctionnelles

- **FR-001** : `pages/carbone/index.vue` + `components/carbone/{ScopeAccordion,EmissionLine,RecalcStrip}.vue`.
- **FR-002** : Pinia `useCarbonStore`.
- **FR-003** : KPIs `tabular-nums` + unit standardisée `tCO2e`.
- **FR-004** : Modification → `PATCH /me/carbon/data/{id}` + recalcul auto.
- **FR-005** : `<VizSourcePin>` F40 obligatoire sur chaque ligne.
- **FR-006** : Wizard empty-state via bottom sheet F39 (`show_form` 3 étapes).

## Exigences non-fonctionnelles

- **NFR-001** : LCP < 1.8 s.
- **NFR-002** : Recalcul backend < 2 s pour 30 lignes.
- **NFR-003** : Donut + line chart accessibles clavier.

## Success Criteria

- **SC-001** : Vue synthèse mock data, donut + KPI corrects.
- **SC-002** : Modifier conso électricité → empreinte recalculée + delta % affiché.
- **SC-003** : Switch facteurs ADEME → IPCC → totaux changent.
- **SC-004** : Wizard empty-state : 3 saisies → bilan complet.

## Hors-scope MVP

- 15 catégories Scope 3 complètes → MVP 5.
- Trajectoire SBTi → post-MVP.
- Cartographie supply chain physique → post-MVP.
- TNFD biodiversité → post-MVP.

## Risques et points de vigilance

- Facteurs versionnés (P4), pas écrasés.
- Saisie kWh / MJ / litres : conversions explicites.
- Comparateur facteurs : marquer "estimation, pas référence officielle".
- Historique long : virtualiser.
