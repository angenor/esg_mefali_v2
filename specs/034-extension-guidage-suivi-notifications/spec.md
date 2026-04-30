# Feature Specification: F34 — Extension Chrome — Guidage, Suivi Candidatures, Notifications, Recommandations

**Feature Branch**: `034-extension-guidage-suivi-notifications`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F34 — Extension Chrome — Panneau de Guidage, Suivi Candidatures, Notifications, Recommandations. Backend MVP minimal: endpoints suivi candidatures (GET /me/candidatures + status PATCH), notifications (table notification + GET/PATCH read sur /me/notifications), recommandations basiques."

## Clarifications

### Session 2026-04-29

- Q: Liste canonique des `kind` de notification en MVP ? → A: enum fermé `deadline_j_minus_30`, `deadline_j_minus_7`, `deadline_j_minus_1`, `candidature_inactive`, `offre_recommandee`.
- Q: Source du score de recommandation ? → A: service F25 si disponible (`MatchingService.score_offre_for_pme`), sinon score=0.0 et tri par fonds source compatible.
- Q: Pagination sur GET /me/candidatures ? → A: pas de pagination en MVP, slice serveur hard `LIMIT 200`.
- Q: Transitions de statut candidature ? → A: transitions libres entre les 5 valeurs autorisées (pas de FSM stricte).
- Q: Dérivation de `progression_pct` ? → A: `snapshot_json["progression_pct"]` si entier 0-100, sinon 0.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Suivi des candidatures actives via l'extension (Priority: P1)

En tant que PME utilisant l'extension Chrome, je veux consulter, depuis le popup ou le panneau,
la liste de mes candidatures en cours, leur statut courant et leur dernière mise à jour, afin de
savoir où j'en suis sans devoir ouvrir la plateforme.

**Why this priority**: C'est la fonction la plus critique pour la valeur de l'extension côté
suivi : sans la liste des candidatures, le reste (recommandations, notifications) perd son ancrage.

**Independent Test**: Avec un compte PME possédant 3 candidatures à différents statuts, appeler
`GET /me/candidatures` retourne ces 3 lignes triées par mise à jour décroissante avec leur
statut courant et leur identifiant Offre.

**Acceptance Scenarios**:

1. **Given** une PME authentifiée avec 2 candidatures non supprimées, **When** elle interroge la
   liste de ses candidatures, **Then** elle reçoit exactement ces 2 candidatures avec champs
   `id`, `projet_id`, `offre_id`, `statut`, `updated_at`, `progression_pct`.
