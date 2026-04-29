# F16 — Tools de Visualisation Inline (show_kpi/radar/bar/line/pie/timeline/comparison/match/map/mermaid)

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 1.1.2 (Réponses Graphiques + Textuelles)
**Dépendances** : F13, F14
**Estimation** : 2.5 jours

## Contexte et objectif

Un message du LLM ne se limite pas à du texte. Quand une visualisation clarifie le propos (chiffre clé, évolution, comparaison, répartition, processus), le LLM invoque un **tool de visualisation** rendu inline dans le fil de conversation (au sein de la bulle assistant — distinct du bottom sheet de réponse F15 qui, lui, est en bas).

**Approche hybride** :
- Tools **typés** pour les visualisations récurrentes (scores, KPI, évolutions, comparaisons) → payload JSON validé Pydantic, composant Vue stylé.
- `show_mermaid` en **fallback ad-hoc** pour les diagrammes libres (processus, décision, organigramme) → code Mermaid validé backend (parse avant envoi front).

> **Sourçage** : tout chiffre affiché dans une visualisation a une source cliquable (F03 `<SourceCite>`).
> **Accessibilité** : chaque visualisation est accompagnée d'un alt-text textuel généré par le LLM.
> **Réactivité** : les visualisations dans l'historique restent interactives et se mettent à jour si la donnée sous-jacente évolue.

## User Stories

### US1 — show_kpi_card : Chiffre clé + delta (P1)
**En tant que** PME,
**je veux** voir un chiffre clé mis en valeur (ex : "45 tCO2e ↓12% vs 2024") avec son contexte et sa source cliquable,
**afin de** capter rapidement l'info importante.

**Test indépendant** : invoquer `show_kpi_card` avec payload valide → le composant rend la carte avec valeur, unité, delta, label, picto Source.

### US2 — show_progress_bar : Avancement vers un objectif (P1)
**En tant que** PME,
**je veux** voir une barre de progression "Score ESG actuel 62/100 — seuil GCF 75" avec couleur (rouge < seuil, vert ≥),
**afin de** comprendre l'écart au seuil.

### US3 — show_radar_chart : Multi-piliers / multi-référentiels (P1)
**En tant que** PME,
**je veux** voir mes scores E/S/G ou ma comparaison multi-référentiels (ESG Mefali / GCF / IFC / BOAD) en radar,
**afin de** visualiser mon profil global.

Lib : chart.js (déjà installé F01).

### US4 — show_bar_chart : Benchmarking sectoriel, ventilation (P1)
**En tant que** PME,
**je veux** voir un graph en barres pour comparer mes scores par référentiel ou ma position dans mon secteur,
**afin de** me situer.

### US5 — show_line_chart : Évolution dans le temps (P1)
**En tant que** PME,
**je veux** voir l'évolution de mon score ESG ou de mon empreinte carbone sur 12 mois,
**afin de** visualiser la tendance.

### US6 — show_pie_chart / show_donut_chart : Répartition (P1)
**En tant que** PME,
**je veux** voir la répartition de mes émissions par source (énergie 60%, transport 25%, déchets 15%) en camembert,
**afin de** prioriser les actions.

### US7 — show_timeline : Étapes / roadmap (P1)
**En tant que** PME,
**je veux** voir les étapes d'une candidature, la roadmap d'un projet, les échéances d'une offre, en timeline horizontale ou verticale,
**afin de** anticiper les jalons.

### US8 — show_comparison_table : Offres A vs B vs C (P1)
**En tant que** PME,
**je veux** voir un tableau aligné comparant 2-5 Offres (ou intermédiaires) sur leurs critères, frais, délais, taux de succès,
**afin de** choisir.

### US9 — show_match_card : Carte "Projet ↔ Offre, compatibilité X%" (P1)
**En tant que** PME,
**je veux** voir une carte avec score de compatibilité, listing des critères couverts/manquants, lien vers la page candidature,
**afin de** décider de candidater ou non.

### US10 — show_map : Localisation (P2)
**En tant que** PME,
**je veux** voir une carte (Leaflet) avec mon entreprise, mes projets, leurs zones d'impact, les bureaux des intermédiaires,
**afin de** visualiser géographiquement.

Lib : Leaflet (déjà installé F01).

### US11 — show_mermaid : Diagramme libre fallback (P2)
**En tant que** PME,
**je veux** que pour des processus ou diagrammes ad-hoc non couverts par le catalogue typé, le LLM produise du Mermaid validé,
**afin de** voir un diagramme cohérent.

**Validation backend** : parser Mermaid avant envoi front ; si invalide, fallback texte.

### US12 — Anatomie d'un message hybride (P1)
**En tant que** PME,
**je veux** que le LLM puisse chaîner dans **un même tour** : texte d'intro + visualisation + texte d'analyse + question QCU pour la suite,
**afin de** vivre une conversation riche.

### US13 — Réactivité des visualisations historiques (P2)
**En tant que** PME,
**je veux** que si je modifie un projet, les visualisations affichées dans des messages anciens basés sur ce projet se mettent à jour si je clique dessus, ou affichent un badge "données obsolètes",
**afin de** ne pas être trompée.

