# Feature Specification: Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission

**Feature Branch**: `009-catalog-referentiels-indicateurs`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F09 — Phase 1 Back-office Admin & Catalogue. Modules brainstorm 0.7 (Mapping ESG), 9.1 (Gestion du Catalogue), 4.2 (Facteurs d'émission). Dépendances : F04, F06, F07.

## Contexte métier

Cette feature livre la **couche atomique du modèle ESG** : `Indicateurs` (unités de mesure), `Référentiels` (collections d'indicateurs avec poids et seuils), `Critères` (expressions logiques d'éligibilité), `Documents requis` (livrables exigés par fonds/intermédiaires) et `Facteurs d'émission` (kgCO2e par unité). La couche `Indicateur` est le **PIVOT du Module 0.7 — Mapping ESG** : une seule réponse PME alimente plusieurs scores (ESG Mefali, GCF, IFC, BOAD, GRI, ODD…) sans duplication.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CRUD Indicateurs atomiques (Priority: P1)

L'admin crée, édite, et publie un Indicateur atomique avec sa définition (markdown), son unité, son type de valeur (numérique, pourcentage, booléen, énumération, texte), son pilier ESG (E/S/G/transverse) et au moins une source vérifiée. L'Indicateur peut ensuite être référencé par plusieurs Référentiels et Critères, sans duplication.

**Why this priority**: Sans Indicateur, aucun Référentiel ni Critère n'est constructible. C'est la brique de base du pivot mapping ESG (Module 0.7) qui rend possible le scoring multi-référentiels (F23) et l'éligibilité (F25).

**Independent Test**: Créer un Indicateur `WASTE_RECYCLED_PCT`, attacher au moins une source vérifiée, le publier, puis vérifier qu'il apparaît dans la liste publique paginée et qu'il est référençable depuis un Référentiel test et un Critère test.

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il crée un Indicateur en `draft` avec code unique, nom, définition, pilier, unité, type de valeur et au moins une source `verified`, **Then** l'objet est persisté en `draft` v1, l'événement est audité et il est visible uniquement aux admins.
2. **Given** un Indicateur `draft` avec sources vérifiées, **When** l'admin clique `Publier`, **Then** le statut passe à `published`, la version devient active, et l'Indicateur est référençable.
3. **Given** un Indicateur `published`, **When** un admin tente une modification destructrice (changement de `code`, `value_type`), **Then** le système refuse en MVP, sinon une nouvelle version v2 est créée via le mécanisme `publish_new_version` + `If-Match` (héritage F04).
4. **Given** un Indicateur sans aucune source attachée, **When** l'admin tente de publier, **Then** le système rejette avec un message explicite (sourcing obligatoire — Invariant Module 0).

---

### User Story 2 - CRUD Référentiels avec indicateurs liés et formule (Priority: P1)

L'admin crée un Référentiel (ESG Mefali, GCF, IFC PS, BOAD, BAD, GRI, ODD, SUNREF, taxonomie UEMOA, interne) qui regroupe un ensemble d'Indicateurs avec leur poids et seuils min/max, définit la formule d'agrégation (somme pondérée par défaut, formule custom optionnelle), est versionné, et est sourcé.

**Why this priority**: Le Référentiel est l'objet exploité par F23 Scoring multi-référentiels. Sans lui, pas de score.

**Independent Test**: Créer un Référentiel `ESG_MEFALI_V1` de type `interne` avec 3 Indicateurs publiés liés (poids 30/30/40, somme 100), sources GCF officielles attachées, formule `weighted_sum`, le publier, puis appeler `GET /admin/referentiels/{id}/full` et vérifier qu'il renvoie l'entête, les indicateurs joints avec poids et seuils, les sources et la version active.

**Acceptance Scenarios**:

1. **Given** des Indicateurs publiés, **When** l'admin crée un Référentiel `draft` et y attache N Indicateurs avec poids et seuils, **Then** la table de liaison `referentiel_indicateur` est peuplée et chaque ligne porte sa propre source.
2. **Given** un Référentiel `draft` avec poids ne sommant pas à 100, **When** l'admin clique `Publier`, **Then** le validateur de cohérence rejette la publication (US7) avec liste explicite des défauts (somme ≠ 100, indicateurs en `draft`, sources non `verified`).
3. **Given** un Référentiel `published` v1, **When** l'admin modifie un poids, **Then** une v2 `draft` est créée via `publish_new_version` + `If-Match`, v1 reste active jusqu'à publication de v2.
4. **Given** un Référentiel publié, **When** F23 appelle le helper `get_referentiel(code, version?)`, **Then** la version active (ou la version demandée) est renvoyée avec ses indicateurs et formule.

---

### User Story 3 - CRUD Critères d'éligibilité avec DSL JSON (Priority: P1)

L'admin définit des Critères = expressions logiques sur Indicateurs ou contexte projet, attachés à un fonds, un intermédiaire, une offre ou un référentiel, avec sévérité `blocking`/`warning`/`info`. Le DSL est strictement structuré en JSON `{op, left, right}` et évaluable côté backend par un parser sandboxé sans exécution de code arbitraire.

**Why this priority**: Les Critères alimentent F25 Matching projet/offre. Sans eux, aucune décision d'éligibilité automatisée n'est possible.

**Independent Test**: Créer 10 Critères couvrant les 11 opérateurs (`==, !=, >=, <=, >, <, in, not_in, and, or, not`), évaluer chaque expression contre un contexte test fourni, vérifier que le résultat booléen est conforme à l'attendu (cf SC-005).

**Acceptance Scenarios**:

1. **Given** un fonds GCF existant, **When** l'admin crée un Critère `country IN ['LDC', 'SIDS']` de sévérité `blocking` avec source GCF Project Eligibility, **Then** le Critère est persisté, audité, versionné et lié au fonds.
2. **Given** un Critère avec une expression JSON invalide (opérateur inconnu, profondeur excessive, référence à un Indicateur non publié), **When** l'admin sauvegarde, **Then** le parser rejette avec une erreur ciblée (clé fautive, position dans l'arbre).
3. **Given** une expression JSON et un contexte projet, **When** le moteur d'évaluation est appelé, **Then** il renvoie `true`/`false` sans jamais exécuter d'eval ni de code dynamique (NFR-002).
4. **Given** un fonds, **When** on appelle `GET /admin/criteres?owner_type=fonds&owner_id=X`, **Then** la liste des critères blocking, warning et info est retournée triée par sévérité décroissante.

