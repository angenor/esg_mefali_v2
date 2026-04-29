# Feature Specification: Profil Entreprise — édition manuelle synchronisée LLM

**Feature Branch**: `011-11-profile-entreprise`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F11 — Profil → Entreprise (édition manuelle, synchronisation bidirectionnelle avec le LLM).

## Contexte

L'entité **Entreprise** est le contexte porteur de la PME (1 par compte). Elle alimente le scoring crédit (F29) et la conformité ESG globale (F23). Cette feature livre la vue **Profil → Entreprise** où la PME peut consulter et éditer manuellement tous les champs, indépendamment du LLM. Le LLM enrichira via la Phase 3 (chat + tools de mutation), mais l'utilisateur doit pouvoir corriger, compléter ou écraser ce que le LLM a extrait. Une synchronisation bidirectionnelle est obligatoire.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Voir le profil de mon entreprise (Priority: P1)

En tant que PME, je veux une page `/profil/entreprise` qui affiche tous les champs de mon entreprise organisés par section (Identité, Activité, Localisation, Pratiques, Gouvernance), afin de comprendre quelles données sont stockées sur mon compte.

**Why this priority**: Sans visualisation, l'édition n'a pas de sens. C'est la pierre angulaire de toute la Phase 2 et conditionne toutes les features de scoring/matching aval (F23, F25, F29).

**Independent Test**: un compte fraîchement inscrit voit un formulaire vierge avec les sections définies. Un compte existant voit ses données déjà saisies, regroupées par section, lisible.

**Acceptance Scenarios**:

1. **Given** une PME nouvellement inscrite et authentifiée, **When** elle ouvre `/profil/entreprise`, **Then** la page affiche 5 sections (Identité, Activité, Localisation, Pratiques, Gouvernance) avec tous les champs vides ou aux valeurs par défaut, sans erreur.
2. **Given** une PME dont le profil a déjà été partiellement renseigné, **When** elle ouvre `/profil/entreprise`, **Then** chaque champ affiche sa valeur actuelle persistée et la page se charge en moins de 1 seconde.
3. **Given** un utilisateur non authentifié, **When** il tente d'accéder à `/profil/entreprise`, **Then** il est redirigé vers la page de login.

---

### User Story 2 — Éditer manuellement chaque champ (Priority: P1)

En tant que PME, je veux modifier directement chaque champ depuis l'UI (édition inline ou modale), avec validation côté client (formats, bornes), afin de corriger des erreurs ou compléter ce que le LLM a extrait.

**Why this priority**: Cœur métier de la feature — sans édition manuelle, la PME est prisonnière du LLM, ce qui contredit le contrat de la plateforme.

**Independent Test**: une PME peut modifier 5 champs distincts (texte, nombre, enum, money, country-iso2) et chaque modification est persistée durablement (visible après reload).

**Acceptance Scenarios**:

1. **Given** une PME sur `/profil/entreprise`, **When** elle saisit "75" dans le champ Effectifs et confirme, **Then** la valeur est validée client (entier 0–10000), persistée et un nouvel enregistrement audit log apparaît avec `source_of_change='manual'`.
2. **Given** la même PME, **When** elle tape "Agro" dans le champ Secteur, **Then** un autocomplete propose les secteurs taxonomiques (~50 entrées sourcées) et la sélection enregistre le `secteur_code` + `secteur_label`.
3. **Given** la même PME, **When** elle ouvre Localisation siège, **Then** un sélecteur n'expose que les pays UEMOA/CEDEAO (ISO2) et accepte une ville libre.
4. **Given** une PME qui saisit "-5" en Effectifs, **When** elle tente de sauvegarder, **Then** la validation client rejette la saisie avec un message clair, sans appel réseau.
5. **Given** une PME qui édite le champ Pratiques environnementales, **When** elle saisit du texte libre + sélectionne 2 tags suggérés, **Then** le `pratiques_actuelles_json` est persisté avec les deux dimensions.

---

### User Story 3 — Synchronisation bidirectionnelle avec le LLM (Priority: P1)

En tant que PME, je veux qu'une édition manuelle soit immédiatement reflétée dans le contexte LLM (au prochain message, le LLM voit la nouvelle valeur), et réciproquement, qu'une mutation LLM (via `update_company_profile`) actualise la page si je suis dessus, afin de ne jamais devoir répéter ce que j'ai déjà corrigé.

**Why this priority**: Garantit que LLM et UI sont la même source de vérité — sans cela, dérive immédiate et perte de confiance utilisateur.

