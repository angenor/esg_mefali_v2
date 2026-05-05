# Feature Specification: Visualization Library (UI de F16)

**Feature Branch**: `040-viz-library`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: `@docs_et_brouillons/features/40-visualization-library.md`

## Vue d'ensemble

Concrétise les principes constitutionnels P10 (bulles LLM display-only) et P1 (sourcing systématique) en fournissant la bibliothèque de composants de visualisation **non-interactifs** que l'assistant LLM peut afficher dans le fil de conversation : texte, KPI, charts (line/area/bar/radar/gauge/pie/donut), diagrammes Mermaid, tables denses, mini-cartes Leaflet. Chaque visualisation expose un **pin de source** cliquable (P1) qui ouvre une popover contenant le titre, l'URL et le pilier de la source vérifiée.

Cette feature est l'UI miroir des outils backend de viz (F16) ; elle ne fait **aucun fetch de données** par elle-même — elle reçoit en entrée des structures déjà calculées par le backend ou par le runtime LLM.

## Clarifications

### Session 2026-05-03

- Q: Niveau d'accessibilité visé pour la bibliothèque de visualisations ? → A: WCAG 2.1 niveau AA (navigation clavier complète des `<VizSourcePin>`, `aria-label` sur charts, fallback texte / description longue par visualisation, contraste 4.5:1).
- Q: Stratégie de résolution / cache des sources côté frontend ? → A: Store Pinia `useSourcesStore()` avec cache mémoire TTL ~5 min, dédoublonnage des requêtes en vol, fetch à la demande à l'ouverture de la popover.
- Q: Format du champ `pillar` dans `SourceRef` ? → A: Enum fermé `{E, S, G, financial, regulatory, methodology}` ; chaque valeur a un badge couleur déterministe.
- Q: Comportement de `<VizDataTable>` au-delà du seuil 100 lignes ? → A: Virtualisation activée par défaut au-delà de 100 lignes ; pagination optionnelle activable via prop `paginate?: { pageSize: number }` quand le contexte le demande (rapports figés, captures).
- Q: Export CSV depuis `<VizDataTable>` : in ou out du MVP ? → A: Hors-scope MVP — reporté à F51 (rapports / exports) qui définira un format CSV unifié pour tableaux et rapports.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — KPI Card avec source pin (Priority: P1)

Le dirigeant PME consulte son score ESG. L'assistant affiche un KPI "Score E : 72/100" avec une variation par rapport au mois précédent et un pin source. Le dirigeant clique sur le pin et voit immédiatement la source qui a permis ce calcul.

**Why this priority**: La carte KPI est la primitive la plus utilisée dans les réponses LLM (scoring, indicateurs, montants). Sans elle, l'assistant ne peut pas restituer une donnée chiffrée de manière conforme à P1 (sourcing).

**Independent Test**: Rendre `<VizKPICard>` avec mock data {label, value, unit, delta, source_id} sur la route `/dev/viz-showcase` ; cliquer le pin doit ouvrir la popover avec la source réelle remontée par l'API.

**Acceptance Scenarios**:

1. **Given** un KPI {label: "Score E", value: 72, unit: "/100", delta: +5, source_id: "src_abc"}, **When** la carte est rendue, **Then** la valeur s'affiche en `tabular-nums`, le delta apparaît en vert avec une flèche montante, et le pin source est visible en exposant.
2. **Given** un KPI sans `source_id`, **When** la carte est rendue, **Then** aucun pin de source n'est affiché et la carte reste lisible.
3. **Given** un KPI cliqué sur son pin source, **When** la popover s'ouvre, **Then** elle contient `{title, url, pillar, valid_from}` issus de la base et un lien externe sécurisé vers l'URL.

---

### User Story 2 — Charts standards (line, bar, radar, pie/donut) (Priority: P1)

L'assistant doit pouvoir afficher l'évolution d'un indicateur (courbe), une décomposition (barres ou camembert), un profil ESG multi-axes (radar). Chaque chart accepte un `source_id` optionnel et un état de chargement / vide.

**Why this priority**: Les charts sont essentiels pour matérialiser les insights (tendance carbone, décomposition Scope 1/2/3, radar E/S/G). Sans eux, les réponses LLM resteraient textuelles et peu lisibles.

