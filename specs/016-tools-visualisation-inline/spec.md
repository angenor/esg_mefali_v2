# Feature Specification: Tools de Visualisation Inline (F16)

**Feature Branch**: `016-tools-visualisation-inline`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: F16 — Tools de Visualisation Inline (show_kpi_card / show_progress_bar / show_radar_chart / show_bar_chart / show_line_chart / show_pie_chart / show_donut_chart / show_timeline / show_comparison_table / show_match_card / show_map / show_mermaid). Phase 3 — Chat & LLM Tool-Use. Module 1.1.2. Dépendances : F13, F14, F15.

## Clarifications

### Session 2026-04-29

- Q: Validation Mermaid backend — parser AST complet ou whitelist ? → A: Whitelist regex Python sur le mot-clé du diagramme + scan des directives `click...href` + interdiction d'URL externe (MVP).
- Q: Réactivité historique (US13) — recalcul serveur ou badge front ? → A: Badge front "données obsolètes" via comparaison `updated_at` de l'entité référencée vs timestamp du payload ; pas de recalcul serveur.
- Q: `source_ids` requis pour `show_match_card` ? → A: Oui, `source_ids` non vide est obligatoire (références aux critères attestés).
- Q: `show_pie_chart` avec slices à valeur négative ? → A: Rejet validation Pydantic — toutes les `slice.value >= 0`.
- Q: Précision numérique des `value` chiffrées ? → A: `Decimal` côté Pydantic, sérialisé en string en JSON pour préserver la précision (cohérent avec l'invariant Money typé du Module 0).



### User Story 1 - show_kpi_card : Chiffre clé + delta (Priority: P1)

En tant que PME, je veux voir un chiffre clé mis en valeur (ex : "45 tCO2e ↓12% vs 2024") avec son contexte (label, unité), un delta éventuel et sa source cliquable, afin de capter rapidement l'info importante dans le fil de conversation.

**Why this priority**: KPI est le tool le plus universel ; sans lui, la conversation reste textuelle uniquement et perd en clarté pour des chiffres clés (score ESG, empreinte carbone, montant levé).

**Independent Test**: Invoquer `show_kpi_card` avec un payload valide → la carte rend valeur, unité, delta éventuel, label et picto source cliquable.

**Acceptance Scenarios**:

1. **Given** un payload `{label:"Empreinte 2025", value:45, unit:"tCO2e", delta:{value:-12, period:"vs 2024"}, source_ids:[42], alt_text:"..."}`, **When** le LLM invoque `show_kpi_card`, **Then** la carte s'affiche dans la bulle assistant avec valeur, unité, delta coloré, source cliquable.
2. **Given** un payload sans `source_ids` non vide alors que `value` est chiffré, **When** la validation Pydantic s'exécute, **Then** la requête est rejetée et le LLM reçoit un message de retry.
3. **Given** un payload contenant des balises HTML (`<script>`) dans `label`, **When** la validation s'exécute, **Then** la requête est rejetée (anti-XSS).

---

### User Story 2 - show_progress_bar : Avancement vers un objectif (Priority: P1)

En tant que PME, je veux voir une barre de progression "Score ESG actuel 62/100 — seuil GCF 75" avec couleur (rouge < seuil, vert ≥), afin de comprendre l'écart au seuil cible.

**Why this priority**: Cas d'usage central pour la conformité (GCF, BOAD, IFC) — visualise immédiatement la position vs seuil de qualification.

**Independent Test**: Invoquer `show_progress_bar` avec `{label, current, target, unit, source_ids, alt_text}` → barre rendue avec couleur conditionnelle.

**Acceptance Scenarios**:

1. **Given** `current=62, target=75`, **When** rendu, **Then** la barre est rouge et affiche `62/75`.
2. **Given** `current=80, target=75`, **When** rendu, **Then** la barre est verte.

---

### User Story 3 - show_radar_chart : Multi-piliers / multi-référentiels (Priority: P1)

En tant que PME, je veux voir mes scores E/S/G ou la comparaison multi-référentiels (ESG Mefali / GCF / IFC / BOAD) en radar, afin de visualiser mon profil global.

**Why this priority**: Visualisation phare du module ESG — un radar est la meilleure façon de comparer plusieurs piliers ou plusieurs référentiels d'un seul coup d'œil.

**Independent Test**: Invoquer `show_radar_chart` avec `{title, axes:[...], series:[{name, values:[...]}], source_ids, alt_text}` → radar rendu sous 200ms (NFR-001) avec source cliquable.

**Acceptance Scenarios**:

1. **Given** un payload avec 5 axes et 2 séries de mêmes longueurs, **When** rendu, **Then** le radar affiche les 2 polygones colorés différenciés avec légende.
2. **Given** un payload où la longueur des `values` ne correspond pas à `axes`, **When** validation, **Then** rejet Pydantic.

---

### User Story 4 - show_bar_chart : Benchmarking sectoriel / ventilation (Priority: P1)

En tant que PME, je veux voir un graph en barres pour comparer mes scores par référentiel ou ma position dans mon secteur, afin de me situer.

**Independent Test**: Invoquer avec `{title, x_label, y_label, bars:[{label, value}], source_ids, alt_text}` → barres rendues, axes étiquetés, sources cliquables.

**Acceptance Scenarios**:

1. **Given** 4 barres avec valeurs différentes, **When** rendu, **Then** 4 barres triées affichées avec étiquettes axes.

---

### User Story 5 - show_line_chart : Évolution dans le temps (Priority: P1)

En tant que PME, je veux voir l'évolution de mon score ESG ou de mon empreinte carbone sur 12 mois, afin de visualiser la tendance.

**Independent Test**: Invoquer avec `{title, x_label, y_label, series:[{name, points:[{x,y}]}], source_ids, alt_text}` → courbe(s) rendue(s).

**Acceptance Scenarios**:

1. **Given** une série de 12 points, **When** rendu, **Then** courbe lissée avec axes datés.

---

### User Story 6 - show_pie_chart / show_donut_chart : Répartition (Priority: P1)

En tant que PME, je veux voir la répartition de mes émissions par source (énergie 60%, transport 25%, déchets 15%) en camembert ou donut, afin de prioriser les actions.

**Independent Test**: Invoquer avec `{title, slices:[{label, value}], variant:"pie"|"donut", source_ids, alt_text}` → camembert ou donut rendu.

**Acceptance Scenarios**:

1. **Given** 3 slices avec valeurs sommant 100, **When** rendu, **Then** chaque slice affiche pourcentage et label.

---

### User Story 7 - show_timeline : Étapes / roadmap (Priority: P1)

En tant que PME, je veux voir les étapes d'une candidature, la roadmap d'un projet ou les échéances d'une offre en timeline horizontale ou verticale, afin d'anticiper les jalons.

**Independent Test**: Invoquer avec `{title, items:[{date, label, status}], orientation:"horizontal"|"vertical", alt_text}` → timeline rendue.

**Acceptance Scenarios**:

1. **Given** 5 jalons avec statuts (done / in_progress / pending), **When** rendu, **Then** timeline avec couleurs/icônes différenciées par statut.

---

### User Story 8 - show_comparison_table : Tableau A vs B vs C (Priority: P1)

En tant que PME, je veux voir un tableau aligné comparant 2-5 Offres (ou intermédiaires) sur leurs critères, frais, délais, taux de succès, afin de choisir.

**Independent Test**: Invoquer avec `{title, columns:[...], rows:[{label, values:[...]}], source_ids, alt_text}` → tableau rendu, max 5x5.

**Acceptance Scenarios**:

1. **Given** 3 colonnes et 5 lignes, **When** rendu, **Then** tableau aligné avec sources cliquables par cellule chiffrée.
2. **Given** un payload avec 6 lignes, **When** validation, **Then** rejet (max 5 — hors-scope MVP).

---

### User Story 9 - show_match_card : Projet ↔ Offre, score compatibilité (Priority: P1)

En tant que PME, je veux voir une carte avec score de compatibilité (0-100), listing des critères couverts/manquants et lien vers la page candidature, afin de décider de candidater ou non.

**Independent Test**: Invoquer avec `{projet_id, offre_id, score:0-100, criteres_couverts:[...], criteres_manquants:[...], link, source_ids, alt_text}` → carte rendue avec barre de progression du score, listes vert/rouge, CTA.

**Acceptance Scenarios**:

1. **Given** score=72, 8 critères couverts, 3 manquants, **When** rendu, **Then** carte affiche score coloré, listes catégorisées, bouton "Voir candidature".

---

### User Story 10 - Message hybride (texte + visualisation + texte + question) (Priority: P1)

En tant que PME, je veux que le LLM puisse chaîner dans un même tour : texte d'intro + visualisation + texte d'analyse + question QCU pour la suite, afin de vivre une conversation riche.

**Why this priority**: C'est l'expérience cible — sans cela, les visualisations deviennent isolées et perdent leur valeur narrative.

**Independent Test**: Le LLM produit un message multi-parts mêlant `text` et `tool_call` (visualisation + ask_qcu) → l'orchestrateur frontal rend chaque part dans l'ordre dans la même bulle assistant.

**Acceptance Scenarios**:

1. **Given** un message multi-parts (texte + show_radar_chart + texte + ask_qcu), **When** rendu, **Then** chaque part s'affiche dans l'ordre.

---

### User Story 11 - show_map : Localisation (Priority: P2)

En tant que PME, je veux voir une carte avec mon entreprise, mes projets, leurs zones d'impact ou les bureaux des intermédiaires, afin de visualiser géographiquement.

**Acceptance Scenarios**:

1. **Given** une liste de marqueurs `[{lat, lng, label, kind}]`, **When** rendu, **Then** carte affichée avec marqueurs et popups au clic.

---

### User Story 12 - show_mermaid : Diagramme libre fallback (Priority: P2)

En tant que PME, je veux que pour des processus ou diagrammes ad-hoc non couverts par le catalogue typé, le LLM produise du Mermaid validé côté backend (parse avant envoi front) afin de voir un diagramme cohérent ; si invalide, fallback texte.

**Acceptance Scenarios**:

1. **Given** un code Mermaid valide, **When** validation backend, **Then** le code est transmis au front et rendu.
2. **Given** un code Mermaid invalide, **When** validation backend, **Then** rejet + retour `validation_error` au LLM (boucle retry F14).

---

### User Story 13 - Réactivité des visualisations historiques (Priority: P2)

En tant que PME, je veux que si je modifie un projet, les visualisations dans des messages anciens basées sur ce projet affichent un badge "données obsolètes", afin de ne pas être trompée.

**Acceptance Scenarios**:

1. **Given** une visualisation historique référençant `projet_id=42`, **When** le projet est modifié, **Then** la carte affiche un badge "données obsolètes — recalculer ?".

---

### Edge Cases

- Payload avec `value` chiffré sans `source_ids` → rejet validation (sourçage F03 obligatoire).
- Payload contenant `<` ou `>` dans un champ texte → rejet (anti-XSS via `no_html`).
- Payload `show_radar_chart` avec longueurs `axes` ≠ `values` → rejet.
- Payload `show_comparison_table` > 5 lignes ou > 5 colonnes → rejet (hors-scope MVP).
- Payload `show_pie_chart` avec slices sommant à 0 → rejet.
- Code Mermaid avec lien externe (`click X href "..."`) → rejet (sandboxing).
- Score `show_match_card` hors [0,100] → rejet.
- Composant graphique chargé dans un message historique → re-render fidèle depuis `payload_json` persisté (F13).
- `alt_text` absent ou vide → rejet (accessibilité obligatoire).
- Bundle initial : chart.js / leaflet / mermaid ne doivent pas être inclus dans le bundle initial.

## Requirements *(mandatory)*

### Functional Requirements

**Tools backend (Pydantic + tool_registry)**

- **FR-001** : Le système DOIT déclarer 12 tools de visualisation (`show_kpi_card`, `show_progress_bar`, `show_radar_chart`, `show_bar_chart`, `show_line_chart`, `show_pie_chart`, `show_donut_chart`, `show_timeline`, `show_comparison_table`, `show_match_card`, `show_map`, `show_mermaid`) avec schémas Pydantic stricts (`extra="forbid"`, validators).
- **FR-002** : Chaque tool DOIT exposer (a) un nom, (b) un `description`, (c) un `use_when`, (d) un `dont_use_when`, (e) un schéma Pydantic, (f) au moins un `positive_example` — alignés sur le contrat F14/F15.
- **FR-003** : Tout champ texte exposé à l'utilisateur (label, title, alt_text, x_label, y_label, etc.) DOIT être validé anti-XSS (refus de `<` et `>`) côté backend (`no_html`).
- **FR-004** : Tout payload contenant au moins une `value` chiffrée DOIT exiger un champ `source_ids: list[int]` non vide. Exceptions : `show_mermaid` (texte libre validé), `show_timeline` (jalons), `show_map` (localisations).
- **FR-005** : Tout payload DOIT exiger un champ `alt_text: str` non vide (accessibilité, aria-label).
- **FR-006** : `show_mermaid` DOIT valider le `code` Mermaid avant envoi front (parse côté backend) ; si invalide, retourner une erreur de validation exploitable par la boucle retry F14.
- **FR-007** : `show_comparison_table` DOIT limiter à 5 colonnes et 5 lignes maximum.
- **FR-008** : `show_match_card` DOIT contraindre `score ∈ [0, 100]`, `link` à un chemin interne (commençant par `/`) pour éviter les redirections externes, et exiger `source_ids` non vide.
- **FR-008b** : `show_pie_chart` et `show_donut_chart` DOIVENT rejeter tout payload où une `slice.value` est négative (toutes `>= 0`).
- **FR-008c** : Toute `value` chiffrée dans un payload (KPI, radar, bar, line, comparison_table, progress_bar) DOIT être typée `Decimal` côté Pydantic, sérialisée en string en JSON pour préserver la précision (cohérent invariant Money typé Module 0).
- **FR-009** : `show_radar_chart` DOIT contraindre la longueur de chaque `series.values` à `len(axes)`.
- **FR-010** : Le système DOIT exposer une fonction d'enregistrement `register_visualisation_tools()` invocable au démarrage pour publier tous les tools P1 dans le `TOOL_REGISTRY` global (F14).

**Frontend (Vue 3 + Nuxt 4)**

- **FR-011** : Le système DOIT fournir un composant Vue par tool (`<ShowKpiCard>`, `<ShowProgressBar>`, `<ShowRadarChart>`, `<ShowBarChart>`, `<ShowLineChart>`, `<ShowPieChart>`, `<ShowDonutChart>`, `<ShowTimeline>`, `<ShowComparisonTable>`, `<ShowMatchCard>`, `<ShowMap>`, `<ShowMermaid>`).
- **FR-012** : Le composant orchestrateur `<ChatMessageRenderer>` (F13 FR-007) DOIT être étendu pour switcher selon `payload.type` parmi tous les tools de visualisation.
- **FR-013** : Chaque visualisation chiffrée DOIT rendre `<SourceCite :source-ids>` (F03) en coin de la carte.
- **FR-014** : Chaque conteneur graphique DOIT exposer `aria-label="{alt_text}"` et `role="img"` (accessibilité).
- **FR-015** : Tous les composants DOIVENT supporter le dark mode.
- **FR-016** : Chart.js, Leaflet et Mermaid DOIVENT être chargés dynamiquement (`import()` à la demande) pour ne pas plomber le bundle initial.
- **FR-017** : Le payload JSON DOIT être persisté dans `chat_message.payload_json` (F13) ; le rendu d'un message historique se fait à partir du payload stocké, sans recalcul serveur.
- **FR-018** : Hover et clic DOIVENT rester fonctionnels sur les charts dans l'historique (pas de gel).

**Réactivité (P2)**

- **FR-019** : `<ShowMatchCard>` et `<ShowKpiCard>` DOIVENT s'abonner à l'EventBus (F13) ; si `entity.updated_at > payload.rendered_at`, afficher un badge front "données obsolètes — recalculer ?". Aucun recalcul serveur n'est déclenché par cette comparaison.

**Anti-injection Mermaid**

- **FR-020** : La validation backend Mermaid DOIT rejeter (a) les directives `click ... href "..."` pointant vers une URL externe, (b) tout HTML inline `%%{init...}%%` avec scripts, (c) les diagrammes non whitelistés (autorisés : flowchart, sequenceDiagram, stateDiagram, gantt, classDiagram, erDiagram).

### Key Entities

- **Aucune nouvelle table**. Les payloads sont stockés tels quels dans `chat_message.payload_json` (F13). Les `source_ids` référencent la table `source` (F03).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Les 11 (P1) + 1 (P2 Mermaid) tools rendent correctement avec un payload de test sur une page de démonstration ou via tests unitaires.
- **SC-002** : Source cliquable visible et fonctionnelle sur 100 % des tools qui affichent des chiffres.
- **SC-003** : `show_mermaid` rejette un code Mermaid invalide avec retry LLM (boucle F14) — taux de retry réussi sous 3 tours ≥ 90 %.
- **SC-004** : Recharger un message ancien re-rend la visualisation à l'identique depuis le payload stocké.
- **SC-005** : Bundle initial Nuxt 4 < 500 KB ; chart.js, leaflet, mermaid sont absents du chunk initial.
- **SC-006** : Rendu d'un radar chart < 200 ms après réception du payload.
- **SC-007** : Couverture de tests ≥ 80 % sur le code F16 ajouté (backend tools).
- **SC-008** : Aucun payload chiffré sans `source_ids` ne passe la validation (test 100 % couvrant).
- **SC-009** : Aucun payload avec `<` ou `>` dans un champ texte ne passe la validation (test 100 % couvrant).

## Assumptions

- **A1** : F13 fournit `chat_message.payload_json` (JSONB) et `<ChatMessageRenderer>` extensible — réutilisé tel quel.
- **A2** : F14 fournit le `TOOL_REGISTRY` global et la boucle retry sur erreur de validation — réutilisée tel quel.
- **A3** : F15 fournit `app/orchestrator/tools/_common.py` (helpers `no_html`, `Option`) — réutilisés tel quel.
- **A4** : F03 fournit le composant `<SourceCite :source-ids>` et la table `source` — réutilisés tel quel.
- **A5** : Chart.js, Leaflet et Mermaid sont des dépendances frontend chargées en lazy ; backend ne dépend que d'une whitelist regex pour la validation Mermaid MVP.
- **A6** : Pas de nouvelle table en base ; le payload JSON sert de source de vérité pour le re-rendu historique.
- **A7** : `show_timeline`, `show_map` et `show_mermaid` ne portent pas obligatoirement de `source_ids`. Pour les autres tools, `source_ids` est obligatoire dès qu'une `value` chiffrée est affichée.
- **A8** : MVP livre P1 (US1–US10) en priorité. P2 (US11 show_map, US12 show_mermaid, US13 réactivité) est livré "best-effort" — peut être [DEFERRED] si budget temps dépassé.
- **A9** : La compatibilité dark mode et l'accessibilité (alt_text → aria-label) sont implémentées dès le MVP, pas reportées.
- **A10** : Le drill-down est livré uniquement sur `<ShowMatchCard>` (clic → page candidature). Pas de drill-down sur les autres tools (hors-scope MVP).
- **A11** : Validation backend Mermaid MVP : whitelist regex sur le mot-clé du diagramme + scan des directives `click...href` ; pas de parser AST complet.