**Independent Test**: après édition manuelle, le LLM (test d'intégration mock) reçoit la nouvelle valeur dans son contexte au prochain appel. Et inversement, mocker un `update_company_profile` LLM-side et vérifier la page reçoit l'événement.

**Acceptance Scenarios**:

1. **Given** une PME édite "Effectifs" de 50 → 75 manuellement, **When** elle envoie le prochain message dans le chat (F13), **Then** le contexte injecté au LLM contient `taille_effectifs=75`.
2. **Given** une PME ouverte sur `/profil/entreprise`, **When** le LLM appelle `update_company_profile` avec un nouveau CA "250M FCFA", **Then** la page se met à jour sans rechargement complet en moins de 1 seconde.
3. **Given** le serveur côté LLM, **When** une mutation est appliquée, **Then** un événement `account.{id}.entreprise.updated` est émis sur le canal de synchro temps réel.

---

### User Story 4 — Indicateur visuel de provenance (Priority: P2)

En tant que PME, je veux voir à côté de chaque champ d'où vient sa valeur (saisie manuelle, extrait par le LLM d'un document, déclaratif initial) afin de savoir où le LLM a "deviné" et où j'ai validé.

**Why this priority**: Fonctionnalité de confiance, peut être livrée juste après le MVP de US1+US2+US3.

**Independent Test**: 5 cas (manuel, LLM-extract-doc, LLM-mutation-tool, déclaratif initial, vide) → chacun affiche le bon badge et un clic révèle le mini-historique audit log.

**Acceptance Scenarios**:

1. **Given** un champ Secteur extrait du document statuts.pdf, **When** la PME visualise `/profil/entreprise`, **Then** le champ affiche un badge "Extrait du document statuts.pdf" + date.
2. **Given** un champ édité manuellement, **When** la PME visualise la page, **Then** le badge indique "Modifié manuellement le 14/03".
3. **Given** la PME clique sur le badge, **When** le mini-historique s'ouvre, **Then** elle voit l'audit log filtré sur ce champ (5 dernières mutations, ordre antéchronologique).

---

### User Story 5 — Champs obligatoires vs optionnels et complétude (Priority: P2)

En tant que PME, je veux voir un % de complétude de mon profil et savoir quels champs sont nécessaires pour débloquer telle ou telle feature aval, afin de prioriser ma saisie.

**Why this priority**: Augmente l'engagement et la qualité des données. Ne bloque pas le MVP mais améliore l'adoption.

**Independent Test**: un profil vide affiche 0%. Un profil renseigné aux 4/10 champs requis pour ESG affiche 40% pour cette feature et liste les 6 manquants.

**Acceptance Scenarios**:

1. **Given** une PME nouvellement inscrite, **When** elle ouvre la page, **Then** un indicateur global affiche 0% et liste les champs manquants.
2. **Given** une PME a renseigné Secteur + Effectifs (mais pas CA), **When** elle consulte la page, **Then** l'indicateur "ESG Scoring" affiche les champs requis encore manquants (CA).
3. **Given** la matrice des features-requises est mise à jour côté config, **When** une nouvelle feature est ajoutée, **Then** l'indicateur de complétude reflète sans changement de code.

---

### User Story 6 — Édition multi-utilisateurs sans conflit (Priority: P3)

En tant que collaborateur d'une PME (Module 7.3 — tous les users PME ont les mêmes droits), je veux que si 2 collègues éditent en même temps, on ne se marche pas dessus, afin de travailler sereinement.

**Why this priority**: Cas peu probable en MVP. Implémentation simple via optimistic concurrency.

**Independent Test**: deux clients chargent la même version, l'un soumet, l'autre soumet → le second reçoit 409 Conflict.

**Acceptance Scenarios**:

1. **Given** deux utilisateurs U1 et U2 du même compte chargent `/profil/entreprise` (version=3), **When** U1 sauvegarde puis U2 tente de sauvegarder avec If-Match=3, **Then** U2 reçoit 409 Conflict avec un message indiquant de recharger.
2. **Given** U2 recharge, **When** il refait son édition sur la version=4, **Then** la sauvegarde aboutit normalement.

---

### Edge Cases

- Tentative d'édition sans token / token expiré → 401, redirection login.
- Tentative d'écriture sur l'entreprise d'un autre compte → 403/404 (RLS PostgreSQL force `account_id`).
- `secteur_code` inconnu de la taxonomie → 422.
- Pays ISO2 hors UEMOA/CEDEAO → 422.
- Money avec devise hors {XOF, EUR, USD} → 422.
- Champs sensibles (CA, effectifs) ne doivent jamais apparaître en clair dans logs ou messages d'erreur.
- Édition concurrente avec deux PATCHes consécutifs → premier passe, second 409.
- Réception d'un événement `entreprise.updated` côté front pendant que l'utilisateur édite → l'édition en cours n'est pas écrasée silencieusement (banner "Recharger ?").
- Connexion temps réel coupée → fallback polling (5s) sans crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** — Modèle de données: la table `entreprise` (créée en F01) DOIT être enrichie avec `secteur_code`, `secteur_label`, `localisation_siege_pays_iso2`, `localisation_siege_ville`, `zones_operation_pays_iso2[]`, `gouvernance_json` (jsonb). Les champs existants `taille_ca_amount`, `taille_ca_currency`, `taille_effectifs`, `pratiques_actuelles_json`, `version` sont conservés.
- **FR-002** — Provenance via audit log: la provenance d'un champ DOIT être calculée à partir de l'audit_log (F04) en agrégeant le dernier `source_of_change` par champ. Aucune table dédiée à la provenance.
- **FR-003** — API REST :
  - `GET /me/entreprise` → renvoie le profil + métadonnées par champ (`{value, source_of_change, last_modified_at, last_modified_by}`).
  - `PUT /me/entreprise` → édition complète, exige `If-Match: <version>`, retourne 409 si stale.
  - `PATCH /me/entreprise` → édition partielle, mêmes règles d'optimistic concurrency.
  - Toute mutation génère un enregistrement audit_log avec `source_of_change='manual'` (US2) ou `'llm_tool'` (US3 réception).