---

### User Story 4 - CRUD Documents requis par fonds/intermédiaire (Priority: P1)

L'admin liste les documents exigés par un fonds ou un intermédiaire (statuts, étude de faisabilité, business plan, étude d'impact, lettres de soutien, attestation fiscale…), classés par type (juridique, financier, technique, impact, autre), avec conditions optionnelles (`required_when` JSON) et source.

**Why this priority**: Alimente la checklist documentaire de F26 (générateur de dossier candidature) et F25 (matching).

**Independent Test**: Pour un fonds donné, créer 5 documents requis (1 par type), publier, puis appeler `GET /admin/documents-requis?owner_type=fonds&owner_id=X` et vérifier que les 5 documents sont retournés avec leurs sources et conditions.

**Acceptance Scenarios**:

1. **Given** un fonds, **When** l'admin crée un Document Requis "Statuts juridiques" de type `juridique` avec source attachée, **Then** il est persisté en `draft`, auditable et publiable.
2. **Given** un Document Requis avec `required_when: {effectifs: ">", literal: 50}`, **When** F26 demande la checklist d'un projet d'une PME de 30 salariés, **Then** ce document n'est pas requis ; pour 60 salariés, il l'est.

---

### User Story 5 - CRUD Facteurs d'émission sourcés et versionnés (Priority: P1)

L'admin maintient la base des facteurs d'émission utilisés par F28 (calculateur carbone) avec code unique, valeur, unité (`kgCO2e/<unité>`), pays optionnel (ISO2), scope (1/2/3), catégorie (énergie, transport, déchets, achats), source vérifiée et fenêtre de validité `valid_from`/`valid_to`.

