# F28 — Calculateur d'Empreinte Carbone (questionnaire + calcul + facteurs sourcés + plan réduction)

**Phase** : 7 — Empreinte Carbone (Module 4)
**Modules brainstorm** : 4.1 (Questionnaire conversationnel), 4.2 (Calcul et visualisation), 4.3 (Plan de réduction)
**Dépendances** : F09 (facteurs émission), F11, F15, F16
**Estimation** : 2.5 jours

## Contexte et objectif

Calculateur d'empreinte carbone **adapté au contexte africain** : questionnaire conversationnel via le LLM, exemples concrets, unités locales, facteurs sourcés ADEME/IPCC/IEA, mix électrique par pays UEMOA.

Visualisation claire (KPI, répartition, comparaison sectorielle, évolution) + plan de réduction priorisé avec actions quick-wins / long terme et estimation des économies financières.

## User Stories

### US1 — Questionnaire conversationnel adapté (P1)
**En tant que** PME,
**je veux** que le LLM me pose des questions ciblées via les tools `ask_*` (F15) sur :
- Énergie (électricité, générateurs diesel, gaz),
- Transport (véhicules de service, livraisons fréquence/distances),
- Déchets (volumes, traitement),
- Achats (matières premières, fournitures).

**afin de** ne pas remplir un formulaire fastidieux.

**Spécificité africaine** : "combien de jours par mois utilisez-vous le générateur ?", "à quelle distance se trouve votre site principal ?", unités locales (litres, km, kWh).

### US2 — Calcul tCO2e par scope et par catégorie (P1)
**En tant que** PME,
**je veux** voir mon empreinte annuelle en tCO2e décomposée par :
- Scope 1 (combustion directe : générateurs, véhicules),
- Scope 2 (électricité achetée),
- Scope 3 (achats, déchets, transport amont/aval) — partiel en MVP.

**afin de** comprendre la structure de mes émissions.

### US3 — Facteurs d'émission sourcés (P1)
**En tant que** PME,
**je veux** voir le facteur utilisé pour chaque calcul avec sa source cliquable (cohérent F03), exemple :
- "Mix électrique Côte d'Ivoire 2024 : 0,456 kgCO2e/kWh — source ADEME Base Carbone v23 page 87".

**afin de** vérifier la rigueur.

**Données** :
- ADEME Base Carbone v23 (gratuit, contient des facteurs Afrique),
- IPCC AR6 (combustion fossile),
- IEA Africa Energy Outlook (mix électrique pays UEMOA),
- Mix électrique 8 pays UEMOA stocké en table `facteur_emission` (F09) avec versioning.

### US4 — Visualisations (P1)
**En tant que** PME,
**je veux** :
- `show_kpi_card` : empreinte totale + delta vs année précédente,
- `show_pie_chart` : répartition par source (Scope 1/2/3),
- `show_bar_chart` : comparaison sectorielle (médiane PME africaines même secteur),
- `show_line_chart` : évolution mensuelle/annuelle.

**afin de** visualiser.

### US5 — Plan de réduction priorisé (P1)
**En tant que** PME,
**je veux** une liste d'actions de réduction priorisées par impact CO2 et par ROI financier :
- Quick wins (≤ 6 mois, faible coût) : LED, programmateurs, bonnes pratiques.
- Moyen terme (6-24 mois) : isolation, batteries, optimisation flotte.
- Long terme (24+ mois) : panneaux solaires, fleet électrique, upgrade industriel.

avec estimation **économies financières** (Money typé F05) et **investissement requis**.

### US6 — Suivi des objectifs (P2)
**En tant que** PME,
**je veux** définir un objectif de réduction (ex : -20% en 3 ans), voir une jauge d'avancement, recevoir des rappels (cohérent F31),
**afin de** être motivée et tenue.

### US7 — Tool LLM `compute_carbon_footprint(entreprise_id, year)` (P2)
**En tant que** PME via chat,
**je veux** dire "calcule mon empreinte 2025" → réponse `show_kpi_card` + `show_pie_chart` + texte d'analyse.

## Exigences fonctionnelles

- **FR-001** : Service backend `CarbonService` :
  - `compute_footprint(entreprise_id, year, source_data) -> CarbonResult`,
  - `source_data` est un objet structuré (consommations énergie, transport, déchets, achats),
  - applique les facteurs sourcés via lookup F09 (`get_facteur(code, pays_iso2, year)`),
  - retourne `{total_tco2e, by_scope:{1,2,3}, by_category:[], breakdown:[{source, value, factor, factor_source_id}]}`.
