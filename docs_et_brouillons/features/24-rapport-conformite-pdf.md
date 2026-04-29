# F24 — Rapport de Conformité PDF (multi-référentiels + radar + lacunes + annexe sources)

**Phase** : 5 — Conformité ESG (Module 2)
**Modules brainstorm** : 2.4 (Rapport de Conformité Généré)
**Dépendances** : F23 (et F03 pour annexe sources)
**Estimation** : 1.5–2 jours

## Contexte et objectif

Permettre à la PME de **télécharger un rapport PDF professionnel** consolidant ses scores ESG sur les référentiels qu'elle choisit (ESG Mefali par défaut + 1 à N référentiels externes), avec radar, points forts, lacunes priorisées, méthodologie technique, et **annexe "Sources et références" auto-générée**.

Le rapport est un livrable concret, présentable à un fund officer, à un partenaire bancaire ou à un investisseur — il doit avoir une **qualité scientifique/auditable**.

## User Stories

### US1 — Sélection des référentiels à inclure (P1)
**En tant que** PME,
**je veux** choisir quels référentiels inclure dans mon rapport (checkbox liste — ESG Mefali coché par défaut),
**afin de** adapter le rapport à son destinataire (banque locale ≠ fonds international).

**Test indépendant** : ouvrir `/profil/rapport-esg`, sélectionner "ESG Mefali + GCF + IFC PS", cliquer Générer → PDF téléchargé.

### US2 — Visualisations graphiques par référentiel (P1)
**En tant que** PME,
**je veux** que le rapport contienne pour chaque référentiel sélectionné :
- entête (publisher, version, date),
- score global avec interprétation textuelle,
- radar chart par pilier ou par critère,
- barres de progression vers les seuils d'éligibilité,

**afin de** un contenu visuel professionnel.

### US3 — Identification des points forts (P1)
**En tant que** PME,
**je veux** une section "Points forts" listant les indicateurs où je suis au-dessus des seuils ou de la médiane sectorielle,
**afin de** valoriser mes acquis.

