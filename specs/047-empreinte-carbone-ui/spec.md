# Feature Specification: Empreinte carbone UI (UI de F28)

**Feature Branch**: `047-empreinte-carbone-ui`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "F47 — Empreinte carbone UI (UI de F28). Page `/carbone` : la PME calcule, visualise et suit son empreinte CO2e par Scope (1, 2, 3) avec drilldown par poste. Calcul traçable jusqu'au facteur d'émission (P1 + P4). Style : grands KPIs lisibles (`12.4 tCO2e`), donut Scope 1/2/3, line chart évolution annuelle, table détail triable."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vue synthèse de l'empreinte (Priority: P1)

La PME ouvre `/carbone` et voit immédiatement, au-dessus de la ligne de flottaison, son empreinte totale (`tCO2e`), la répartition Scope 1/2/3 (donut), le delta vs année N-1, et le taux de couverture des données. Elle comprend en moins de 10 secondes l'ordre de grandeur de son impact et la qualité de son inventaire.

**Why this priority**: C'est la valeur immédiate de la page : sans synthèse lisible, la PME ne perçoit ni l'effort ni la trajectoire. Tout le reste de la page (drilldown, recalcul, comparateur) sert à creuser cette synthèse.

**Independent Test**: Charger `/carbone` avec un jeu de données simulé non vide → vérifier qu'un KPI total `tCO2e` (deux décimales, `tabular-nums`), un donut Scope 1/2/3, un KPI delta vs N-1 (signe + couleur) et un KPI couverture % sont affichés et cohérents avec les données.

**Acceptance Scenarios**:

1. **Given** la PME a une empreinte complète pour l'année courante et N-1, **When** elle ouvre `/carbone`, **Then** le KPI total, le donut Scope 1/2/3, le delta % vs N-1 et la couverture % apparaissent au-dessus de la ligne de flottaison sans scroll.
2. **Given** une empreinte courante existe mais aucune donnée N-1, **When** la page charge, **Then** le delta vs N-1 affiche un état neutre (`—`) et un libellé explicite ("Pas de comparaison disponible") plutôt qu'une valeur trompeuse.
3. **Given** la couverture est inférieure à 60 %, **When** la PME consulte la synthèse, **Then** un avertissement visuel signale que l'empreinte est partielle et invite à compléter l'inventaire.

---

### User Story 2 - Drilldown par scope avec traçabilité du facteur (Priority: P1)

La PME déplie chaque Scope (1, 2, 3) en accordéon pour voir les postes (combustion fixe / mobile / fugitives en S1, électricité / vapeur / chaleur / froid en S2, 5 catégories MVP en S3 : achats, transport amont, déchets, déplacements, transport aval). Pour chaque ligne elle voit la valeur d'activité, l'unité, le facteur d'émission appliqué et peut consulter la source de ce facteur via un pin "Source".

**Why this priority**: La traçabilité jusqu'au facteur (P1 Sourcing, P4 Versioning) est non-négociable : sans elle, l'empreinte n'est pas opposable et la PME ne peut pas justifier ses chiffres à un financeur ou auditeur.

**Independent Test**: Déplier le Scope 1 → vérifier que chaque ligne expose `valeur + unité + facteur (valeur, unité, version, période validité)` et qu'un clic sur le pin "Source" ouvre la fiche de la source vérifiée correspondante.

**Acceptance Scenarios**:

1. **Given** une donnée d'activité Scope 1 (combustion gaz naturel, 12 000 kWh) avec un facteur d'émission versionné, **When** la PME déplie Scope 1, **Then** la ligne affiche la valeur, l'unité (`kWh`), le facteur (`kgCO2e/kWh`, version, valid_from), et le pin source est cliquable.
2. **Given** une ligne Scope 2 électricité, **When** la PME survole la mention "market vs location-based", **Then** une infobulle explique la différence et indique laquelle est utilisée par défaut.
3. **Given** un facteur a été révisé entre l'année N-1 et l'année courante, **When** la PME consulte la même ligne sur les deux années, **Then** chaque ligne référence sa propre version de facteur (jamais réécrite rétroactivement).

---

### User Story 3 - Saisie / modification d'une donnée d'activité (Priority: P1)

