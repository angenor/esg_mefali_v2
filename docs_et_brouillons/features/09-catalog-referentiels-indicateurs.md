# F09 — Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission

**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 0.7 (Mapping ESG), 9.1 (Gestion du Catalogue), 4.2 (Facteurs d'émission)
**Dépendances** : F04, F06, F07
**Estimation** : 3 jours

## Contexte et objectif

Cette feature livre la **couche atomique** du modèle ESG : les `Indicateurs` (unités de mesure ESG), les `Référentiels` (collections d'indicateurs avec seuils + poids), les `Critères` (conditions logiques sur indicateurs pour qualifier un projet), les `Documents requis` (papiers exigés par fonds/intermédiaire), et les `Facteurs d'émission` (kgCO2e par unité).

C'est ce qui permet d'avoir **une seule réponse de la PME qui alimente plusieurs scores** (ESG Mefali + GCF + IFC + BOAD…) sans duplication. La couche `Indicateur` est le pivot.

## User Stories

### US1 — CRUD Indicateurs (P1)
**En tant qu'**admin,
**je veux** créer/éditer/publier un Indicateur atomique avec définition, unité, ressources de calcul, sources,
**afin de** modéliser "% de déchets recyclés", "Émissions Scope 1 en tCO2e", "Présence d'une politique anti-corruption", etc.

**Champs** : `id, code (unique, ex: 'WASTE_RECYCLED_PCT'), name, definition (markdown), pillar ENUM('E','S','G','transverse'), unite, value_type ENUM('numeric','percentage','boolean','enum','text'), enum_values JSONB NULL, version, status, source_ids[]`.

**Test indépendant** : créer un Indicateur, le publier (avec source vérifiée), vérifier qu'il est référençable depuis un Référentiel et un Critère.

### US2 — CRUD Référentiels (P1)
**En tant qu'**admin,
**je veux** créer un Référentiel (ESG Mefali, taxonomie UEMOA, GCF, IFC PS, GRI, ODD, politique BOAD, politique BAD, SUNREF, etc.) qui :
- liste un ensemble d'`Indicateurs` avec poids et seuils,
- définit la formule d'agrégation (somme pondérée par défaut, formule custom possible),
- est versionné (F04).

**afin de** alimenter le scoring multi-référentiels de F23.

**Champs** : `referentiel : id, code, name, publisher, type ENUM('fonds','intermediaire','transverse','interne'), formula_type ENUM('weighted_sum','custom'), formula_expression TEXT NULL, version, valid_from, valid_to, status, source_ids[]`.
**Champs liés** : `referentiel_indicateur : referentiel_id, indicateur_id, poids, seuil_min NUMERIC NULL, seuil_max NUMERIC NULL, source_id`.

**Scénarios** :
1. Référentiel ESG Mefali : 30 indicateurs, poids variables, score sur 100.
2. Référentiel GCF : 8 critères de haut niveau, chacun lié à 3-5 indicateurs sous-jacents.
3. Référentiel BOAD : référence des indicateurs IFC PS + ajoute des critères propres.

### US3 — CRUD Critères d'éligibilité (P1)
**En tant qu'**admin,
**je veux** définir des Critères = expressions logiques sur indicateurs pour qualifier un projet,
**afin de** alimenter F25 Matching.

**Champs** : `critere : id, owner_type ENUM('fonds','intermediaire','offre','referentiel'), owner_id, expression_json (DSL simple), label, severity ENUM('blocking','warning','info'), source_id, version`.

Exemple expression : `{op: ">=", left: {indicateur: "WASTE_RECYCLED_PCT"}, right: {literal: 30}}`.

**Scénarios** :
1. Critère GCF "projet adaptation" : `country IN [LDC, SIDS]` — blocking.
2. Critère BOAD "taille PME" : `effectifs <= 200` — blocking.
3. Critère SUNREF Ecobank "garantie" : `garantie_provided = true` — warning.

### US4 — CRUD Documents requis (P1)
**En tant qu'**admin,
**je veux** lister les Documents requis par fonds et/ou par intermédiaire (statuts, étude de faisabilité, business plan, étude d'impact, lettres de soutien, attestation fiscale, etc.),
**afin de** alimenter la checklist documentaire de F26 (Génération de dossier) et F25 (Matching).

**Champs** : `document_requis : id, owner_type ENUM('fonds','intermediaire'), owner_id, name, description, type ENUM('juridique','financier','technique','impact','autre'), required_when JSONB NULL (conditions), source_id, version`.

### US5 — CRUD Facteurs d'émission (P1)
**En tant qu'**admin,
**je veux** maintenir la base des facteurs d'émission utilisés par F28 (Calculateur Carbone),
**afin de** garantir des chiffres sourcés ADEME / IPCC / IEA.

**Champs** : `facteur_emission : id, code (ex: 'ELEC_MIX_CI_KWH'), name, valeur NUMERIC, unite (ex: 'kgCO2e/kWh'), pays_iso2 NULL, scope ENUM('1','2','3'), categorie (energie, transport, dechets, achats), source_id, version, valid_from, valid_to`.

**Scénarios** :
1. Mix électrique Côte d'Ivoire 2024 : `0.456 kgCO2e/kWh` — source ADEME Base Carbone v23 page 87.
2. Diesel transport routier : `2.491 kgCO2e/L` — source IPCC AR6.
3. Le facteur évolue → nouvelle version créée, ancienne marquée `valid_to=now()`.

### US6 — Page de visualisation d'un Référentiel complet (P2)
**En tant qu'**admin,
**je veux** une page admin qui affiche un Référentiel avec :
- son entête (publisher, version, dates),
- la liste des indicateurs liés avec leurs poids et seuils,
- la formule d'agrégation,
- les références sources,
- l'historique des versions.

**afin de** auditer rapidement qu'il est complet et cohérent.

### US7 — Validation cohérence d'un Référentiel avant publication (P2)
**En tant qu'**admin,
**je veux** qu'au clic "Publier", le système vérifie :
- somme des poids = 100% (ou normalisée),
- toutes les sources sont `verified`,
- aucun indicateur référencé n'est en `draft`.

**afin de** ne pas publier un référentiel cassé.

## Exigences fonctionnelles

- **FR-001** : CRUD complet pour `indicateur`, `referentiel`, `critere`, `document_requis`, `facteur_emission` (5 endpoints chacun, avec `/publish`).
- **FR-002** : Endpoint `GET /admin/indicateurs?pillar=&search=` paginé avec filtres.
- **FR-003** : Endpoint `GET /admin/referentiels/{id}/full` → renvoie le référentiel + indicateurs liés (joined) + sources + version active. Optimisé pour l'affichage admin (US6) et pour F23 Scoring (consommé en lecture).
- **FR-004** : DSL d'expression de critère : structure JSON simple `{op, left, right}` avec opérateurs `==, !=, >=, <=, >, <, in, not_in, and, or, not`. Évaluateur backend (`evaluate(expr, context) -> bool`) testable. Pas de Turing complet — pas d'eval.
- **FR-005** : Validateur cohérence référentiel (US7) appelé en `POST /admin/referentiels/{id}/publish`.
- **FR-006** : Tous les objets sont versionnés (F04). Modifier un référentiel `published` crée v2.
- **FR-007** : Lookup helper `get_facteur(code, pays?, at?)` consommable par F28.
- **FR-008** : Lookup helper `get_referentiel(code, version?)` consommable par F23.
- **FR-009** : Endpoint `GET /admin/criteres?owner_type=fonds&owner_id=X` pour aligner les critères d'un fonds, d'un intermédiaire ou d'une offre.
- **FR-010** : Endpoint `GET /admin/documents-requis?owner_type=...&owner_id=X` similaire.

## Exigences non-fonctionnelles

- **NFR-001** : 200+ indicateurs, 20+ référentiels, 1000+ critères, 500+ facteurs d'émission supportés sans dégradation.
- **NFR-002** : Le DSL d'expression de critère est sandboxé : impossible d'exécuter du code arbitraire (parser strict).
- **NFR-003** : Les facteurs d'émission ont un index sur `(code, pays_iso2, valid_from)` pour lookup rapide.
- **NFR-004** : Toutes les opérations auditées (F04) et versionnées.

## Entités clés

- **Indicateur** (FR-001 US1).
- **Referentiel** + **ReferentielIndicateur** (US2).
- **Critere** (US3) + DSL JSON (FR-004).
- **DocumentRequis** (US4).
- **FacteurEmission** (US5).

## Success Criteria

- **SC-001** : Référentiel ESG Mefali (30 indicateurs) saisi + publié → score calculable depuis F23 (test à venir).
- **SC-002** : Référentiel GCF (8 critères / ~25 indicateurs) saisi avec sources GCF officielles → publié.
- **SC-003** : 50 facteurs d'émission ADEME saisis (énergie, transport, déchets) → consommables par F28.
- **SC-004** : Validateur de cohérence rejette un référentiel dont la somme des poids ≠ 100%.
- **SC-005** : DSL de critère évalué correctement sur 10 cas tests (and, or, not, in, comparaisons).

## Hors-scope MVP

- Éditeur visuel de DSL de critère (JSON brut OK en MVP, post-MVP : éditeur graphique drag-and-drop).
- Import en masse depuis CSV/Excel des indicateurs et facteurs (post-MVP).
- Référentiels composés (référentiel = union d'autres référentiels) — non implémenté en MVP, stratégie alternative : dupliquer manuellement les indicateurs.
- A/B testing de versions de référentiels.
- Marketplace de référentiels communautaires.

## Risques et points de vigilance

- **DSL de critère** : ne pas céder à la tentation d'un mini-langage trop riche. Garder JSON simple. Tout cas qui ne rentre pas → critère "manuel" + `severity=warning` + commentaire admin.
- **Cohérence référentiel ↔ indicateurs ↔ sources** : une chaîne de FK longue. Bien tester les cas où un indicateur passe en `outdated` après publication d'un référentiel.
- **Charge initiale de saisie** : 200+ indicateurs + 20 référentiels = ~3-5 jours de travail concentré pour l'équipe métier ESG. Prévoir le temps.
- **Facteurs d'émission par pays** : ADEME a peu de données Afrique. Compléter avec IEA Africa Energy Outlook + GHG Protocol grid. Stocker la chaîne de sources.
- **Indicateur déclaré atomique mais qui dérive d'autres indicateurs** : éviter en MVP. Si un indicateur est dérivable, le calculer côté F23 dans la formule du référentiel, pas en cascade d'indicateurs.