**Independent Test**: La route `/dev/viz-showcase` doit rendre chaque type avec mock data sans erreur, et permettre de basculer manuellement entre `loading`, `empty` et `data`.

**Acceptance Scenarios**:

1. **Given** une série temporelle de 12 mois, **When** `<VizLineChart>` est rendu, **Then** une courbe lissée avec gradient subtil s'affiche, le hover déclenche un tooltip cohérent avec le design system, et la légende reste sobre.
2. **Given** un dataset à 6 axes E/S/G, **When** `<VizRadarChart>` est rendu, **Then** un radar rempli (filled subtle) s'affiche avec maximum 6 points.
3. **Given** un chart sans données, **When** la prop `empty` est `true`, **Then** un EmptyState avec illustration sobre et message "Aucune donnée disponible — lancez un calcul ESG" s'affiche à la place du chart.
4. **Given** un chart en chargement, **When** la prop `loading` est `true`, **Then** un skeleton chart shimmer s'affiche ; le chart vide ne doit jamais être visible avant que les données arrivent.

---

### User Story 3 — Mermaid renderer avec fallback (Priority: P1)

L'assistant peut produire un diagramme Mermaid (flowchart, séquence, gantt) pour expliquer un processus ESG. Le rendu doit être robuste : un diagramme invalide ne doit pas crasher la conversation.

**Why this priority**: Mermaid est utilisé pour rendre lisibles les flux conformité, les arborescences de critères, les séquences d'orchestration. Sa robustesse conditionne la confiance dans le système.

**Independent Test**: Sur `/dev/viz-showcase`, fournir un script Mermaid valide puis un script invalide ; vérifier l'absence de crash et la présence d'un fallback texte lisible.

**Acceptance Scenarios**:

1. **Given** un script Mermaid valide, **When** `<VizMermaidRenderer>` est rendu, **Then** le SVG produit est sanitisé puis injecté dans le DOM sans script exécutable.
2. **Given** un script Mermaid invalide, **When** le parsing échoue, **Then** un fallback texte affiche le code source brut sans interrompre le rendu de la bulle parente.
3. **Given** un environnement SSR Nuxt, **When** la page se charge, **Then** Mermaid n'est pas hydraté côté serveur et reste encapsulé dans `<ClientOnly>`.

---

### User Story 4 — DataTable performante avec colonnes typées (Priority: P1)

L'assistant peut présenter une liste de transactions, indicateurs ou résultats de matching. Le tableau accepte des colonnes typées (texte, number, date, badge, money), permet le tri, la recherche et la pagination, et virtualise au-delà de 100 lignes.

**Why this priority**: Sans table dense, les réponses contenant plus de 5 lignes deviennent illisibles. La virtualisation est un prérequis pour les listes longues (offres, candidatures, indicateurs).

**Independent Test**: Sur `/dev/viz-showcase`, fournir un dataset de 1000 lignes ; vérifier l'absence de lag au scroll et le bon fonctionnement du tri / recherche.

**Acceptance Scenarios**:

1. **Given** un dataset de 1000 lignes typées, **When** `<VizDataTable>` est rendu, **Then** seules les lignes visibles sont peintes (virtualisation), le scroll reste fluide.
2. **Given** une colonne `type: "money"` recevant `{amount, currency}`, **When** la cellule est rendue, **Then** le montant est formaté avec la devise et le séparateur de milliers, sans jamais utiliser de `float`.
3. **Given** un dataset vide, **When** la table est rendue, **Then** un EmptyState explicatif est affiché.
4. **Given** un dataset filtré par recherche, **When** l'utilisateur saisit un terme, **Then** seules les lignes correspondant à au moins une colonne textuelle sont conservées.

---

### User Story 5 — Source pin universel (Priority: P1)

Le composant `<VizSourcePin>` est utilisé par tous les autres composants (KPI, charts, tables, mermaid, cartes). Cliqué, il ouvre une popover qui montre le titre, l'URL, le pilier et la date de validité de la source. Les sources révoquées affichent une icône d'avertissement.

**Why this priority**: P1 (sourcing) est non-négociable. Aucune valeur affichée par l'assistant ne doit être lue sans pouvoir remonter à sa source vérifiée.

**Independent Test**: Réutiliser `<VizSourcePin source_id="src_abc">` dans un KPI, un chart et une cellule de table ; vérifier la cohérence visuelle et le comportement de la popover.