La PME corrige une consommation d'électricité ou ajoute un poste manquant. La saisie se fait dans une bottom sheet (jamais inline) avec input numérique, sélecteur d'unité et **source obligatoire** (justificatif PDF, lien, ou note "déclaratif"). À la validation, l'empreinte est recalculée et la nouvelle valeur, le delta induit et l'audit (qui, quand, source) sont visibles.

**Why this priority**: Sans la possibilité d'éditer manuellement (P8 Bidirectional sync), la PME est prisonnière du calcul automatique et ne peut pas corriger une erreur d'extraction LLM. C'est le pivot de confiance.

**Independent Test**: Cliquer "Modifier" sur une ligne S2 électricité → bottom sheet s'ouvre avec input + unit + champ source → soumettre une nouvelle valeur → la ligne se met à jour, l'empreinte totale est recalculée, l'événement est visible dans l'historique d'audit.

**Acceptance Scenarios**:

1. **Given** une ligne S2 électricité à 50 000 kWh, **When** la PME clique "Modifier" et saisit 45 000 kWh avec source "facture EDF mars 2026", **Then** la ligne se met à jour, le KPI total et le donut sont recalculés, et un évènement d'audit est enregistré (`source_of_change = manual`).
2. **Given** la PME tente de soumettre une nouvelle valeur sans renseigner de source, **When** elle clique "Valider", **Then** la soumission est refusée avec un message explicite ("Source obligatoire pour toute donnée carbone").
3. **Given** une donnée a été écrite par le LLM, **When** la PME la modifie manuellement, **Then** le contexte LLM est invalidé immédiatement et la donnée est marquée `source_of_change = manual` (pas de reprise silencieuse).

---

### User Story 4 - Évolution annuelle par scope (Priority: P1)

La PME visualise l'évolution de son empreinte sur l'année courante vs N-1, segmentée par Scope, sous forme de courbe. Elle identifie immédiatement les pics, les baisses, et la tendance générale.

**Why this priority**: Sans courbe de progression, la PME ne peut ni mesurer ses efforts de réduction ni alimenter un narratif crédible auprès d'un financeur. C'est la dimension temporelle de la valeur de la page.

**Independent Test**: Charger `/carbone` avec deux années de données → vérifier que la courbe affiche au minimum 2 séries (par scope ou cumulé), avec axe X temporel et axe Y en `tCO2e`, et que la légende permet d'isoler chaque scope.

**Acceptance Scenarios**:

1. **Given** des données mensuelles pour N et N-1, **When** la PME consulte la courbe, **Then** chaque mois est représenté pour les deux années, avec une distinction visuelle claire (couleur, motif).
2. **Given** la PME clique sur la légende "Scope 2", **When** elle masque cette série, **Then** la courbe se met à jour sans rechargement et le total affiché reflète uniquement les scopes visibles.

---

### User Story 5 - Recalcul global manuel (Priority: P1)

