# Feature Specification: Scoring ESG Multi-Référentiels

**Feature Branch**: `023-scoring-esg-multi-referentiels`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F23 — Scoring ESG multi-référentiels (Mefali + UEMOA/GCF/IFC/GRI/ODD + intermédiaires). MVP P1 minimal vert : moteur de calcul d'un score ESG par référentiel basé sur les indicateurs F09 et les valeurs PME (entreprise/projet), avec snapshot de version, détail couverts/manquants, recalcul à la demande. Différé : activation contextuelle fonds+intermédiaire, benchmarking sectoriel, historique chart."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Score ESG Mefali (vitrine principale) (Priority: P1)

En tant que PME, je veux voir un score global sur 100 (et le détail par pilier E/S/G) selon le référentiel "ESG Mefali", afin d'avoir une vue synthétique compréhensible de ma maturité ESG.

**Why this priority** : c'est l'élément vitrine de la plateforme, la justification produit principale. Sans ce score, F23 n'a pas de valeur visible pour la PME.

**Independent Test** : créer une PME, renseigner profil entreprise + au moins un projet, déclencher le calcul du référentiel `ESG_MEFALI` actif → la PME reçoit `{score_global, scores_by_pillar:{E,S,G}, indicateurs_couverts, indicateurs_manquants, sources_used}`. Le résultat est persisté et relisible.

**Acceptance Scenarios** :

1. **Given** une PME avec entreprise renseignée et 1 projet, et un référentiel `ESG_MEFALI` publié avec 5 indicateurs (au moins 1 par pilier E/S/G), **When** la PME demande son scoring Mefali, **Then** elle reçoit un score global entre 0 et 100, des scores par pilier, et la liste des indicateurs couverts (avec valeur et contribution) + manquants.
2. **Given** une PME sans aucune donnée entreprise, **When** elle demande son scoring, **Then** elle reçoit un score `null` ou 0 avec coverage = 0 et tous les indicateurs en `manquants`, sans erreur 500.
3. **Given** un référentiel publié, **When** un calcul est effectué, **Then** la version du référentiel est snapshotée dans le résultat (référentiel_id + version) et reste reproductible si on relance avec les mêmes valeurs.

---

### User Story 2 — Scores par référentiel externe (UEMOA/GCF/IFC/GRI/ODD) (Priority: P1)

En tant que PME, je veux pouvoir lister tous les scores disponibles selon les référentiels publiés (Mefali + externes) afin de comprendre où je suis bien positionnée et où je dois progresser.

**Why this priority** : la promesse multi-référentiels est l'un des points différenciants. Un seul moteur paramétré sert tous les référentiels.

**Independent Test** : un compte avec 3 référentiels publiés (`ESG_MEFALI`, `GCF`, `UEMOA`) → l'endpoint liste retourne 3 scores calculés à la volée pour la même entité.

**Acceptance Scenarios** :

1. **Given** 3 référentiels publiés ayant des indicateurs en commun et propres, **When** la PME demande la liste de ses scores pour son entreprise, **Then** elle reçoit une entrée par référentiel avec son score global et le code du référentiel.
2. **Given** un référentiel sans indicateur publié, **When** un score est demandé, **Then** la réponse indique `score=null, indicateurs_couverts=[]` et n'échoue pas.

---

### User Story 3 — Détail des indicateurs couverts / manquants (Priority: P1)

En tant que PME, je veux pouvoir cliquer sur un score pour consulter le détail des indicateurs qui contribuent au calcul (avec valeur, poids, contribution) et la liste des indicateurs manquants à renseigner pour améliorer mon score.

**Why this priority** : sans explicabilité, le score n'est pas actionnable et perd sa valeur pédagogique (cohérent F03 sourçage).

**Independent Test** : pour une PME avec 6 indicateurs sur 10 renseignés, l'endpoint détail retourne 6 entrées dans `indicateurs_couverts` (avec value, weight, contribution, source_id du mapping référentiel→indicateur) et 4 entrées dans `indicateurs_manquants` (avec code, raison "valeur absente").

**Acceptance Scenarios** :

1. **Given** une PME avec une partie des indicateurs renseignés, **When** elle consulte le détail d'un score, **Then** chaque indicateur couvert présente `{indicateur_code, value, weight, contribution, source_id}` et chaque indicateur manquant présente `{indicateur_code, reason}`.
2. **Given** un indicateur lié au référentiel mais sans `source_id` côté `referentiel_indicateur`, **When** le calcul est effectué, **Then** une erreur de configuration est journalisée et l'indicateur est exclu du calcul (signalé en manquant) — le score reste calculable.

---

### User Story 4 — Recalcul à la demande (Priority: P1)

