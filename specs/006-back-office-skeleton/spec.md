# Feature Specification: F06 — Squelette Back-Office Admin & Workflow draft → published

**Feature Branch**: `006-back-office-skeleton`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: F06 — Squelette Back-Office Admin & Workflow draft → published (Phase 1 — Back-office Admin & Catalogue ; Modules 9.1 ; Dépendances F02, F03)

## Context & Goal

Le back-office est le poumon de la plateforme : sans lui, personne ne peut peupler le catalogue (Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Templates, Facteurs d'émission, Skills) et la plateforme reste une coquille vide.

Cette feature livre **le cadre commun** réutilisé par toutes les features de catalogue qui suivent (F07 à F10, F20) :

- Layout admin séparé du frontend PME (`/admin/*`).
- Workflow standardisé `draft → published` (un objet n'est `published` que si toutes ses sources sont `verified`).
- Composants CRUD réutilisables (formulaire, liste paginée, badge de statut, indicateur de version).
- Garde d'accès basée sur le rôle Admin (F02).

Pas de logique métier propre à un type d'objet ici — c'est un squelette. Mais il doit être assez robuste pour porter 8+ types de catalogue.

## Clarifications

### Session 2026-04-29

- Q: Concurrency control for simultaneous draft edits by two admins → A: If-Match (ETag) optimistic locking, reusing F04 publish_new_version pattern.
- Q: Pagination contract for `/admin/{entity}/` list endpoints → A: Cursor-based — `?limit=N&cursor=opaque` returning `{items, next_cursor, total_estimate}`.
- Q: Refresh strategy for `GET /admin/stats/catalog` → A: Live recompute on each call (no cache) for MVP.
- Q: Search algorithm for `GET /admin/search?q=` → A: ILIKE/trigram on indexed text fields (name, publisher, external_id), top 10 per type.
- Q: localStorage draft auto-save cadence and scope → A: Debounce 1.5 s on change; scoped per `(entity_type, entity_id|new, user_id)`; cleared on save/discard; confirmation on resume.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Layout admin distinct accessible aux admins (Priority: P1)

En tant qu'admin ESG Mefali, je veux qu'après login, le menu de navigation me propose un accès "Back-office" (ou je suis directement redirigé), avec un layout dédié (sidebar des sections : Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Facteurs d'émission, Templates, Skills, PME, Métriques), afin de travailler dans un contexte dédié.

**Why this priority**: Sans cet accès, aucune autre feature back-office n'est utilisable. C'est la porte d'entrée du module Admin et le pré-requis pour F07-F10, F20.

**Independent Test**: Un admin se connecte et accède à `/admin` ; il voit la sidebar avec les sections vides. Un user PME tentant la même URL reçoit 403 et est redirigé.

**Acceptance Scenarios**:

1. **Given** un compte avec rôle `admin`, **When** l'utilisateur visite `/admin`, **Then** il voit le layout admin avec sidebar et header dédiés.
2. **Given** un compte avec rôle `pme`, **When** l'utilisateur visite `/admin`, **Then** il reçoit 403 et est redirigé vers la racine PME.
3. **Given** un visiteur non authentifié, **When** il visite `/admin`, **Then** il est redirigé vers la page de login.

---

### User Story 2 - Workflow draft → published standardisé (Priority: P1)

En tant qu'admin, je veux que chaque objet du catalogue ait un cycle de vie commun : création en `draft`, édition libre tant qu'en `draft`, bouton "Publier" qui vérifie que toutes les sources liées sont `verified` (sinon erreur explicite listant les sources manquantes), et une fois `published`, modifier l'objet crée une nouvelle version (F04) — l'ancienne reste accessible.

**Why this priority**: C'est le cœur du contrat back-office : sans ce workflow, l'invariant "toute donnée publiée est sourcée et vérifiée" (F03) ne tient plus, et le versioning immuable (F04) n'est pas exploité.

**Independent Test**: Sur une entité de démonstration (Indicateur), créer un draft sans source vérifiée, tenter de publier → refus 422 listant les sources manquantes ; ajouter une source vérifiée, publier → succès, statut `published`. Éditer après publication → création v2 avec confirmation.

**Acceptance Scenarios**:

1. **Given** un Indicateur en `draft` sans source vérifiée, **When** l'admin clique sur "Publier", **Then** le bouton est désactivé avec tooltip "1 source en attente de vérif" et l'API retourne 422 avec liste des sources `pending`.
2. **Given** un Indicateur en `draft` avec toutes ses sources `verified`, **When** l'admin clique sur "Publier", **Then** le statut passe à `published`, l'objet devient consommable par le LLM et un événement est écrit dans `audit_log`.
3. **Given** un Indicateur `published`, **When** l'admin tente une modification, **Then** une confirmation "Ceci créera la version v2 — continuer ?" s'affiche, et la sauvegarde crée une nouvelle version immuable via le mécanisme F04.

---

### User Story 3 - Composants CRUD réutilisables (Priority: P1)

En tant que dev frontend, je veux des composants Vue génériques `<AdminListPage>`, `<AdminFormPage>`, `<StatusBadge>`, `<VersionTimeline>` afin de ne pas réécrire le même CRUD 10 fois.

**Why this priority**: Ces composants sont la fondation réutilisée par F07, F08, F09, F10, F20. Sans eux, chaque feature catalogue rejoue le même code, multiplie les bugs et casse la cohérence visuelle.

**Independent Test**: Brancher les 4 composants sur une entité de démonstration ; vérifier la liste paginée, le formulaire, le badge de statut et la timeline des versions. Vérifier qu'ils restent agnostiques du type d'entité (props seulement).

**Acceptance Scenarios**:

1. **Given** une entité de démo avec 75 enregistrements, **When** la liste est rendue via `<AdminListPage>`, **Then** la pagination s'active à partir de 50 lignes, les filtres et actions fonctionnent.
2. **Given** une entité en `published`, **When** on rend `<StatusBadge :status="published">`, **Then** la couleur verte définie par la palette admin est appliquée (jaune=draft, vert=published, gris=outdated, orange=pending).
3. **Given** une entité avec 3 versions, **When** on rend `<VersionTimeline>`, **Then** la liste verticale affiche `version, valid_from, valid_to, published_by` pour chaque version.

---

### User Story 4 - Toutes les actions admin sont auditées (Priority: P1)

En tant que compliance, je veux que toute mutation faite via le back-office soit journalisée dans `audit_log` (F04) avec `source_of_change='admin'` et `user_id` = l'admin, afin de tracer qui a publié quoi.

**Why this priority**: Audit append-only est un invariant Module 0. Sans ce câblage côté back-office, la conformité est rompue dès qu'un admin agit.

**Independent Test**: Effectuer une création, une mise à jour, une publication via `/admin/*`, puis interroger `audit_log` et vérifier la présence de 3 entrées avec `source_of_change='admin'` et le bon `user_id`.

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il effectue une création/modification/publication via le back-office, **Then** une entrée `audit_log` est ajoutée avec `source_of_change='admin'`, `user_id`, `entity_type`, `entity_id`, `action`.
2. **Given** une mutation back-office qui échoue (ex. publish refusé), **When** la transaction est annulée, **Then** aucune entrée incohérente n'est ajoutée à `audit_log`.

---

### User Story 5 - Recherche transversale dans le catalogue (Priority: P2)

En tant qu'admin, je veux une barre de recherche globale qui cherche dans tous les types d'objets du catalogue (par nom, publisher, ID), afin de retrouver rapidement un objet sans cliquer dans 10 menus.

**Why this priority**: Confort opérationnel à mesure que le catalogue grossit. Pas bloquant pour l'amorçage mais nécessaire dès qu'il y a >100 objets.

**Independent Test**: Saisir un terme dans la barre globale ; vérifier que les résultats sont groupés par type d'entité avec une limite de 10 par type.

**Acceptance Scenarios**:

1. **Given** un catalogue contenant Sources, Indicateurs, Fonds, **When** l'admin tape un terme partiel, **Then** les résultats s'affichent groupés par type, max 10 par type.

---

### User Story 6 - Indicateur de complétude par section (Priority: P2)

En tant qu'admin, je veux voir sur la sidebar le nombre d'objets `draft`, `published` et `pending verification` par section, afin de savoir où il reste du travail.

**Why this priority**: Aide à la priorisation opérationnelle — non bloquant mais améliore l'efficacité quotidienne.

**Independent Test**: Charger la sidebar, vérifier les compteurs ; ajouter un draft via API, recharger, vérifier que le compteur draft a augmenté de 1.

**Acceptance Scenarios**:

1. **Given** la sidebar admin chargée, **When** la requête `/admin/stats/catalog` répond, **Then** chaque section affiche `{draft, published, pending}` à jour.

---

### Edge Cases

- Que se passe-t-il si un objet `published` voit l'une de ses sources passer à `outdated` après publication ? L'objet reste publié mais doit être affiché avec un indicateur visuel (à raffiner avec F23) — F06 conserve le statut tel quel et n'invalide pas rétroactivement.
- Que se passe-t-il si la connexion réseau tombe pendant la saisie d'un formulaire de 30 minutes ? Le brouillon est conservé en localStorage ; à la reprise, l'utilisateur reçoit une confirmation avant écrasement.
- Que se passe-t-il si deux admins éditent le même objet `draft` simultanément ? Le second à sauvegarder reçoit un conflit If-Match (réutilise le mécanisme F04 publish_new_version).
- Que se passe-t-il si la publication échoue à mi-transaction (ex. coupure DB) ? La transaction est annulée, aucune entrée audit n'est créée, le statut reste `draft`.
- Comportement du middleware si la session Postgres ne peut pas poser `app.is_admin = true` ? La requête est rejetée avec 500 et un log d'erreur (RLS doit rester garante).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La route `/admin` MUST passer par un middleware vérifiant `role === 'admin'`. Sinon 403.
- **FR-002**: Le système MUST fournir un layout dédié `layouts/admin.vue` avec sidebar permanente, header simple, breadcrumbs.
- **FR-003**: Le frontend MUST exposer un composable `useEntityCrud<T>(entityName)` couvrant `list`, `get`, `create`, `update`, `publish`, `getVersions`, lié aux endpoints REST conventionnels :
  - `GET /admin/{entity}/`
  - `GET /admin/{entity}/{id}`
  - `POST /admin/{entity}/`
  - `PUT /admin/{entity}/{id}`
  - `POST /admin/{entity}/{id}/publish`
  - `GET /admin/{entity}/{id}/versions`
- **FR-004**: L'endpoint `POST /admin/{entity}/{id}/publish` MUST :
  - vérifier que toutes les sources liées sont `verified` (sinon 422 avec liste des sources manquantes),
  - passer le statut à `published`,
  - écrire une entrée dans `audit_log` (F04) avec `source_of_change='admin'`.
- **FR-005**: Le système MUST fournir un composant `<StatusBadge>` à 4 variantes visuelles (draft=jaune, published=vert, outdated=gris, pending=orange).
- **FR-006**: Le système MUST fournir un composant `<VersionTimeline>` qui appelle `/admin/{entity}/{id}/versions` et rend la liste verticale `version, valid_from, valid_to, published_by`.
- **FR-007**: L'endpoint `GET /admin/search?q=` MUST retourner des résultats groupés par type d'entité (limit 10 par type).
- **FR-008**: L'endpoint `GET /admin/stats/catalog` MUST retourner un objet `{section: {draft:N, published:N, pending:N, ...}}` pour la sidebar.
- **FR-009**: F06 MUST se limiter aux rails — pas de CRUD complet par type d'entité (livré par F07, F08, F09, F10, F20).
- **FR-010**: Toutes les routes `/admin/*` MUST passer par un middleware backend qui pose `app.is_admin = true` dans la session Postgres pour la durée de la requête (cohérence avec RLS F02).
- **FR-011**: Toute mutation back-office (create/update/publish) MUST écrire une entrée `audit_log` avec `source_of_change='admin'` et `user_id` de l'admin authentifié ; en cas d'échec applicatif, la transaction MUST être rollbackée intégralement.
- **FR-012**: Le formulaire admin MUST conserver un brouillon en localStorage durant la saisie et présenter une confirmation avant écrasement à la reprise.
- **FR-013**: Toute édition d'un objet `published` MUST déclencher une confirmation utilisateur explicite et créer une nouvelle version immuable via le mécanisme F04 (publish_new_version + If-Match).
- **FR-014**: Les endpoints `PUT /admin/{entity}/{id}` et `POST /admin/{entity}/{id}/publish` MUST appliquer un contrôle de concurrence optimiste via en-tête `If-Match` (ETag = version courante). Conflit → 412 Precondition Failed avec la version serveur.
- **FR-015**: Les endpoints `GET /admin/{entity}/` MUST utiliser une pagination cursor-based : query params `?limit=N&cursor=opaque` ; réponse `{items, next_cursor, total_estimate}`. `limit` MUST être borné (défaut 50, max 200).
- **FR-016**: `GET /admin/stats/catalog` MUST recalculer les compteurs à chaque appel (pas de cache) pour le MVP ; latence cible <500 ms pour un catalogue jusqu'à 10 000 objets.
- **FR-017**: `GET /admin/search?q=` MUST exécuter une recherche ILIKE/trigram sur les champs indexés `name`, `publisher`, `external_id` de chaque entité ; max 10 résultats par type ; aucune dépendance aux embeddings (réservé à F23+).
- **FR-018**: Le formulaire admin MUST auto-sauvegarder le brouillon en localStorage avec debounce 1,5 s, scope `(entity_type, entity_id|new, user_id)` ; vidage à la sauvegarde réussie ou au discard explicite ; à la reprise, confirmation si une version serveur plus récente existe.

### Non-Functional Requirements

- **NFR-001**: Le back-office MUST tenir 100+ admins simultanés sans dégradation observable. Pagination obligatoire à partir de 50 lignes.
- **NFR-002**: Le formulaire admin MUST fonctionner offline-friendly (localStorage de brouillon).
- **NFR-003**: Aucun composant admin MUST utiliser une couleur du design system PME — palette dédiée (sobre, dense d'information, pas d'animations gsap).
- **NFR-004**: Accessibilité clavier complète sur listes et formulaires (Tab, Enter, Esc).

### Key Entities

- Aucune nouvelle table introduite par F06. Réutilise :
  - Colonne `status ENUM('draft','published','outdated','pending')` posée par F01 sur les tables catalogue.
  - Mécanisme de versions de F04 (`publish_new_version`, If-Match, `valid_from`/`valid_to`).
  - `audit_log` de F04 (append-only).
  - `sources_verified` de F03 (gate de publication).
  - Rôle `admin` et RLS de F02.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un admin avec son login peut accéder à `/admin`, voit la sidebar et peut ouvrir une section (la liste sera peuplée par F07+).
- **SC-002**: Un user PME tentant `/admin` reçoit 403 et est redirigé en moins d'une seconde.
- **SC-003**: Le composant `<AdminListPage>` est utilisé par au moins 2 features de catalogue ultérieures (F07, F08 ou F09) sans réécriture.
- **SC-004**: `POST /admin/{entity}/{id}/publish` rejette avec 422 si une source liée est `pending` et liste explicitement les sources manquantes.
- **SC-005**: 100% des mutations back-office (create/update/publish) sont retrouvables dans `audit_log` avec `source_of_change='admin'`.
- **SC-006**: La pagination s'active automatiquement à partir de 50 lignes ; un test charge 75 lignes et vérifie le découpage.
- **SC-007**: La barre de recherche globale retourne des résultats groupés par type avec au plus 10 résultats par type.

## Out of Scope

- CRUD spécifique aux Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Facteurs d'émission, Templates, Skills, PME → F07, F08, F09, F10, F20.
- Métriques admin avancées (volumes, coûts LLM) → F10.
- Bulk actions (publish multiple, import CSV) → post-MVP.
- Workflow d'approbation à 4 yeux supplémentaire (la double-validation F03 des Sources reste la seule).
- Internationalisation des libellés admin (français MVP).

## Assumptions

- Les rôles `admin` et `pme` ainsi que la table `users` et le mécanisme d'auth sont disponibles via F02.
- Les colonnes `status` et le contrat de versioning sont disponibles via F01 et F04.
- La notion de source vérifiée est gérée par F03 et exposée via une colonne ou table relationnelle exploitable côté FastAPI.
- Le frontend Nuxt 4 expose déjà un layout `default.vue` PME ; F06 ajoute `admin.vue` sans modifier `default.vue`.
- Le back-office est livré en français uniquement pour le MVP.
- Au moins une entité de démonstration (Indicateur) est utilisée pour valider le pattern de versioning avant généralisation (point d'attention F04).
- Le design system PME et la palette admin sont distincts ; aucune fuite CSS entre layouts.

## Risks & Watchpoints

- **Couplage fort avec F04 (versioning)** : si F04 n'est pas solide, F06 va l'amplifier. Vérifier le pattern de versioning sur 1 entité (Indicateur) avant de le généraliser.
- **Nuxt 4 layouts** : bien séparer `layouts/admin.vue` et `layouts/default.vue` pour éviter les fuites CSS.
- **`status='draft'` sur les sources** : un objet du catalogue qui dépend d'une source `pending` ne peut pas être `published`. Cette règle est centrale et doit être testée explicitement.

## Dependencies

- **F02** — auth-roles-rls (rôle admin, RLS multi-tenant, session Postgres).
- **F03** — source-anti-hallucination (sources verified, gate publication).
- **F04** — audit-log-versioning (audit append-only, publish_new_version, If-Match).
- **F01** — foundations-stack-init (colonne status, schémas catalogue).