- **FR-004** — Validation stricte au boundary: enum sectors (taxonomie maison ~50 entrées sourcée via F09), pays ISO2 limités à UEMOA/CEDEAO, money typé `{amount, currency}` avec devises {XOF, EUR, USD}, peg FCFA-EUR 655.957 (F05), bornes numériques (effectifs 0–10000).
- **FR-005** — Page UI `/profil/entreprise`: layout en sections déployables, édition inline pour les champs simples, modale (bottom-sheet sur mobile) pour les champs composés, indicateur de complétude global, badge de provenance par champ.
- **FR-006** — Synchronisation temps réel: canal `account.{id}.entreprise.updated` (Server-Sent Events MVP) + fallback polling 5s si SSE indisponible.
- **FR-007** — Endpoint complétude: `GET /me/entreprise/completeness` → `{percentage, missing_required_for_features:[{feature_code, missing_fields}]}`. La matrice features→champs DOIT être déclarative en config.
- **FR-008** — Optimistic concurrency: `version` int incrémenté à chaque mutation; client envoie `If-Match`; 409 si stale avec body `{current_version, your_version}`.
- **FR-009** — Multi-tenant RLS: lecture/écriture sur `entreprise` filtrée par RLS PostgreSQL via `account_id` (invariant Module 0).
- **FR-010** — Audit append-only: enregistrements audit_log liés à entreprise immuables (invariant Module 0).
- **FR-011** — Sourcing: les valeurs LLM-extract DOIVENT référencer une `source_id` (invariant Module 0).
- **FR-012** — Plateforme PME/Admin uniquement: aucune surface publique non authentifiée n'expose ces endpoints.

### Non-Functional Requirements

- **NFR-001**: édition d'un champ → persistance + invalidation cache LLM en moins de 500 ms (p95).
- **NFR-002**: chargement complet du formulaire en moins de 1 seconde (p95).
- **NFR-003**: validation côté front strictement identique à celle backend (schéma partagé / OpenAPI).
- **NFR-004**: aucun champ sensible (effectifs, CA) en clair dans logs ou messages d'erreur.
- **NFR-005**: synchro temps réel UI mise à jour en moins de 1 seconde après mutation côté serveur.

### Key Entities

- **Entreprise** (table existante en F01, enrichie) — porte tous les champs profil PME, lié 1:1 à `account` via `account_id` UNIQUE.
- **Audit Log** (F04) — utilisé pour la provenance par champ et l'historique.
- **Source** (F03) — référencée pour les valeurs LLM-extract.
- **Taxonomie sectorielle** — référentiel ~50 entrées géré via F09.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: une PME complète son profil entreprise (10 champs principaux) en moins de 5 minutes lors du premier passage.
- **SC-002**: après édition manuelle, le prochain tour de chat LLM voit la nouvelle valeur dans son contexte (test d'intégration end-to-end).
- **SC-003**: après mutation LLM, l'UI ouverte se met à jour en moins de 1 seconde (p95) sans rechargement.
- **SC-004**: badges de provenance corrects sur 5 cas tests (manuel, LLM-extract-doc, LLM-tool, déclaratif initial, jamais saisi).
- **SC-005**: zéro fuite cross-account sur 1000 requêtes de scan automatisé (test RLS).
- **SC-006**: zéro régression sur les tests pré-existants des features 01–10.

## Assumptions

- L'authentification (F02) et le système de rôles PME/Admin sont déjà en place.
- L'audit_log (F04) supporte déjà `source_of_change` enum incluant `manual` et `llm_tool` (à vérifier ; ajouter sinon en migration).
- La table `entreprise` créée en F01 peut être enrichie via migration alembic non destructive (ajout de colonnes nullable).
- Le chat LLM (F13–F18) est la source des mutations LLM côté serveur — F11 expose seulement le canal de réception et l'API.
- La taxonomie sectorielle est gérée via F09 — F11 consomme un endpoint d'autocomplete (ou liste de codes statique en MVP si F09 n'a pas encore livré l'endpoint d'autocomplete).
- Pays UEMOA/CEDEAO : sous-ensemble fixe d'ISO2 (~15 pays) défini en config.
- Server-Sent Events (SSE) préférés au WebSocket pour MVP.
- L'indicateur de complétude consomme une config déclarative (`features_required_fields.yaml` ou équivalent) versionnée.
- La devise par défaut pour `taille_ca` est XOF avec peg fixe 655.957 FCFA = 1 EUR.
- Tests manuels (E2E navigateur) listés mais joués hors session.