En tant que PME, je veux pouvoir déclencher manuellement un recalcul de mon score afin de vérifier l'impact d'une modification de profil sans attendre un job de fond.

**Why this priority** : indispensable pour TDD (déterminisme) et pour rendre la feature interactive en MVP. Le recalcul automatique au save profil est différé.

**Independent Test** : `POST /me/scoring/{entity}/{id}/recompute?referentiel=...` recalcule, persiste un nouveau `score_calculation` et le retourne.

**Acceptance Scenarios** :

1. **Given** un score précédent calculé à T0, **When** la PME modifie une valeur entreprise et demande un recalcul, **Then** un nouveau `score_calculation` est créé avec `computed_at` postérieur et reflète la nouvelle valeur.
2. **Given** une PME tentant de recalculer un score sur une entité d'un autre compte, **When** la requête arrive, **Then** elle est rejetée par RLS / permissions (404 ou 403).

---

### User Story 5 — Grille E/S/G dérivée des indicateurs (Priority: P1)

En tant que développeur, je veux que la grille E/S/G du Module 2.2 soit une projection des indicateurs `pillar` du référentiel ESG Mefali, sans table dédiée, afin de respecter le mapping unique (Module 0.7) et d'éviter la duplication de données.

**Why this priority** : invariant architectural. Toute table redondante condamnerait la maintenance long terme.

**Independent Test** : ajouter un indicateur `pillar='E'` à `ESG_MEFALI` puis recalculer → le score E mis à jour, sans modification de schéma DB.

**Acceptance Scenarios** :

1. **Given** un référentiel `ESG_MEFALI` avec 3 indicateurs E, 2 S, 1 G, **When** un calcul est effectué, **Then** `scores_by_pillar` contient les 3 piliers avec leurs scores normalisés respectifs et la somme pondérée donne le score global.
2. **Given** un référentiel sans aucun indicateur sur le pilier `S`, **When** un calcul est effectué, **Then** `scores_by_pillar.S` vaut `null` (et non 0) — distinction "vide" vs "zéro".

---

### Edge Cases

- Aucun indicateur publié pour le référentiel → `score=null, scores_by_pillar={}, indicateurs_couverts=[], indicateurs_manquants=[]`, pas d'erreur 500.
- Référentiel inactif/draft → 404 (la PME ne voit que les référentiels publiés actifs).
- Tous les indicateurs marqués manquants → `score=null`, coverage=0, recalcul possible plus tard.
- Indicateur lié au référentiel mais source de valeur introuvable (mapping `value_source_path` absent) → exclu en `manquants` avec `reason="value_source_unmapped"`.
- Poids total des indicateurs couverts = 0 → `score=null` (division par zéro évitée), pas 500.
- Tentative cross-tenant : un utilisateur PME demande un calcul sur l'entité d'un autre compte → 404 (RLS).
- Référentiel republié pendant un calcul long → le calcul snapshote la version résolue à `t0` (non rétroactif).
- Indicateur `value_type='enum'` avec valeur PME hors `enum_values` → exclu en manquant avec `reason="invalid_value"`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT exposer un service de calcul `compute_score(entity_type, entity_id, referentiel_code, account_id)` produisant `{score_global, scores_by_pillar, indicateurs_couverts, indicateurs_manquants, sources_used, referentiel_version}`.
- **FR-002** : Le système DOIT supporter au minimum la formule `weighted_sum` (Module 0.7), normalisée sur 100 et calculée uniquement sur les indicateurs couverts (coverage partielle gérée par renormalisation des poids).
- **FR-003** : Le système DOIT persister chaque calcul dans une table `score_calculation` avec `(account_id, entity_type, entity_id, referentiel_id, referentiel_version, score_global, scores_by_pillar, details_json, computed_at)` et un index pour récupérer le dernier score par entité+référentiel.
- **FR-004** : Le système DOIT exposer `GET /me/scoring/{entity_type}/{entity_id}` listant le dernier score actif par référentiel publié.
- **FR-005** : Le système DOIT exposer `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}` retournant le détail (couverts/manquants/sources/version).
- **FR-006** : Le système DOIT exposer `POST /me/scoring/{entity_type}/{entity_id}/recompute?referentiel=` pour recalculer à la demande et persister un nouveau snapshot.
- **FR-007** : Le système DOIT lire les valeurs PME via une couche de mapping `value_source_resolver` (champ `entreprise.<colonne>` pour MVP), et déclarer un indicateur en `manquant` si la valeur est `null` ou non disponible.
- **FR-008** : Le système DOIT renforcer l'isolation tenant : impossible de calculer ou lire un score d'une entité hors `account_id` courant (RLS strict).
- **FR-009** : Le système DOIT renvoyer `404` si le référentiel n'est pas publié ou si l'entité n'appartient pas au compte.
- **FR-010** : Le système DOIT garantir le déterminisme : mêmes valeurs PME + même version de référentiel → même score (utilisé en tests).
- **FR-011** : Le système DOIT exposer la grille E/S/G de la PME comme projection dynamique des indicateurs `pillar` du référentiel ESG Mefali (pas de table dédiée).
- **FR-012** : Le système DOIT journaliser via le mécanisme d'audit existant chaque calcul de score (append-only, source_of_change interne).