**Acceptance Scenarios**:

1. **Given** un `source_id` valide, **When** le pin est cliqué, **Then** la popover affiche `{title, url, pillar, valid_from}` et un lien externe.
2. **Given** une source au statut `revoked`, **When** le pin est rendu, **Then** une icône warning remplace l'icône standard et la popover indique le motif de révocation.
3. **Given** un `source_id` introuvable, **When** le pin est rendu, **Then** il n'apparaît pas (fail-silent) plutôt que d'afficher un état d'erreur dans la conversation.

---

### User Story 6 — Gauge chart pour score (Priority: P2)

L'assistant peut afficher un gauge chart 0-100 (ex. credit_score) avec un arc de 270°, une valeur centrale et des zones colorées (rouge / orange / vert).

**Why this priority**: Le gauge est utilisé spécifiquement pour les scores synthétiques (P2 car moins fréquent que KPI/line/bar/radar).

**Independent Test**: Sur `/dev/viz-showcase`, rendre `<VizGaugeChart :value="68">` ; vérifier la valeur centrale, l'arc 270° et la couleur de la zone correspondante.

**Acceptance Scenarios**:

1. **Given** une valeur 68 sur l'échelle 0-100, **When** le gauge est rendu, **Then** l'aiguille pointe entre les deux tiers de l'arc et la zone orange est mise en évidence.
2. **Given** `prefers-reduced-motion`, **When** le gauge est rendu, **Then** l'animation d'entrée est désactivée.

---

### User Story 7 — Mini-carte Leaflet avec clusters (Priority: P2)

L'assistant peut afficher une mini-carte présentant les pins d'intermédiaires, fonds ou projets avec clustering automatique au-delà de 10 marqueurs.

**Why this priority**: Utile pour matching géographique (F25) mais pas indispensable au MVP de viz.

**Independent Test**: Sur `/dev/viz-showcase`, rendre `<VizLeafletMap :pins="50pins">` ; vérifier le clustering, le zoom max 5 et l'attribution OSM.

**Acceptance Scenarios**:

1. **Given** 50 pins répartis sur l'Afrique de l'Ouest, **When** la carte est rendue, **Then** les pins sont automatiquement clusterisés et l'attribution OSM est visible.
2. **Given** un zoom utilisateur supérieur à 5, **When** l'utilisateur zoome, **Then** le zoom est plafonné à 5.

---

### Edge Cases

