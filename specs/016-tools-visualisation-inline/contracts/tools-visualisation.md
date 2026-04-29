# Tool Contracts — F16 Tools de Visualisation Inline

Synthèse des contrats LLM pour les 12 tools (10 P1 + 2 P2). Chaque tool est enregistré dans le `TOOL_REGISTRY` global F14 via `register_visualisation_tools()`.

> Schémas Pydantic complets dans `../data-model.md`. Ce document fournit pour chaque tool : `name`, `description`, `use_when`, `dont_use_when`, et un `positive_example` JSON synthétique.

## P1

### show_kpi_card

- **Description** : Affiche un chiffre clé mis en valeur avec son contexte, un delta éventuel et une source cliquable.
- **Use when** : un chiffre unique mérite d'être mis en exergue (score ESG global, empreinte carbone, montant levé).
- **Don't use when** : plusieurs valeurs liées à comparer → préférer `show_bar_chart` ou `show_radar_chart`.
- **Example** :
```json
{
  "label": "Empreinte carbone 2025",
  "value": "45.00",
  "unit": "tCO2e",
  "delta": {"value": "-12.0", "period": "vs 2024"},
  "source_ids": [42],
  "alt_text": "Empreinte carbone 2025 : 45 tCO2e, en baisse de 12% par rapport à 2024."
}
```

### show_progress_bar