### Out of Scope (DEFERRED, post-MVP)

- US3 — Endpoint d'activation contextuelle `GET /me/scoring/offre/{offre_id}` (deux scores fonds + intermédiaire avec bottleneck) — requiert F25 matching offre.
- US5 — Benchmarking sectoriel (`/me/scoring/{ref}/benchmark`) — requiert F32 dashboard + anonymisation.
- US6 — Historique time-series (`/me/scoring/{entity}/{ref}/history`) — vue `show_line_chart`.
- US7 (partie auto) — Recalcul automatique debounced 5s au save profil — sera attaché par hook F11/F12 plus tard. Le recalcul manuel est livré.
- Formules `custom` (eval JSON safe) — MVP uniquement `weighted_sum`.
- Sources cliquables côté UI Vue — la donnée `source_id` est exposée par l'API, mais le rendu front est hors scope.

### Key Entities

- **ScoreCalculation** : un calcul figé pour un compte, une entité (entreprise/projet), un référentiel et sa version. Contient le score global, les scores par pilier (JSON), les détails (couverts/manquants/sources_used), et l'horodatage de calcul.
- **Referentiel** (réutilisé F09) : code, version, formule (`weighted_sum`), statut (`published`).
- **Indicateur** (réutilisé F09) : code, pillar (`E|S|G|GOV|TRANS`), value_type, status, version.
- **ReferentielIndicateur** (réutilisé F09) : association poids + source_id + seuils min/max.
- **Entreprise / Projet** (réutilisés F11/F12) : sources de valeur pour les indicateurs MVP.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : 100 % des calculs sur un référentiel comportant au moins 1 indicateur publié retournent un résultat structurellement valide (pas d'erreur 500), couverture partielle incluse.
- **SC-002** : Pour une PME complète sur un référentiel à 30 indicateurs, le calcul d'un score retourne en moins de 500 ms côté API (cible NFR-001 du brief = 200 ms p95, on se donne 500 ms en MVP avec marge).
- **SC-003** : Deux calculs successifs sans modification de données produisent un score global identique au centième près (déterminisme).
- **SC-004** : 100 % des indicateurs couverts dans la réponse exposent un `source_id` réutilisable (cliquable côté F03), audité par tests automatiques.
- **SC-005** : 0 fuite cross-tenant : un test d'intégration vérifie qu'un utilisateur PME B ne peut ni lire ni recalculer un score de PME A.
- **SC-006** : Couverture de tests ≥ 80 % sur le service de scoring.

## Assumptions

- F09 (référentiels/indicateurs/critères) est mergé : les modèles `Referentiel`, `Indicateur`, `ReferentielIndicateur` existent en base avec leurs données seed (au moins `ESG_MEFALI` ou un référentiel de test).
- F11/F12 fournissent les modèles `entreprise` et `projet` avec des colonnes lisibles via SQLAlchemy. Si certaines colonnes attendues n'existent pas (ex. `taille_effectifs`), la feature livrera une couche d'abstraction `ValueSourceResolver` extensible et signalera ces indicateurs en manquants pour l'instant.
- Pour le MVP, le mapping indicateur → champ entreprise est minimaliste : on lit `entreprise.<colonne>` selon une convention de nommage (ex. `value_source_path = "entreprise.taille_effectifs"`), avec fallback en "manquant" si la colonne n'existe pas.
- La normalisation d'un indicateur numérique sur 0-100 utilise les seuils `seuil_min/seuil_max` de `referentiel_indicateur` quand présents, sinon une normalisation linéaire bornée 0-100 par défaut.
- Pas d'orchestration LLM dans cette feature (calcul purement déterministe sur données structurées).
- L'audit reuse le helper `record_audit` (F04) déjà disponible en backend.
- L'authentification existe : routes `/me/...` filtrées par `account_id` du JWT, conformes au RLS Postgres déjà en place (F02).

## Dependencies

- **F02** auth + RLS — pour le filtre tenant et l'authentification des routes `/me/...`.
- **F04** audit log + versioning — pour `record_audit` et le snapshot de version référentiel.
- **F09** catalog référentiels/indicateurs — modèles obligatoires (référentiels publiés avec indicateurs liés).
- **F11/F12** entreprise + projets — fournissent les valeurs source pour les indicateurs.