## Exigences fonctionnelles

- **FR-001** : 11 tools déclarés (`show_kpi_card`, `show_progress_bar`, `show_radar_chart`, `show_bar_chart`, `show_line_chart`, `show_pie_chart`, `show_donut_chart`, `show_timeline`, `show_comparison_table`, `show_match_card`, `show_map`, `show_mermaid`) avec schémas Pydantic stricts.
- **FR-002** : Schémas types (extraits) :
  - `show_kpi_card`: `{label:str, value:Decimal, unit:str, delta?:{value, period}, source_ids:[int], alt_text:str}`.
  - `show_radar_chart`: `{title:str, axes:[str], series:[{name, values:[Decimal]}], source_ids, alt_text}`.
  - `show_comparison_table`: `{title:str, columns:[str], rows:[{label, values:[]}], source_ids, alt_text}`.
  - `show_match_card`: `{projet_id, offre_id, score:int(0-100), criteres_couverts, criteres_manquants, link, source_ids, alt_text}`.
  - `show_mermaid`: `{code:str (parsed côté backend), alt_text}`.
- **FR-003** : Composants Vue par tool (`<ShowKpiCard>`, `<ShowRadarChart>`, etc.). Stylés Tailwind v4. Charts via chart.js avec wrapper Vue. Mermaid via lib mermaid.
- **FR-004** : Composant orchestrateur `<ChatMessageRenderer>` (déjà initié en F13 FR-007) étendu pour switcher sur `payload.type` parmi tous les tools de visualisation.
- **FR-005** : Validation backend Mermaid : `mermaid.parse(code)` (en Node side via service ou en Python via wrapper). Si erreur, retourner `validation_error` au LLM (retry F14).
- **FR-006** : Chaque visualisation reçoit `source_ids` ; le composant rend `<SourceCite :source-ids>` (de F03) en coin.
- **FR-007** : `alt_text` rendu en `aria-label` du conteneur graphique pour l'accessibilité. Le LLM doit le générer (instruction system prompt F14).
- **FR-008** : Réactivité : `<ShowMatchCard>` et `<ShowKpiCard>` souscrivent à l'EventBus (F13) pour les entités qu'elles affichent. Si l'entité est mise à jour, badge "données obsolètes — recalculer ?" + bouton.
- **FR-009** : Le payload JSON est stocké dans `chat_message.payload_json` (F13). Le re-rendu fidèle des messages anciens est garanti par persistance du payload (pas seulement de l'image rendue).
- **FR-010** : Hover/clic restent fonctionnels sur les charts dans l'historique (pas de gel).

## Exigences non-fonctionnelles

- **NFR-001** : Rendu d'un radar chart < 200ms.
- **NFR-002** : Bundle frontend : chart.js + leaflet + mermaid sont lazy-chargés (import dynamique) pour ne pas plomber l'initial load.
- **NFR-003** : Tous les composants graphiques doivent supporter le dark mode (cohérent design system).
- **NFR-004** : Sanitize tout texte rendu dans les visualisations (XSS).

## Entités clés

- Aucune nouvelle table — payload dans `chat_message.payload_json`.

## Success Criteria

- **SC-001** : Les 11 tools rendent correctement avec un payload de test sur Storybook ou page de démo.
- **SC-002** : Source cliquable visible et fonctionnelle sur tous les tools qui affichent des chiffres.
- **SC-003** : `show_mermaid` rejette un code Mermaid invalide avec retry LLM (F14 boucle).
- **SC-004** : Recharger un message ancien re-rend la visualisation à l'identique depuis le payload stocké.
- **SC-005** : Bundle initial Nuxt 4 < 500 KB (chart.js, leaflet, mermaid lazy-loaded).

## Hors-scope MVP

- Visualisations 3D, animations complexes (post-MVP).
- Drill-down (clic sur une barre → détails) : seulement sur `show_match_card` en MVP. Les autres : non en MVP.
- Export PNG/SVG des visualisations directement depuis le chat (post-MVP, mais déjà couvert pour les rapports PDF F24/F30).
- Tableau comparatif > 5 lignes/colonnes (post-MVP, on limite la lisibilité).

## Risques et points de vigilance

- **Hallucination de payload** : le LLM peut produire un payload "plausible" mais avec des chiffres inventés. La règle F03 (sourçage) le bloque normalement, mais double-check : tout `value` chiffré doit avoir une source. Le validator F14 + F03 doit imposer cette contrainte.
- **Cohérence des unités** : un radar mêlant scores ESG (0-100) et tCO2e brouille tout. Le LLM doit normaliser. À tester en eval F35.
- **Mermaid avec injection** : un code Mermaid peut contenir des éléments interactifs ou des liens externes. Sandboxer le rendu.
- **Bundle size** : leaflet + mermaid + chart.js sont lourds. Lazy-load impératif.
- **Accessibilité** : un graphique sans alt-text est inutile pour un lecteur d'écran. Le LLM doit toujours fournir alt_text — le validator F14 doit imposer ce champ requis.