### US4 — Liste priorisée des lacunes (P1)
**En tant que** PME,
**je veux** une section "Lacunes à combler" qui :
- liste les indicateurs manquants ou en-dessous des seuils,
- indique pour chaque indicateur **quels référentiels** sont concernés,
- propose une action concrète (cohérent F31 plan d'action),
- priorise par **impact attendu sur le score global**.

**afin de** savoir où agir.

### US5 — Annexe technique (méthodologie) (P2)
**En tant qu'**auditeur,
**je veux** une annexe expliquant :
- comment les scores sont calculés (formules par référentiel),
- la table des indicateurs avec leur poids et seuil,
- la version exacte de chaque référentiel utilisé (cohérent F04 versioning).

**afin de** auditer la rigueur.

### US6 — Annexe "Sources et références" auto-générée (P1)
**En tant que** PME / auditeur,
**je veux** que toutes les sources mobilisées dans le rapport soient listées en annexe avec :
- URL,
- titre,
- publisher,
- version,
- date capture,
- statut de vérification.

**afin de** offrir une traçabilité complète (cohérent F03 US5).

### US7 — En-tête identité PME + horodatage (P1)
**En tant que** PME,
**je veux** que le PDF affiche en couverture mon nom d'entreprise, mon logo (si uploadé), la date de génération, et un identifiant unique,
**afin de** professionnalisme.

### US8 — Génération en français (P1)
**En tant que** PME francophone,
**je veux** que le rapport soit **par défaut en français**,
**afin de** correspondre à mes besoins.

EN possible post-MVP via paramètre `language` (cohérent `accepted_languages` Module 0.7).

### US9 — Téléchargement direct + lien archivé (P2)
**En tant que** PME,
**je veux** que le PDF généré soit téléchargeable immédiatement et accessible plus tard depuis `/profil/rapports` (historique),
**afin de** retrouver mes anciens rapports.

## Exigences fonctionnelles

- **FR-001** : Service backend `RapportEsgService.generate(entity_id, referentiels: list[str], lang='fr') -> bytes (PDF)`.
- **FR-002** : Stack PDF : `weasyprint` (HTML→PDF) ou `reportlab` (programmatique). Recommandation MVP : **weasyprint** (CSS print-friendly, plus simple à maintenir, support multi-pages, polices custom). Templates Jinja2 côté backend.
- **FR-003** : Templates Jinja2 :
  - `template/rapport_esg/cover.html` (couverture),
  - `template/rapport_esg/section_referentiel.html` (1 section par référentiel),
  - `template/rapport_esg/lacunes.html`,
  - `template/rapport_esg/methodologie.html`,
  - `template/rapport_esg/sources.html`.
- **FR-004** : Graphiques rendus en SVG via `chart.js` server-side (avec `node` ou via une lib Python comme `matplotlib`/`plotly`). Recommandation MVP : `matplotlib` (déjà dans l'écosystème Python, statique, simple).
- **FR-005** : Endpoint `POST /me/rapports/esg` body `{entity_type, entity_id, referentiels:[code], language}` → renvoie `{rapport_id, download_url}`. Le PDF est généré synchrone < 10s pour un rapport standard.
- **FR-006** : Table `rapport_genere` : `id, account_id, entity_type, entity_id, referentiels TEXT[], language, file_path, generated_at, generated_by, score_snapshot_json (cohérent F04 versioning : on stocke les scores au moment de la génération)`.
- **FR-007** : Endpoint `GET /me/rapports` (historique) + `GET /me/rapports/{id}/download`.
- **FR-008** : Helper `build_sources_appendix(source_ids)` (déjà livré F03 FR-008) consommé pour l'annexe sources.
- **FR-009** : Page Vue `/profil/rapports` (historique des rapports générés).
- **FR-010** : Bouton "Générer un rapport" sur `/profil/scoring` qui ouvre le wizard de sélection référentiels.

## Exigences non-fonctionnelles

- **NFR-001** : Génération d'un rapport ESG Mefali + 3 référentiels externes en < 10s.
- **NFR-002** : Le PDF est de qualité print (300 DPI minimum, polices intégrées, pagination correcte, en-tête/pied de page).
- **NFR-003** : Tous les chiffres ont leur source en note de bas de page ou en lien (compatible PDF avec liens cliquables).
- **NFR-004** : Le PDF reste lisible en noir et blanc (couleurs sémantiques mais aussi labels lisibles).

## Entités clés

- **RapportGenere** (FR-006).

## Success Criteria

- **SC-001** : PDF de 10–20 pages généré pour une PME avec 4 référentiels en < 10s.
- **SC-002** : Annexe sources contient toutes les sources mobilisées, dédoublonnées.
- **SC-003** : Visualisations radar/barres lisibles en print.
- **SC-004** : Versioning : un rapport généré aujourd'hui reste reproductible plus tard car scores snapshotés.
- **SC-005** : Téléchargement immédiat + accessible 30 jours plus tard depuis l'historique.

## Hors-scope MVP

- Génération en EN (post-MVP, mais structure prête).
- Templating personnalisable par PME (logo, couleurs).
- Signature numérique du PDF (post-MVP — F30 pour les attestations).
- Export PowerPoint / Word.
- Diff entre 2 rapports historiques.
- Génération automatique récurrente (mensuel, trimestriel).

## Risques et points de vigilance

- **Charts server-side** : matplotlib / plotly statiques sont plus simples que rendre chart.js côté serveur. Mais cohérence visuelle avec les charts inline F16 importante. Acceptable de divergence en MVP.
- **Polices et accents** : weasyprint + Noto Sans + Inter pour le français. S'assurer que les caractères spéciaux (é, ç, à) s'affichent partout.
- **Taille du PDF** : 4 référentiels × 5 pages = 20 pages, ~2-5 MB. OK.
- **Performance** : 30 PME générant en simultané = 30 weasyprint workers. En MVP synchrone, ça peut pénaliser. Acceptable, post-MVP queue Celery.
- **Liens hypertexte** : les sources doivent être cliquables dans le PDF (weasyprint le supporte).
