# Feature 028 — Empreinte Carbone (MVP minimal)

**Branch**: `028-empreinte-carbone-complete` | **Date**: 2026-04-29
**Source brief**: `docs_et_brouillons/features/28-empreinte-carbone-complete.md`

## Scope MVP livré

US1 partiel + US2 (calcul) + US3 (facteurs sourcés) + US5 stub (plan réduction).
Reporté `[DEFERRED]` : questionnaire conversationnel complet, frontend Vue, intégration F15/F16,
Scope 3 exhaustif, US6 objectifs, US7 tool LLM, comparaison sectorielle.

## User Stories livrées

- **US2 (P1)** : `POST /me/carbon/compute` calcule total tCO2e + breakdown par scope/catégorie à partir d'un `source_data` structuré (énergie/transport/déchets simplifiés).
- **US3 (P1)** : chaque ligne du breakdown porte le `factor_id`, la valeur du facteur, son unité et son `source_id` (cohérence F03/F09).
- **US5 stub (P1)** : `GET /me/carbon/{year}/reduction-plan` retourne 3-5 actions priorisées seedées en dur (catégorie : énergie/transport/déchets) avec impact estimé.

## Exigences fonctionnelles MVP

- **FR-001** : `CarbonService.compute_footprint(db, account_id, entreprise_id, year, source_data) -> CarbonResult`.
- **FR-002** : Table `carbon_footprint` (id, account_id, entreprise_id, year, source_data_json, total_tco2e, by_scope_json, breakdown_json, factor_versions_json, computed_at, version).
- **FR-003** : Endpoints `POST /me/carbon/compute`, `GET /me/carbon/{year}`, `GET /me/carbon/{year}/reduction-plan`.
- **FR-004** : Lookup F09 via `code` + `pays_iso2` + `valid_from_date <= year-12-31` (snapshotté dans `factor_versions_json`).
- **FR-005** : Plan réduction stub — bibliothèque inline (pas de table dédiée en MVP, `[DEFERRED]` table `action_reduction`).

## Exigences non-fonctionnelles

- **NFR-001** : calcul < 200ms sur source_data type (≤ 20 lignes).
- **NFR-002** : tests ≥ 80 % sur engine + service + router.
- **NFR-003** : RLS via `account_id`. Écriture audit `carbon_footprint:compute` (cohérent F04).

## Success criteria MVP

- SC-001 : POST avec source_data (`electricite_kwh`, `diesel_litres`, `vehicule_km`) → réponse contient `total_tco2e > 0` + `breakdown[].factor_source_id`.
- SC-002 : GET récupère le dernier calcul d'une année.
- SC-003 : GET reduction-plan retourne ≥ 3 actions.

## Hors scope MVP `[DEFERRED]`

- Questionnaire conversationnel (US1 complet, F15/F16 viz).
- Comparaison sectorielle, line/pie chart (US4 frontend).
- US6 objectifs, US7 tool LLM compute_carbon_footprint.
- Table `action_reduction` seedée → bibliothèque inline pour MVP.
- Frontend `/profil/carbone`.
- Scope 3 exhaustif (achats amont/aval).