**Why this priority**: Sans facteurs d'émission sourcés, F28 ne peut produire de chiffres carbone défendables. Le sourcing y est CRITIQUE (Invariant Module 0).

**Independent Test**: Saisir 50 facteurs ADEME (énergie, transport, déchets) avec sources `Base Carbone v23` vérifiées, publier, puis appeler `get_facteur('ELEC_MIX_CI_KWH', pays='CI', at='2024-06-01')` et vérifier que la bonne version active est renvoyée.

**Acceptance Scenarios**:

1. **Given** la sortie d'une nouvelle version ADEME, **When** l'admin crée un nouveau facteur `ELEC_MIX_CI_KWH` v2 avec `valid_from=2025-01-01`, **Then** v1 est automatiquement marqué `valid_to=2024-12-31` et le helper `get_facteur(code, pays, at)` renvoie la bonne version selon la date.
2. **Given** une recherche par `(code, pays_iso2, valid_from)`, **When** F28 demande un facteur, **Then** la requête est servie via index dédié (NFR-003).
3. **Given** un facteur sans pays renseigné, **When** F28 demande pour un pays donné, **Then** le helper applique la logique de fallback : pays exact → mondial → erreur explicite.

---

### User Story 6 - Page admin de visualisation Référentiel complet (Priority: P2)

L'admin ouvre la page d'un Référentiel et voit son entête (publisher, version, dates de validité, statut), la liste de ses Indicateurs liés avec leurs poids et seuils, la formule d'agrégation, la liste des sources, et l'historique des versions précédentes.

**Why this priority**: Indispensable pour audit qualité avant publication, mais peut suivre les CRUD P1 sans bloquer la valeur métier minimale.

**Independent Test**: Pour un Référentiel publié avec 5 Indicateurs, ouvrir la page et vérifier que l'entête, la table des indicateurs liés, les sources et au moins une version antérieure sont affichées correctement (UI bottom sheet).

**Acceptance Scenarios**:

1. **Given** un Référentiel publié v2 avec v1 archivée, **When** l'admin ouvre la page, **Then** v2 est affichée par défaut et un sélecteur permet de consulter v1.
2. **Given** un Référentiel avec 30 Indicateurs liés, **When** la page se charge, **Then** elle reste lisible et utilisable (tri, filtre par pilier).

---

### User Story 7 - Validateur de cohérence avant publication d'un Référentiel (Priority: P2)

Au clic `Publier` d'un Référentiel, le système exécute un validateur qui vérifie : (a) somme des poids = 100% (à epsilon près) OU normalisation activée, (b) toutes les sources `verified`, (c) aucun Indicateur référencé en `draft` ou `outdated`, (d) formule custom (si présente) parse sans erreur. Si l'un échoue, la publication est bloquée avec liste détaillée des défauts.

**Why this priority**: Filet de sécurité critique mais activable après le CRUD de base. Sans lui, on peut publier un Référentiel cassé et fausser F23.

**Independent Test**: Créer un Référentiel avec poids sommant à 95, déclencher la publication, vérifier rejet ; corriger à 100, vérifier publication acceptée.

**Acceptance Scenarios**:

1. **Given** un Référentiel `draft` dont la somme des poids ≠ 100% à epsilon 0.01 près, **When** l'admin tente de publier, **Then** le serveur répond `409 Conflict` avec un payload `{errors: [{code: 'WEIGHTS_SUM_INVALID', actual: 95, expected: 100}]}`.
2. **Given** un Référentiel `draft` référençant un Indicateur `draft`, **When** l'admin tente de publier, **Then** la publication est rejetée avec liste des indicateurs non publiés.

---

### Edge Cases