- **FR-002** : Table `carbon_footprint` : `id, account_id, entreprise_id, year, source_data_json, total_tco2e, by_scope_json, breakdown_json, factor_versions_json (snapshot facteurs au moment du calcul), computed_at, version`.
- **FR-003** : Endpoints :
  - `POST /me/carbon/compute` body `{year, source_data}` → calcule et persiste.
  - `GET /me/carbon/{year}` → résultat le plus récent pour cette année.
  - `GET /me/carbon/history` → série temporelle.
  - `GET /me/carbon/{year}/reduction-plan` → plan de réduction généré.
- **FR-004** : Skill `skill_carbon_calc` (cohérent F21 catalog) qui :
  - sait poser les questions adaptées (via `ask_*`),
  - sait orchestrer la collecte (`source_data` complet),
  - sait expliquer les résultats avec sources,
  - sait proposer le plan de réduction.
- **FR-005** : Service `CarbonReductionPlanService` :
  - `generate_plan(footprint_id) -> Plan`,
  - parcourt le breakdown (top contributeurs),
  - matche avec une bibliothèque sourcée d'actions (table `action_reduction` à seeder F09 ou ici),
  - retourne actions priorisées avec coût/économie estimés.
- **FR-006** : Page Vue `/profil/carbone` :
  - Cartes empreinte + delta,
  - Répartition pie/donut + sectoriel bar,
  - Évolution line chart,
  - Section plan de réduction avec checklist d'actions.
- **FR-007** : Tool LLM `compute_carbon_footprint(entreprise_id, year, source_data?)` exposé en F14, utilise `CarbonService`.
- **FR-008** : Pour chaque chiffre affiché, source cliquable (cohérent F03).
- **FR-009** : Le mix électrique par pays UEMOA est seedé en F09 avec sources (ADEME Base Carbone, IEA Africa Energy Outlook).

## Exigences non-fonctionnelles

- **NFR-001** : Calcul d'une empreinte sur source_data complet < 200ms.
- **NFR-002** : Tous les facteurs ont leur source `verified` (cohérent F03).
- **NFR-003** : Cohérence avec les indicateurs ESG : `total_tco2e` peut alimenter l'indicateur `EMISSIONS_SCOPE_1_TCO2E` (etc.) → réutilisable par F23.
- **NFR-004** : Snapshot des facteurs au moment du calcul (FR-002 `factor_versions_json`) — si les facteurs évoluent, l'historique reste comparable.

## Entités clés

- **CarbonFootprint** (FR-002).
- **ActionReduction** (table seedée — `id, code, name, description, category, scope, impact_tco2e_estimated, cout_estime_money, economie_estimee_money, duree_estimee_mois, source_id`).

## Success Criteria

- **SC-001** : PME renseigne ses consommations → empreinte calculée avec source cliquable sur chaque facteur.
- **SC-002** : Plan de réduction propose 5–10 actions priorisées avec ROI.
- **SC-003** : Comparaison sectorielle s'affiche avec moyennes anonymisées.
- **SC-004** : Skill `skill_carbon_calc` orchestre la collecte conversationnelle.

## Hors-scope MVP

- Scope 3 complet (achats amont/aval détaillés) — MVP : version simplifiée.
- Bilan Carbone V8 / GHG Protocol exhaustif (post-MVP).
- Vérification tierce ISAE 3000 (post-MVP, partenariats).
- Carbon offsetting marketplace (post-MVP).
- Empreinte produit/service unitaire (post-MVP).

## Risques et points de vigilance

- **Granularité des données** : une PME ne sait pas toujours sa conso kWh exacte. Proposer estimations à partir de facture FCFA (avec facteur de conversion local).
- **Couverture facteurs Afrique** : ADEME Base Carbone est plutôt FR. Pour spécifiques Afrique, IEA + données locales nationales (ANER Sénégal, ANARE-CI). Sourcer correctement.
- **Mix électrique par pays UEMOA** : à actualiser annuellement. Cohérent avec versioning F04.
- **Plan de réduction qualité** : la bibliothèque d'actions doit être réelle (PNUE, ADEME, BOAD bonnes pratiques) et non pas générique.
- **UX du questionnaire conversationnel** : 20 questions = risqué, perte d'attention. Découper en sessions, sauvegarder progression.