- **Description** : Barre de progression vers une cible avec couleur conditionnelle.
- **Use when** : avancement vs un seuil (score ESG vs seuil GCF, % complétion d'un dossier).
- **Don't use when** : pas de notion de cible → `show_kpi_card`.
- **Example** :
```json
{
  "label": "Score ESG actuel vs seuil GCF",
  "current": "62",
  "target": "75",
  "unit": "/100",
  "source_ids": [10, 11],
  "alt_text": "Score ESG actuel 62/100, seuil GCF 75."
}
```

### show_radar_chart

- **Description** : Radar multi-axes pour visualiser un profil sur plusieurs dimensions.
- **Use when** : scores E/S/G ; comparaison multi-référentiels (Mefali / GCF / IFC / BOAD) ; profil de risque.
- **Don't use when** : 1 seule dimension → `show_kpi_card` ou `show_bar_chart`.
- **Example** :
```json
{
  "title": "Score ESG par pilier (Mefali vs GCF)",
  "axes": ["Environnement", "Social", "Gouvernance", "Climat", "Diversité"],
  "series": [
    {"name": "Mefali", "values": ["72", "65", "80", "60", "75"]},
    {"name": "GCF",    "values": ["75", "70", "78", "70", "72"]}
  ],
  "source_ids": [21, 22],
  "alt_text": "Radar comparant les scores Mefali et GCF sur 5 piliers ESG."
}
```

### show_bar_chart

- **Description** : Barres pour ventilation ou benchmarking.
- **Use when** : comparer plusieurs catégories sur une métrique.
- **Don't use when** : évolution temporelle → `show_line_chart` ; répartition d'un total → `show_pie_chart`.
- **Example** :
```json
{
  "title": "Score ESG par référentiel",
  "x_label": "Référentiel",
  "y_label": "Score /100",
  "bars": [
    {"label": "Mefali", "value": "72"},
    {"label": "GCF",    "value": "68"},
    {"label": "IFC",    "value": "70"},
    {"label": "BOAD",   "value": "65"}
  ],
  "source_ids": [21, 22, 23, 24],
  "alt_text": "Score ESG par référentiel : Mefali 72, GCF 68, IFC 70, BOAD 65."
}
```

### show_line_chart

- **Description** : Courbe d'évolution dans le temps.
- **Use when** : tendance mensuelle/annuelle d'une métrique.
- **Don't use when** : pas d'axe temps.
- **Example** :
```json
{
  "title": "Évolution de l'empreinte carbone (12 mois)",
  "x_label": "Mois",
  "y_label": "tCO2e",
  "series": [
    {"name": "2025", "points": [
      {"x": "2025-01", "y": "5.2"},
      {"x": "2025-02", "y": "4.9"}
    ]}
  ],
  "source_ids": [42],
  "alt_text": "Empreinte carbone mensuelle 2025."
}
```

### show_pie_chart / show_donut_chart

- **Description** : Répartition d'un total en parts.
- **Use when** : décomposition en catégories.
- **Don't use when** : > 10 catégories → `show_bar_chart`.
- **Example** :
```json
{
  "title": "Répartition des émissions par source",
  "slices": [
    {"label": "Énergie",   "value": "60"},
    {"label": "Transport", "value": "25"},
    {"label": "Déchets",   "value": "15"}
  ],
  "source_ids": [42],
  "alt_text": "Répartition des émissions : énergie 60%, transport 25%, déchets 15%."
}
```

### show_timeline

- **Description** : Étapes ou jalons sur une frise chronologique.
- **Use when** : roadmap projet, étapes candidature, échéances offre.
- **Don't use when** : courbe continue → `show_line_chart`.
- **Example** :
```json
{
  "title": "Étapes de candidature GCF",
  "items": [
    {"date": "2026-05-01", "label": "Soumission dossier",   "status": "done"},
    {"date": "2026-06-15", "label": "Pré-screening",         "status": "in_progress"},
    {"date": "2026-09-01", "label": "Décision finale",       "status": "pending"}
  ],
  "orientation": "horizontal",
  "alt_text": "Timeline candidature GCF avec 3 étapes."
}
```

### show_comparison_table

- **Description** : Tableau aligné comparant 2 à 5 entités.
- **Use when** : choix entre Offres ou intermédiaires.
- **Don't use when** : > 5 lignes/colonnes (limite MVP).
- **Example** :
```json
{
  "title": "Offres GCF vs BOAD",
  "columns": ["Critère", "GCF", "BOAD"],
  "rows": [
    {"label": "Frais de dossier", "values": ["Frais", "0%",   "1.2%"]},
    {"label": "Délai d'octroi",   "values": ["Délai", "180j", "90j"]}
  ],
  "source_ids": [55, 56],
  "alt_text": "Tableau comparatif Offres GCF et BOAD."
}
```

### show_match_card

- **Description** : Carte de compatibilité Projet ↔ Offre avec score, critères couverts/manquants, lien interne.
- **Use when** : suggérer ou évaluer un match Projet/Offre.
- **Don't use when** : juste afficher les infos d'une Offre.
- **Example** :
```json
{
  "projet_id": 12,
  "offre_id": 7,
  "score": 72,
  "criteres_couverts": ["Secteur agricole", "PME < 50 ETP", "Pays UEMOA"],
  "criteres_manquants": ["ISO 14001", "Étude d'impact"],
  "link": "/candidatures/new?projet=12&offre=7",
  "source_ids": [99],
  "alt_text": "Compatibilité 72% entre projet 12 et offre 7."
}
```

## P2 (DEFERRABLE)

### show_map

- **Description** : Carte Leaflet avec marqueurs.
- **Example** :
```json
{
  "title": "Localisation projet et bureaux GCF",
  "markers": [
    {"lat": "5.348", "lng": "-4.024", "label": "Siège PME",  "kind": "entreprise"},
    {"lat": "5.355", "lng": "-4.000", "label": "Bureau GCF", "kind": "intermediaire"}
  ],
  "alt_text": "Carte montrant le siège de la PME et le bureau GCF à Abidjan."
}
```

### show_mermaid

- **Description** : Diagramme libre Mermaid validé backend.
- **Example** :
```json
{
  "code": "flowchart LR\n  A[Soumission] --> B{Pré-screening}\n  B -->|OK| C[Évaluation]\n  B -->|KO| D[Rejet]",
  "alt_text": "Flowchart du processus de candidature GCF."
}
```

## Boucle retry F14

Tout payload non conforme déclenche un `validation_error` → relance LLM avec le message Pydantic. Boucle plafonnée à 3 itérations.