La PME déclenche un recalcul de toute son empreinte à partir des données et facteurs courants (utile après un import massif, un changement de facteurs, ou pour s'assurer de la cohérence). Un indicateur visuel signale le travail en cours et l'horodatage du dernier calcul est affiché.

**Why this priority**: Le recalcul transparent et déclenchable est un acte de réassurance. Sans lui, la PME peut douter que les chiffres affichés sont à jour.

**Independent Test**: Cliquer le bouton "Recalculer" → un spinner global apparaît → au retour, l'horodatage "Dernier calcul" se met à jour et le KPI total reflète l'état le plus récent. Durée perçue < 2 s pour 30 lignes.

**Acceptance Scenarios**:

1. **Given** la PME a 30 lignes d'activité, **When** elle clique "Recalculer", **Then** un spinner global s'affiche, le bouton est désactivé, et au retour (< 2 s), l'horodatage et les KPIs sont mis à jour.
2. **Given** le recalcul échoue (backend indisponible), **When** la promesse rejette, **Then** un message d'erreur français explicite s'affiche et l'état précédent est préservé.

---

### User Story 6 - Wizard empty-state (Priority: P1)

La PME n'a aucune donnée carbone. À la place de la synthèse, elle voit un wizard 3 étapes (énergie → déplacements → achats) propulsé par la bottom sheet `show_form` qui lui permet, en moins de 5 minutes, d'obtenir un premier bilan complet.

**Why this priority**: L'onboarding sur le carbone est le principal frein. Sans un parcours guidé, la PME quitte la page sans avoir rien produit.

**Independent Test**: Ouvrir `/carbone` avec un compte vide → vérifier que la synthèse est remplacée par un wizard 3 étapes avec progression visible. Compléter les 3 étapes → vérifier qu'un bilan est généré, le wizard disparaît, et la synthèse s'affiche.

**Acceptance Scenarios**:

1. **Given** un compte sans aucune donnée d'empreinte, **When** la PME ouvre `/carbone`, **Then** la synthèse est masquée et un wizard 3 étapes (énergie / déplacements / achats) s'affiche avec une indication de progression.
2. **Given** la PME complète les 3 étapes, **When** elle valide la dernière, **Then** un bilan initial est calculé, le wizard se ferme et la vue synthèse s'affiche avec les nouvelles données.
3. **Given** la PME quitte le wizard à mi-parcours, **When** elle revient sur `/carbone`, **Then** ses réponses partielles sont conservées et elle peut reprendre où elle s'était arrêtée.

---

### User Story 7 - Synchronisation avec le chat (Priority: P1)

La PME discute dans le chat avec l'IA, qui met à jour une donnée carbone (ex. "ajoute 8 000 km de déplacements professionnels"). La page `/carbone`, si elle est ouverte, se met à jour automatiquement sans rechargement.

**Why this priority**: La cohérence entre chat et UI est constitutionnelle (P8). Sans synchronisation, la PME perd confiance dans la valeur affichée.

**Independent Test**: Ouvrir `/carbone` dans un onglet, déclencher dans un autre onglet une mutation `entity_updated{carbon_footprint}` → vérifier que la ligne concernée et les KPIs agrégés se rafraîchissent automatiquement.

**Acceptance Scenarios**:

1. **Given** `/carbone` est affichée, **When** un évènement `entity_updated{carbon_footprint}` est reçu, **Then** seules les lignes concernées et les agrégats sont mis à jour (pas de rechargement complet de la page).

---

### User Story 8 - Comparateur de référentiels de facteurs (Priority: P2)

La PME bascule entre deux référentiels de facteurs (ex. ADEME 2024 vs IPCC AR6) via un switch et voit en temps réel l'impact sur ses totaux. Une mention claire indique qu'il s'agit d'une **estimation** et non d'une référence officielle.

**Why this priority**: Utile pour benchmarker et négocier (financeurs internationaux peuvent demander IPCC), mais non bloquant pour le MVP.

**Independent Test**: Avec une empreinte calculée sur ADEME, basculer sur IPCC → vérifier que le KPI total et le donut se mettent à jour, et qu'un badge "estimation" est visible. Rebasculer → l'état d'origine est restauré.

**Acceptance Scenarios**:

1. **Given** un référentiel ADEME 2024 actif, **When** la PME bascule vers IPCC AR6, **Then** les KPIs et le donut se recalculent et un badge "Estimation, pas référence officielle" apparaît.
2. **Given** le switch est sur IPCC, **When** la PME quitte la page, **Then** le référentiel par défaut (ADEME 2024) est restauré au prochain chargement (le switch n'est pas persistant).

---

### User Story 9 - Export du bilan en PDF (Priority: P2)

La PME exporte son bilan carbone en PDF avec annexe "Sources et références" auto-générée, prête à transmettre à un financeur ou auditeur.

**Why this priority**: Valeur forte pour la PME mais dépend de la fonctionnalité PDF transverse (F51) ; reportable post-MVP de la page elle-même.

**Independent Test**: Cliquer "Exporter PDF" → un fichier PDF est généré contenant la synthèse, le détail par scope, et une annexe sources listant chaque facteur cité.

**Acceptance Scenarios**:

1. **Given** une empreinte complète, **When** la PME clique "Exporter PDF", **Then** un PDF est produit incluant la synthèse, les drilldowns et l'annexe "Sources et références" avec une entrée par facteur cité.

---

### Edge Cases

- **Pas de N-1** : delta affiché en état neutre, pas de signe trompeur.
- **Couverture < 60 %** : avertissement visuel + invitation à compléter.
- **Facteur révoqué entre deux années** : la donnée historique conserve son facteur d'origine ; la donnée courante utilise la version active. Aucune réécriture rétroactive.
- **Conversion d'unités** : kWh / MJ / litres explicitement convertis avant application du facteur ; la conversion est visible dans la fiche détail.
- **Saisie sans source** : refusée systématiquement avec message clair.
- **Mutation chat pendant édition manuelle** : l'édition manuelle l'emporte ; un message signale que la donnée a été modifiée parallèlement.
- **Historique long (5+ ans, 200+ lignes)** : la table détail est virtualisée pour préserver le LCP.
- **Recalcul échoué** : état précédent préservé, message d'erreur explicite, possibilité de réessayer.
- **Référentiel comparé indisponible** : le switch est désactivé avec une infobulle explicative ; pas d'état cassé.
- **Wizard interrompu** : réponses partielles conservées entre sessions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT afficher sur `/carbone` une vue synthèse comprenant : KPI total `tCO2e` (2 décimales, `tabular-nums`), donut Scope 1/2/3, KPI delta % vs N-1, KPI couverture %.
- **FR-002** : Le système DOIT permettre le drilldown par scope (accordéon) avec, par ligne : valeur d'activité, unité, facteur d'émission appliqué et accès à la source du facteur.
- **FR-003** : Le système DOIT supporter les 3 postes du Scope 1 (combustion fixe, mobile, fugitives), les 4 postes du Scope 2 (électricité, vapeur, chaleur, froid avec mention market vs location-based), et 5 catégories du Scope 3 (achats, transport amont, déchets, déplacements, transport aval).
- **FR-004** : Le système DOIT permettre l'édition d'une donnée d'activité via une bottom sheet (jamais inline) avec input numérique, sélecteur d'unité et champ source obligatoire.
- **FR-005** : Le système DOIT recalculer l'empreinte automatiquement après chaque modification d'une donnée d'activité.
- **FR-006** : Le système DOIT exposer un bouton "Recalculer" déclenchant un recalcul global avec spinner et horodatage du dernier calcul.
- **FR-007** : Le système DOIT afficher une courbe d'évolution annuelle (année courante vs N-1) segmentée par scope, avec légende interactive.
- **FR-008** : Le système DOIT, en cas d'absence totale de données, présenter un wizard 3 étapes (énergie → déplacements → achats) propulsé par la bottom sheet et préservant les réponses partielles.
- **FR-009** : Le système DOIT s'abonner aux évènements de mutation d'entité `carbon_footprint` et mettre à jour les seules zones impactées sans rechargement de page.
- **FR-010** : Le système DOIT garantir la traçabilité de chaque calcul jusqu'au facteur d'émission utilisé (version, valid_from, source vérifiée).
- **FR-011** : Le système DOIT empêcher toute soumission de donnée d'activité sans source renseignée.
- **FR-012** : Le système DOIT afficher un avertissement visuel quand la couverture des données est inférieure à 60 %.
- **FR-013** : Le système DOIT afficher un état neutre explicite quand la comparaison vs N-1 est indisponible.
- **FR-014** : Le système DOIT proposer un comparateur de référentiels de facteurs (ADEME 2024, IPCC AR6) recalculant les totaux en temps réel et marquant le résultat comme "estimation, pas référence officielle". *(P2)*
- **FR-015** : Le système DOIT permettre l'export du bilan complet en PDF avec annexe sources et références. *(P2, dépend de F51)*
- **FR-016** : Le système DOIT virtualiser la table de détail au-delà d'un seuil (centaine de lignes) pour préserver les performances.
- **FR-017** : Le système DOIT préserver l'état précédent et afficher un message d'erreur français explicite si un recalcul échoue.
- **FR-018** : Toute conversion d'unité (kWh, MJ, litres, etc.) DOIT être explicite et visible dans la fiche détail de la ligne concernée.
- **FR-019** : Le système DOIT enregistrer dans l'audit toute modification d'une donnée d'activité (auteur, horodatage, source du changement, ancienne et nouvelle valeur).

### Key Entities *(include if feature involves data)*

- **Empreinte carbone (carbon_footprint)** : agrégation par PME et par période (année), regroupant les données d'activité par scope, le total `tCO2e`, la couverture %, et l'horodatage du dernier calcul.
- **Donnée d'activité (carbon_data)** : valeur numérique + unité, rattachée à un scope et à un poste, datée, avec source obligatoire et référence au facteur d'émission appliqué.
- **Facteur d'émission (facteur_emission)** : valeur en `kgCO2e/<unité>`, versionné (version, valid_from, valid_to), rattaché à un référentiel (ADEME 2024, IPCC AR6, …) et à une source vérifiée. Jamais réécrit (P4).
- **Source** : référence vérifiable (document, URL, mention déclarative) attachée à toute donnée et à tout facteur (P1).
- **Évènement d'audit** : trace immuable de chaque mutation (qui, quand, ancienne et nouvelle valeur, source du changement) (P3).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME novice obtient un premier bilan carbone complet (synthèse + drilldown) en moins de 5 minutes via le wizard empty-state, à partir d'un compte vide.
- **SC-002** : Modifier une consommation d'électricité (édition d'une ligne S2) déclenche un recalcul visible et un delta % vs valeur précédente affiché en moins de 2 secondes après validation.
- **SC-003** : Le basculement entre référentiels de facteurs (ADEME ↔ IPCC) recalcule et réaffiche les totaux en moins de 1 seconde côté utilisateur.
- **SC-004** : Sur un inventaire de 30 lignes, le recalcul global complet rend la main à l'utilisateur en moins de 2 secondes.
- **SC-005** : 100 % des lignes affichées exposent leur facteur d'émission et l'accès à la source de ce facteur (traçabilité P1/P4 complète).
- **SC-006** : 0 soumission de donnée d'activité sans source acceptée par le système (vérifié par tests).
- **SC-007** : Le LCP de `/carbone` reste sous 1.8 seconde sur un inventaire représentatif.
- **SC-008** : Donut Scope 1/2/3 et courbe d'évolution annuelle accessibles au clavier (focus visible, navigation séquentielle, valeurs annoncées).
- **SC-009** : Une mutation `entity_updated{carbon_footprint}` propagée par le chat met à jour les zones impactées de la page en moins de 1 seconde, sans rechargement de page.
- **SC-010** : Au minimum 90 % des sessions ouvrant `/carbone` avec un inventaire vide complètent le wizard 3 étapes (objectif d'engagement onboarding).

## Assumptions

- L'API backend de F28 (carbon_footprint, facteur_emission) est disponible et expose les endpoints nécessaires : lecture de l'empreinte courante et historique, modification d'une donnée d'activité, recalcul global, switch de référentiel.
- Les briques transverses sont disponibles : design system (F36), primitives UI (F37), shell de navigation (F38), bottom sheet engine (F39), bibliothèque de visualisations dont donut, line chart et `<VizSourcePin>` (F40).
- Les facteurs d'émission sont versionnés côté backend conformément à P4 (jamais écrasés ; chaque ligne historique conserve son facteur d'origine).
- La synchronisation chat ↔ UI s'appuie sur l'EventBus / SSE défini par F41.
- L'export PDF (US9) dépend de F51 et peut être livré après le reste de la page sans bloquer le MVP.
- Le wizard empty-state utilise la mécanique `show_form` de la bottom sheet F39 ; aucun input n'est inline.
- Les conversions d'unités (kWh ↔ MJ, litres ↔ kg, etc.) sont effectuées par le backend ; l'UI n'effectue que l'affichage et le rappel explicite de la conversion.
- 5 catégories Scope 3 (achats, transport amont, déchets, déplacements, transport aval) suffisent pour le MVP ; les 10 autres catégories GHG Protocol sont post-MVP.
- Trajectoire SBTi, cartographie supply chain physique et TNFD biodiversité sont explicitement hors-scope MVP.
- La langue par défaut de toutes les chaînes utilisateur est le français (constitution).
- Le référentiel par défaut est ADEME 2024 ; le switch IPCC AR6 n'est pas persistant entre sessions au MVP.