- Un Indicateur passe en `outdated` après publication d'un Référentiel le référençant : le Référentiel reste publié (immutable), mais une alerte admin est levée et le Référentiel est marqué pour révision.
- Un facteur d'émission a une période de validité qui se chevauche avec une autre version du même code : interdit par contrainte d'unicité `(code, pays_iso2, valid_from)` ; rejet à la création.
- Un Critère référence un Indicateur supprimé : la suppression d'Indicateur publié est interdite ; seul l'archivage (`status=archived`) est autorisé, et les Critères restent évaluables sur les contextes historiques.
- Un Référentiel composé (union d'autres Référentiels) : hors-scope MVP, dupliquer manuellement les Indicateurs.
- Un Indicateur dérivé d'autres indicateurs : éviter en MVP, calculer dans la formule custom du Référentiel côté F23.
- Un fonds sans aucun Critère ni Document requis : autorisé en MVP (matching renverra "non décidable").
- Concurrence d'édition : protégée par `If-Match`/ETag (héritage F04/F06).
- Un Indicateur avec `value_type=enum` mais `enum_values=NULL` : rejet de validation à la création.
- Une expression JSON de Critère imbriquée à profondeur > 6 niveaux : rejet par parser pour limiter le coût d'évaluation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer un CRUD complet (`POST`, `GET list`, `GET id`, `PUT/PATCH`, `DELETE`/`archive`, `POST publish`) pour chacune des 5 entités : `indicateur`, `referentiel`, `critere`, `document_requis`, `facteur_emission`, sous le préfixe `/admin`, conformément au registry F06.
- **FR-002**: Le système DOIT fournir `GET /admin/indicateurs?pillar=&search=&status=` paginé avec filtres sur pilier (E/S/G/transverse), recherche plein-texte sur `code` et `name`, et statut.
- **FR-003**: Le système DOIT fournir `GET /admin/referentiels/{id}/full` qui retourne l'entête du Référentiel + table jointe `referentiel_indicateur` (avec données Indicateur en lecture) + sources + version active. Optimisé pour US6 et pour consommation par F23.
- **FR-004**: Le système DOIT évaluer les Critères via un DSL JSON strict : structure `{op, left, right}` avec opérateurs `==, !=, >=, <=, >, <, in, not_in, and, or, not`. Les feuilles peuvent être `{indicateur: code}`, `{context: key}` ou `{literal: valeur}`. L'évaluateur DOIT être un parser/interpréteur custom sandboxé : aucun `eval`, aucun chargement dynamique, aucune introspection.
- **FR-005**: Le système DOIT exécuter le validateur de cohérence (US7) lors de `POST /admin/referentiels/{id}/publish` ; en cas d'échec, retourner `409 Conflict` avec liste structurée des défauts.
- **FR-006**: Toutes les entités DOIVENT être versionnées via le mécanisme F04 (`publish_new_version` + `If-Match`) ; modifier un objet `published` crée une v(N+1) `draft`.
- **FR-007**: Le système DOIT exposer un helper backend `get_facteur(code, pays_iso2?, at?)` consommable par F28, avec fallback pays exact → mondial → 404.
- **FR-008**: Le système DOIT exposer un helper backend `get_referentiel(code, version?)` consommable par F23, retournant la version active par défaut.
- **FR-009**: Le système DOIT fournir `GET /admin/criteres?owner_type=&owner_id=` triant par sévérité (`blocking` > `warning` > `info`).
- **FR-010**: Le système DOIT fournir `GET /admin/documents-requis?owner_type=&owner_id=` retournant la liste des documents requis avec leur catégorie et conditions `required_when`.
- **FR-011**: Le système DOIT appliquer la politique RLS catalogue global (politique alternative comme F08) : tous les admins voient le catalogue ; les utilisateurs PME ne voient que les objets `published`.
- **FR-012**: Le système DOIT auditer (F04, append-only) chaque création, modification, publication, archivage, et suppression sur les 5 entités, avec acteur, payload avant/après, et timestamp.
- **FR-013**: Le système DOIT rejeter la publication d'un Indicateur, Référentiel, Critère, Document Requis ou Facteur d'émission ne possédant pas au moins une source `verified` (Invariant sourcing Module 0). Le sourcing est CRITIQUE pour facteurs d'émission, seuils et formules.
- **FR-014**: Le système DOIT garantir l'unicité de `code` au sein de chaque entité catalogue (insensible à la casse, normalisée en upper snake case).
- **FR-015**: Le système DOIT permettre l'archivage (`status=archived`) mais interdire la suppression dure d'un objet `published` référencé par d'autres objets catalogue ou par un dossier projet (intégrité référentielle catalogue).

### Key Entities

- **Indicateur**: unité de mesure ESG atomique. Attributs : code unique, nom, définition (markdown), pilier (E/S/G/transverse), unité, type de valeur, valeurs possibles (si enum), version, statut, sources liées.
- **Référentiel**: collection nommée d'Indicateurs avec poids et seuils. Attributs : code, nom, publisher, type (fonds/intermédiaire/transverse/interne), type de formule (somme pondérée par défaut, custom), expression de formule, version, fenêtre de validité, statut, sources.
- **ReferentielIndicateur**: table de liaison N-N. Attributs : référentiel, indicateur, poids, seuil min/max, source.
- **Critere**: expression logique sur Indicateurs ou contexte. Attributs : owner (fonds/intermédiaire/offre/référentiel), expression JSON, label, sévérité (blocking/warning/info), source, version.
- **DocumentRequis**: document exigé par un fonds ou un intermédiaire. Attributs : owner, nom, description, type (juridique/financier/technique/impact/autre), conditions JSON, source, version.
- **FacteurEmission**: coefficient kgCO2e par unité. Attributs : code, nom, valeur, unité, pays ISO2, scope (1/2/3), catégorie, source, version, fenêtre de validité.
- **Source** (héritée F07) : référence bibliographique citable, statut `verified`/`pending`/`rejected`.

### Non-Functional Requirements

- **NFR-001**: Le catalogue DOIT supporter 200+ Indicateurs, 20+ Référentiels, 1000+ Critères et 500+ Facteurs d'émission sans dégradation perceptible des temps de réponse admin (≤ 500 ms p95 pour list paginée, ≤ 1 s pour `/full`).
- **NFR-002**: Le DSL d'expression de Critère DOIT être strictement sandboxé : interdiction d'exécuter du code arbitraire, parser strict, profondeur d'arbre limitée, taille de payload limitée.
- **NFR-003**: La table `facteur_emission` DOIT porter un index sur `(code, pays_iso2, valid_from)` pour servir le helper `get_facteur` en O(log n).
- **NFR-004**: Toutes les opérations DOIVENT être auditées (F04) et versionnées (F04).
- **NFR-005**: Toutes les valeurs monétaires éventuellement portées par un Critère ou un Document Requis (ex. seuil de financement) DOIVENT utiliser le type Money pegged FCFA-EUR à 655.957 (Invariant Module 0).
- **NFR-006**: L'UI admin de chaque entité DOIT respecter le pattern bottom sheet (Invariant Module 0).
- **NFR-007**: Plateforme fermée : seuls les profils `admin` accèdent aux endpoints `/admin/...` ; les profils `pme` n'accèdent qu'aux helpers de lecture publique nécessaires (`get_referentiel`, `get_facteur` côté serveur via F23/F28, jamais en direct).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Le Référentiel `ESG_MEFALI_V1` (30 Indicateurs, somme des poids = 100, sources vérifiées) est saisi et publié sans intervention manuelle hors validateur ; il est ensuite consommable par F23 via `get_referentiel('ESG_MEFALI', 1)`.
- **SC-002**: Le Référentiel GCF (8 critères de haut niveau et ~25 Indicateurs sous-jacents) est saisi avec sources GCF officielles et publié.
- **SC-003**: 50 Facteurs d'émission ADEME (énergie, transport, déchets) sont saisis avec sources `Base Carbone` vérifiées et consommables par F28 via `get_facteur(...)`.
- **SC-004**: Le validateur de cohérence rejette en moins de 200 ms toute publication de Référentiel avec somme des poids ≠ 100% (epsilon 0.01) ou Indicateur référencé non publié, en retournant la liste exhaustive des défauts.
- **SC-005**: Le moteur DSL évalue correctement 10 cas tests couvrant les 11 opérateurs (`==, !=, >=, <=, >, <, in, not_in, and, or, not`) avec 100% de réussite et aucune fuite d'exécution arbitraire (vérifiée par fuzzing négatif).
- **SC-006**: Toute modification d'objet catalogue laisse une trace d'audit consultable depuis le back-office en moins de 2 s.
- **SC-007**: La page de visualisation Référentiel complet (US6) charge en moins de 1 s pour un référentiel à 30 Indicateurs.
- **SC-008**: 100% des objets catalogue publiés portent au moins une source `verified` (vérifiable par requête de contrôle).

## Assumptions

- Les entités F04 (audit, versioning, `publish_new_version` + `If-Match`), F06 (registry admin, ETag, crud_router, publish gate, scaffolding routes `/admin`) et F07 (Source `verified`/`pending`/`rejected`) sont disponibles et stables. Cette feature les compose sans les redéfinir.
- La politique RLS catalogue global (alternative, comme F08) est appliquée : admins voient tout ; PME voient les objets `published` uniquement, à travers les helpers serveur F23/F28.
- Le DSL de Critère est suffisant en MVP pour exprimer les règles d'éligibilité connues (cf scénarios 1-3 US3) ; les cas hors DSL deviennent des Critères "manuels" avec sévérité `warning` et commentaire admin (hors-scope MVP : éditeur visuel).
- L'import en masse depuis CSV/Excel (Indicateurs, Facteurs d'émission) est hors-scope MVP ; la saisie initiale (200+ Indicateurs, 50 Facteurs) est manuelle, estimée 3 à 5 jours équipe métier.
- Les Référentiels composés (union de Référentiels) sont hors-scope MVP : duplication manuelle des Indicateurs.
- Les Indicateurs dérivés (calcul à partir d'autres Indicateurs) sont hors-scope MVP : la dérivation est portée par la formule custom d'un Référentiel côté F23.
- Les facteurs d'émission Afrique sont complétés par IEA Africa Energy Outlook et GHG Protocol grid factors quand ADEME est insuffisant ; la chaîne de sources est conservée.
- L'A/B testing de versions de Référentiels et la marketplace de Référentiels communautaires sont hors-scope MVP.
- La plateforme reste fermée (PME + Admin uniquement) : aucune API publique non-authentifiée n'expose le catalogue.

## Clarifications (auto-resolved 2026-04-29)

- **DSL feuilles**: uniquement `{indicateur:CODE}`, `{context:KEY}`, `{literal:VALUE}` — aucune fonction, aucune variable d'env.
- **DSL limites**: profondeur ≤ 6, payload ≤ 8 KB JSON.
- **RLS catalogue**: politique alternative `auth.role()='admin' OR (auth.role()='pme' AND status='published')`. Aucune route `/admin/*` exposée aux PME ; lecture indirecte via F23/F28.
- **Poids Référentiel**: somme exacte = 100 ± 0.01 au publish ; flag de normalisation hors-scope MVP.
- **Stockage value_type**: `numeric` et `percentage` en `DECIMAL(18,6)` (percentage borné [0..100]) ; boolean/enum/text en JSON.
- **Évaluateur Critère tri-state**: {true, false, undecidable}. `undecidable` + `blocking` → traité blocking par F25 ; `undecidable` + `warning|info` → ignoré.
- **Suppression**: hard delete autorisé sur `draft` seulement ; sinon archive (`status=archived`).
- **`formula_type=custom`**: accepté en stockage, non évalué MVP (F23 fallback `weighted_sum`) ; validateur publish exige seulement non-vacuité.
- **Statuts Indicateur**: `draft|published|archived|outdated` ; `outdated` automatique si source liée passe `rejected`.

## Dependencies

- **F04** — audit-log-versioning (audit append-only, versioning `publish_new_version` + `If-Match`).
- **F06** — back-office-skeleton (registry admin, ETag, crud_router, publish gate, scaffolding routes `/admin`).
- **F07** — catalog-sources-management (entité `Source` + statut `verified`).
- **F08** — catalog-fonds-intermediaires-offres (référence pour `owner_type=fonds|intermediaire|offre` dans Critères et Documents Requis).