2. **Given** une PME avec 0 candidature, **When** elle interroge la liste, **Then** elle reçoit
   une liste vide (pas d'erreur).
3. **Given** une candidature `deleted_at` non NULL, **When** la PME interroge la liste, **Then**
   cette candidature n'apparaît pas.
4. **Given** une PME A, **When** elle tente de lire les candidatures alors qu'une autre PME B en
   possède, **Then** elle ne voit que les siennes (isolation tenant via RLS).

---

### User Story 2 — Mise à jour du statut d'une candidature (Priority: P1)

En tant que PME, je veux pouvoir mettre à jour manuellement le statut de ma candidature
(`brouillon`, `soumise`, `en_instruction`, `acceptee`, `refusee`), depuis l'extension ou la
plateforme, afin de garder mon suivi à jour sans dépendre d'un parsing email.

**Why this priority**: Sans mise à jour de statut, la liste reste figée et les notifications
ne peuvent pas réagir aux transitions.

**Independent Test**: Une PME passe une candidature de `brouillon` à `soumise` via PATCH ; un
GET ultérieur reflète le nouveau statut, et un audit log est écrit.

**Acceptance Scenarios**:

1. **Given** une candidature en `brouillon` appartenant à la PME, **When** elle envoie
   `PATCH /me/candidatures/{id}/status` avec `{statut: "soumise"}`, **Then** la candidature
   est en `soumise`, `updated_at` est rafraîchi, `version` est incrémenté.
2. **Given** une candidature appartenant à une autre PME, **When** la PME courante tente le
   PATCH, **Then** elle reçoit une réponse 404 (isolation).
3. **Given** un statut inconnu (ex. `archivee`), **When** la PME envoie le PATCH, **Then** elle
   reçoit une réponse 422 expliquant les valeurs autorisées.
4. **Given** un PATCH valide, **Then** une ligne `audit_log` est ajoutée avec
   `entity_type=candidature`, `field=statut`, ancienne et nouvelle valeur,
   `source_of_change=manual`.

---

### User Story 3 — Centre de notifications PME (Priority: P1)

En tant que PME, je veux consulter la liste de mes notifications récentes (échéances proches,
candidatures inactives, recommandations) et marquer une notification comme lue, afin de gérer
mon attention.

**Why this priority**: La création des notifications côté serveur précède toute UI/push. Le
centre de notifications est la base sur laquelle les futures alertes Chrome (push,
déduplication) viendront se brancher.

**Independent Test**: Insérer 2 notifications pour une PME, l'une lue et l'autre non. Le GET
retourne les 2, marquées correctement, triées par date décroissante. PATCH read sur l'une
modifie son flag.

**Acceptance Scenarios**:

1. **Given** une PME avec 3 notifications (2 non lues, 1 lue), **When** elle interroge
   `GET /me/notifications`, **Then** elle reçoit les 3 avec leur flag `read_at`, triées par
   `created_at` décroissant.
2. **Given** elle filtre `?unread=true`, **Then** elle ne reçoit que les 2 non lues.
3. **Given** une notification non lue lui appartenant, **When** elle envoie
   `PATCH /me/notifications/{id}/read`, **Then** `read_at` est positionné à maintenant et la
   notification n'apparaît plus dans le filtre `unread`.
4. **Given** une notification appartenant à une autre PME, **When** elle tente le PATCH,
   **Then** elle reçoit 404.

---

### User Story 4 — Recommandations d'Offres compatibles depuis l'URL courante (Priority: P1)

En tant que PME naviguant sur un site fonds (ex. gcf.org), je veux que l'extension demande au
backend les Offres compatibles avec mon profil et l'URL courante, afin de choisir le meilleur
intermédiaire.

**Why this priority**: La détection d'URL est livrée en F33 ; F34 livre l'endpoint qui retourne
les Offres recommandées de base, point d'ancrage du panneau latéral.

**Independent Test**: Pour une PME donnée, appeler `GET /me/extension/offres-recommandees?url=https://www.gcf.org`
retourne au moins une Offre triée par compatibilité (au minimum les Offres dont le fonds est lié
à l'URL fournie).

**Acceptance Scenarios**:

1. **Given** une PME avec un projet et un fonds source `GCF` détecté pour l'URL `gcf.org`,
   **When** elle appelle l'endpoint avec cette URL, **Then** elle reçoit la liste des Offres
   `GCF×Intermédiaire_n` triée par `score` décroissant (au moins une).
2. **Given** une URL inconnue (aucun pattern), **When** elle appelle l'endpoint, **Then** elle
   reçoit une liste vide et un statut 200 (pas d'erreur).
3. **Given** une URL absente du paramètre, **When** elle appelle l'endpoint, **Then** elle
   reçoit une réponse 422.

---

### Edge Cases

- Une candidature est créée puis supprimée logiquement (`deleted_at`) : elle n'apparaît plus dans
  la liste, et tout PATCH renvoie 404.
- Une notification a un `entity_id` pointant sur une candidature supprimée : elle reste
  consultable mais son lien devient inerte (le client ne plante pas).
- Plus de 100 notifications pour une PME : pagination via `limit`/`offset`, défaut `limit=50`.
- Un PATCH read concurrent sur la même notification : idempotent, second PATCH n'écrase pas
  `read_at` initial.
- Une URL avec query string ou fragments arbitraires : la résolution se fait sur l'autorité
  (host) puis chemin canonisé.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer `GET /me/candidatures` qui retourne la liste des
  candidatures non supprimées appartenant à la PME courante (filtrage RLS), triée par
  `updated_at` décroissant, avec champs : `id`, `projet_id`, `offre_id`, `statut`,
  `progression_pct` (lue dans `snapshot_json["progression_pct"]` si entier 0-100, sinon 0),
  `updated_at`, `created_at`. Pas de pagination en MVP, mais le serveur applique un
  `LIMIT 200` en garde-fou.
- **FR-002**: Le système DOIT exposer `PATCH /me/candidatures/{id}/status` qui accepte
  `{statut: "brouillon" | "soumise" | "en_instruction" | "acceptee" | "refusee"}`, valide
  l'appartenance, rejette les valeurs hors liste (422), met à jour la candidature et
  enregistre une ligne d'audit (champ `statut`, ancienne et nouvelle valeur,
  `source_of_change=manual`). Toute transition entre les 5 valeurs autorisées est
  acceptée (pas de FSM stricte en MVP) ; l'audit log conserve la traçabilité.
- **FR-003**: Le système DOIT créer une table `notification` (account_id, user_id nullable,
  kind, title, body, entity_type, entity_id, payload_json, read_at, created_at, updated_at,
  version, deleted_at) avec RLS PME (lecture/écriture sur `account_id` courant) et index
  `(account_id, created_at DESC)`. La colonne `kind` est contrainte à l'enum MVP :
  `deadline_j_minus_30`, `deadline_j_minus_7`, `deadline_j_minus_1`,
  `candidature_inactive`, `offre_recommandee`.
- **FR-004**: Le système DOIT exposer `GET /me/notifications?unread=&limit=&offset=` qui
  retourne les notifications de la PME courante triées par `created_at` décroissant ;
  `unread=true` filtre `read_at IS NULL` ; `limit` défaut 50 max 200, `offset` défaut 0.
- **FR-005**: Le système DOIT exposer `PATCH /me/notifications/{id}/read` qui valide
  l'appartenance, positionne `read_at = now()` si NULL (idempotent), retourne 404 si la
  notification n'appartient pas à la PME ou est supprimée.
- **FR-006**: Le système DOIT exposer `GET /me/extension/offres-recommandees?url=...` qui
  retourne au plus 10 Offres compatibles avec l'URL et le profil PME, triées par score
  décroissant. Un paramètre `url` est obligatoire (422 sinon). En l'absence de pattern
  matché, la réponse est une liste vide (200). Le score est calculé via le service de
  matching F25 (`MatchingService.score_offre_for_pme`) lorsque disponible ; sinon `score=0.0`
  est retourné et le tri se fait simplement par fonds source compatible (best-effort).
- **FR-007**: Tous les endpoints DOIVENT exiger l'authentification PME (rôle `pme`) et
  être inutilisables par un compte admin via ces routes (admin a son périmètre).
- **FR-008**: Toute mutation (status candidature, notification read) DOIT être journalisée
  via `record_audit` avec `source_of_change=manual` et `entity_id` correspondant.
- **FR-009**: Le seed DOIT insérer un service interne (`NotificationService.create_for_account`)
  pour permettre aux autres modules (échéances, recommandations, dossiers) de créer des
  notifications sans dupliquer la logique de RLS/audit.
- **FR-010**: Les statuts de candidatures hors liste blanche DOIVENT être rejetés ; la liste
  de référence est `brouillon`, `soumise`, `en_instruction`, `acceptee`, `refusee`. Toute
  autre valeur génère une réponse 422.

### Key Entities *(include if feature involves data)*

- **Candidature** *(existante, non modifiée par F34)* : `id`, `account_id`, `projet_id`,
  `offre_id`, `statut`, `snapshot_json`, `version`, `updated_at`. F34 ajoute uniquement la
  lecture/mutation via API.
- **Notification** *(nouvelle table)* : représente une alerte ou information adressée à une
  PME (échéance proche, candidature inactive, recommandation).
  - Attributs : `id` (UUID), `account_id` (FK account), `user_id` (FK account_user nullable —
    cible un utilisateur précis sinon le compte entier), `kind` (texte court ; ex.
    `deadline_j_minus_30`, `candidature_inactive`, `offre_recommandee`), `title` (texte),
    `body` (texte), `entity_type` / `entity_id` (lien optionnel vers candidature/offre),
    `payload_json` (extensions), `read_at` (TIMESTAMP nullable), colonnes communes (`version`,
    `created_at`, `updated_at`, `deleted_at`).
  - Politique RLS : la PME lit/écrit ses lignes (`account_id` courant) ; admin lit toutes.

## Success Criteria *(mandatory)*

- **SC-001**: Une PME peut consulter sa liste de candidatures et la voir refléter en moins
  d'une seconde après chaque mise à jour de statut.
- **SC-002**: 100 % des transitions de statut effectuées via l'API génèrent une ligne d'audit
  consultable côté admin.
- **SC-003**: Une PME ne peut jamais voir, lire ou modifier une candidature ou notification
  d'une autre PME (taux de fuite mesuré 0 % sur jeu de tests d'isolation).
- **SC-004**: Le centre de notifications retourne les notifications les plus récentes en
  premier dans 100 % des cas testés.
- **SC-005**: L'endpoint de recommandations retourne au moins une Offre lorsque l'URL pointe
  vers un fonds source actif et que la PME a un projet ; il retourne une liste vide sans
  erreur lorsque l'URL est inconnue.

## Assumptions

- L'authentification PME, la RLS, le helper `record_audit` et la table `candidature` sont
  livrés par les features antérieures (F02, F04, F25). F34 réutilise sans les modifier.
- La table existante `candidature` ne reçoit pas de nouvelle colonne en F34 ; la persistance
  fine du `form_data` détaillée par US5 du brainstorm est différée (post-MVP).
- Le panneau de guidage UI, le mini-chat embarqué, la création automatique de candidature au
  remplissage du formulaire et les notifications push Chrome (chrome.notifications,
  chrome.alarms) sont reportés en post-MVP. F34 livre uniquement les fondations backend
  (tables, endpoints, audit, RLS).
- La logique de matching avancée (scores décomposés F25) est réutilisée si disponible ; sinon
  un tri simple par fonds source compatible est suffisant pour le MVP.
- La pagination sur les notifications utilise des paramètres `limit`/`offset` (cohérent avec
  les conventions existantes du backend).
- La création de notifications par d'autres modules (échéances, recommandations) est différée :
  F34 ne fournit que le service `NotificationService.create_for_account` mais ne pose pas de
  job planifié.

## Out of Scope (MVP F34)

- Panneau latéral HTML/CSS de guidage et navigateur d'étapes.
- Mini-chat IA contextuel embarqué dans l'extension.
- Création automatique d'une candidature lorsqu'un formulaire est détecté.
- Sauvegarde de progression `form_data` côté backend (`PATCH /candidatures/{id}/progress`).
- Push notifications via `chrome.notifications.create` et cycle `chrome.alarms` 6h.
- Comparateur côte-à-côte d'Offres dans un modal popup.
- Email parsing (Gmail/Outlook OAuth).