- **Source révoquée** : icône warning explicite, cohérent avec F03.
- **Source absente** : pas d'erreur visible, le pin est simplement omis.
- **Mermaid invalide** : fallback texte, jamais de crash.
- **Dataset chart vide** : EmptyState dédié, jamais un chart blanc.
- **Dataset > 100 lignes** : virtualisation activée automatiquement.
- **`prefers-reduced-motion`** : toutes les animations chart sont désactivées.
- **Daltonisme** : aucune information critique n'est portée par la couleur seule (toujours doublée par icône, label ou motif).
- **Caractères non-latins** dans les titres / labels : préservation des accents et caractères africains.
- **SSR** : Mermaid, Leaflet et chart.js sont systématiquement encapsulés dans `<ClientOnly>` ; aucun rendu serveur.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT fournir des composants `<Viz*>` regroupés sous `frontend/app/components/viz/` couvrant : KPICard, LineChart, AreaChart, BarChart, StackedBarChart, RadarChart, GaugeChart, PieChart, DonutChart, MermaidRenderer, DataTable, LeafletMap, SourcePin, EmptyState, LoadingState.
- **FR-002** : Chaque composant chart DOIT s'appuyer sur une configuration partagée (couleurs design system F36, fonts Inter, tooltip cohérent) exposée par un composable `useChartTheme()`.
- **FR-003** : Les composants chart, mermaid et carte DOIVENT être chargés en `lazy` (dynamic import) afin de ne pas figurer dans le bundle initial.
- **FR-004** : Tous les composants chart DOIVENT accepter les props `:title, :caption, :source_id?, :size, :loading, :empty`.
- **FR-005** : `<VizDataTable>` DOIT accepter `:rows` et `:columns: [{key, label, type, format?}]` ; il NE DOIT PAS effectuer de fetch interne — la donnée est fournie par l'appelant.
- **FR-006** : Les types de colonnes supportés DOIVENT inclure : `text`, `number`, `date`, `badge`, `money` (`{amount, currency}` conforme à P5).
- **FR-007** : `<VizMermaidRenderer>` DOIT sanitiser le SVG produit (DOMPurify) avant injection pour prévenir tout XSS.
- **FR-008** : `<VizSourcePin>` DOIT être réutilisé par tous les composants exposant `source_id`, et DOIT ouvrir une popover affichant `{title, url, pillar, valid_from}` résolus via un store partagé `useSourcesStore()` (Pinia) qui maintient un cache mémoire TTL ~5 min, dédoublonne les requêtes en vol et fetch à la demande lors de la première ouverture de popover pour un `source_id` donné.
- **FR-009** : Les sources avec `status = 'revoked'` DOIVENT afficher une icône d'avertissement distincte.
- **FR-009b** : Le champ `pillar` d'un `SourceRef` DOIT appartenir à l'enum fermé `{'E', 'S', 'G', 'financial', 'regulatory', 'methodology'}` ; toute valeur hors enum DOIT être traitée comme une erreur d'intégration côté front (log + fallback neutre, pas de crash).
- **FR-010** : Une route de démonstration `/dev/viz-showcase` DOIT rendre chaque type de composant avec mock data sans erreur, accessible uniquement en environnement de développement.
- **FR-011** : `<VizDataTable>` DOIT activer la virtualisation par défaut dès que le dataset dépasse 100 lignes et supporter le tri ainsi que la recherche full-text. La pagination DOIT être désactivée par défaut (scroll virtualisé continu) et activable au cas par cas via une prop `paginate?: { pageSize: number }` qui bascule la table en mode paginé classique (et désactive alors la virtualisation au sein d'une page).
- **FR-012** : Tous les composants animés DOIVENT respecter `prefers-reduced-motion` et désactiver les animations le cas échéant.
- **FR-013** : Mermaid, Leaflet et chart.js DOIVENT être encapsulés dans `<ClientOnly>` pour éviter toute hydratation SSR.
- **FR-014** : Aucun composant `<Viz*>` NE DOIT contenir d'élément interactif modifiant l'état (input, bouton submit, slider) — l'interaction utilisateur passe par les bottom sheets (P10).
- **FR-015** : Toutes les valeurs monétaires affichées DOIVENT respecter le format `{amount: Decimal, currency: ISO 4217}` ; aucun `float` ne doit transiter (P5).
- **FR-016** : L'export CSV depuis `<VizDataTable>` est **hors-scope MVP** ; il sera traité par F51 (rapports / exports) qui définira un format CSV unifié pour tableaux et rapports.
- **FR-017** : Les états `loading` et `empty` DOIVENT systématiquement remplacer le rendu du composant — un composant ne DOIT jamais s'afficher avec des données partielles ou en cours de chargement.
- **FR-018** : Tous les libellés, messages d'état et textes EmptyState DOIVENT être en français (par défaut) ; l'anglais reste réservé aux dossiers de candidature autorisant `'en'`.
- **FR-019** : La bibliothèque DOIT respecter **WCAG 2.1 niveau AA** : `<VizSourcePin>` et tout élément focusable DOIVENT être atteignables au clavier (Tab) avec indicateur de focus visible ; chaque chart DOIT exposer un `aria-label` synthétique et une description longue alternative (texte) reprenant le titre, la caption et les valeurs clés ; le contraste texte/fond DOIT être ≥ 4.5:1 sur l'ensemble des composants.

### Key Entities

- **VizConfig** : représente la configuration partagée d'un chart (palette couleurs depuis F36, fonts, tooltip, animations). Exposé par `useChartTheme()`.
- **SourcesStore** : store Pinia `useSourcesStore()` détenant un cache mémoire `Map<source_id, {data: SourceRef, fetchedAt}>` avec TTL ~5 min, et un index des requêtes en vol pour dédoublonner les `resolve(source_id)` concurrents.
- **ChartProps (commun)** : `{title?, caption?, source_id?, size: 'sm'|'md'|'lg', loading?, empty?}`.
- **ColumnDef** : `{key: string, label: string, type: 'text'|'number'|'date'|'badge'|'money', format?: string}` — décrit une colonne de `<VizDataTable>`.
- **MoneyValue** : `{amount: Decimal, currency: ISO 4217}` — type unique pour toute valeur monétaire (P5).
- **SourceRef** : `{source_id, title, url, pillar, valid_from, status}` — donnée résolue par l'API et affichée dans la popover. `pillar` est un enum fermé `'E' | 'S' | 'G' | 'financial' | 'regulatory' | 'methodology'` ; chaque valeur dispose d'un badge couleur déterministe issu des tokens F36. `status` est un enum fermé `'verified' | 'revoked'`.
- **MermaidPayload** : `{script: string}` — entrée brute pour le renderer ; sortie SVG sanitisée.
- **MapPin** : `{lat, lng, label?, type?}` — point d'une `<VizLeafletMap>`, jamais d'identifiant utilisateur sensible.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : La route `/dev/viz-showcase` rend chaque type de composant (KPI, line, area, bar, stacked, radar, gauge, pie, donut, mermaid, table, map, source pin, empty state, loading state) avec mock data sans erreur console.
- **SC-002** : Cliquer un `<VizSourcePin>` ouvre la popover avec les données réelles (`title, url, pillar, valid_from`) provenant de la base, en moins de 300 ms après le clic dans 95 % des cas.
- **SC-003** : `<VizDataTable>` rend 1000 lignes typées et conserve un scroll fluide (jamais plus d'une frame > 16 ms sur un appareil de référence).
- **SC-004** : Un script Mermaid invalide produit le fallback texte sans crasher la bulle parente ni l'application.
- **SC-005** : `<VizLeafletMap>` rend 50 pins clusterisés sans dépasser 1 s de Largest Contentful Paint sur un appareil de référence.
- **SC-006** : Un chart avec 100 points obtient un Largest Contentful Paint inférieur à 1 s.
- **SC-007** : Aucun chart, mermaid ou carte n'apparaît dans le bundle initial JavaScript ; ils sont tous chargés en chunks asynchrones.
- **SC-008** : Aucun composant `<Viz*>` ne contient d'élément interactif modifiant l'état (validation par audit du code et test E2E vérifiant l'absence d'`<input>`, `<button type="submit">` ou autre primitive d'entrée à l'intérieur d'une bulle LLM).
- **SC-009** : 100 % des valeurs monétaires affichées sont rendues à partir d'un type `{amount, currency}` (audit statique du code).
- **SC-010** : L'expérience reste lisible sous simulation de daltonisme (Color Oracle) — aucune information critique portée par la couleur seule.
- **SC-011** : Un audit automatisé (axe-core ou équivalent) sur `/dev/viz-showcase` ne remonte aucune violation WCAG 2.1 AA bloquante ; tous les `<VizSourcePin>` sont atteignables au clavier et chaque chart expose une description textuelle alternative.

## Assumptions

- La librairie chart.js est verrouillée à la version v4 dans `frontend/package.json` pour éviter toute rupture de compatibilité.
- Le design system F36 fournit déjà les tokens de couleurs, fonts et espacements consommés par `useChartTheme()`.
- Les sources sont déjà persistées avec un statut (`verified`, `revoked`) côté backend (F03) ; cette feature n'introduit pas de nouvelle table.
- L'API expose déjà un endpoint permettant de résoudre `source_id → {title, url, pillar, valid_from, status}` ; sinon il sera ajouté dans le cadre de F03 avant ou pendant cette feature.
- Mermaid v10+ est utilisable côté client uniquement ; aucun rendu SSR n'est attendu.
- DOMPurify est disponible (déjà utilisé pour la sanitization existante du frontend) et sert à nettoyer le SVG Mermaid.
- `vue-virtual-scroller` est utilisé pour la virtualisation de `<VizDataTable>` au-delà du seuil 100 lignes.
- Cette feature ne couvre **pas** les charts custom D3 (heatmap, sankey, treemap), l'export PNG/SVG, ni les animations avancées de morphing — tout cela est hors-scope MVP.
- Les bulles LLM utilisant ces composants sont strictement display-only (P10) ; toute interaction utilisateur passe par le bottom sheet engine (F39).
- Les types de colonnes supportés en MVP sont limités à `text, number, date, badge, money` ; les types complexes (image, lien custom, formule) sont post-MVP.
- L'export CSV est explicitement **hors-scope MVP** et sera adressé par F51 (rapports / exports).
