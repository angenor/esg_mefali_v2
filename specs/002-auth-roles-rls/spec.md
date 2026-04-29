# Feature Specification: Authentification & Rôles PME/Admin (Row-Level Security)

**Feature Branch**: `002-auth-roles-rls`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: F02 — Authentification & Rôles PME/Admin (Row-Level Security). Phase 0 — Fondations transversales. Module 0.2. Mettre en place l'authentification simple email + mot de passe, deux rôles seulement (PME et Admin), et l'isolation multi-tenant stricte via Row-Level Security PostgreSQL. Plateforme FERMÉE — aucun rôle Intermédiaire ou Banque.

## Clarifications

### Session 2026-04-29

- Q: Comment le jeton d'accès est-il transporté/stocké côté navigateur ? → A: Cookie httpOnly + Secure + SameSite=Strict (le frontend ne lit jamais le jeton ; CSRF mitigé par double-submit token sur les opérations modifiantes).
- Q: Durée de vie du jeton de renouvellement (TTL) ? → A: 30 jours, glissants à chaque rotation.
- Q: Politique de limitation de débit sur les endpoints d'authentification ? → A: 5 tentatives/minute/IP sur /auth/login et /auth/forgot-password ; 10 inscriptions/heure/IP sur /auth/register ; réponse 429 sans révéler l'état des comptes.
- Q: Durée de vie du jeton de réinitialisation de mot de passe ? → A: 30 minutes, à usage unique.
- Q: Modèle de rattachement du rôle Admin à un Account ? → A: Admin TOUJOURS avec account_id NULL ; bypass d'isolation strictement via mécanisme de session contrôlé par l'API.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inscription d'un nouveau compte PME (Priority: P1)

Une PME africaine francophone crée un compte via email + mot de passe afin de commencer à utiliser la plateforme. À l'inscription, un nouvel `Account` (tenant) est créé et un `AccountUser` rôle PME y est rattaché. La PME reçoit un jeton d'accès et un jeton de renouvellement, et peut immédiatement consulter son profil.

**Why this priority**: Sans inscription, aucun usage possible. C'est la porte d'entrée fonctionnelle de toute la plateforme.

**Independent Test**: Effectuer une requête d'inscription avec email valide + mot de passe conforme à la politique → vérifier qu'un Account et un AccountUser PME sont créés, qu'un jeton d'accès valide est retourné, et qu'une consultation du profil retourne les bonnes informations sans le hash du mot de passe.

**Acceptance Scenarios**:

1. **Given** un email valide non utilisé et un mot de passe ≥ 12 caractères avec maj/min/chiffre, **When** la PME s'inscrit, **Then** un Account + AccountUser PME sont créés et un jeton d'accès + un jeton de renouvellement sont retournés.
2. **Given** un email déjà enregistré, **When** une nouvelle inscription est tentée, **Then** la réponse est un conflit (HTTP 409) avec un message clair.
3. **Given** un mot de passe ne respectant pas la politique, **When** l'inscription est tentée, **Then** la réponse est une erreur de validation (HTTP 422) listant les règles non respectées.

---

### User Story 2 - Connexion email + mot de passe (Priority: P1)

Un utilisateur déjà enregistré (PME ou Admin) se connecte avec ses identifiants pour accéder à ses données. Les réponses d'erreur ne révèlent jamais si un email est connu ou non du système.

**Why this priority**: La connexion est la deuxième porte d'entrée critique : sans elle, aucun retour utilisateur n'est possible.

**Independent Test**: Créer un utilisateur, se déconnecter, puis se reconnecter avec les bons identifiants → recevoir un nouveau jeton d'accès + jeton de renouvellement et accéder aux données protégées. Tester aussi avec un mauvais mot de passe et un email inconnu et vérifier que les deux réponses sont indistinguables.

**Acceptance Scenarios**:

1. **Given** des identifiants valides, **When** l'utilisateur se connecte, **Then** un jeton d'accès (durée 24h) et un jeton de renouvellement rotatif sont retournés.
2. **Given** un mot de passe erroné, **When** la connexion est tentée, **Then** la réponse est 401 avec un message générique sans révéler si l'email existe.
3. **Given** un email inconnu, **When** la connexion est tentée, **Then** la réponse est strictement identique à celle d'un mot de passe erroné.

---

### User Story 3 - Isolation stricte entre comptes PME (Priority: P1)

Un utilisateur PME A ne peut jamais accéder, lister, modifier ou supprimer les données d'un autre compte PME B, même en injectant l'identifiant de B, même via des chemins atypiques. L'isolation est garantie au niveau de la base de données et pas seulement au niveau applicatif. Les tentatives de cross-account retournent 404 (et non 403) afin de ne pas révéler l'existence des données d'autrui.

**Why this priority**: C'est l'invariant central de confidentialité multi-tenant. Une fuite ici détruit la crédibilité de toute la plateforme.

**Independent Test**: Créer deux comptes PME A et B avec chacun des données métier (par exemple une entreprise). Depuis le compte A, tenter de consulter, modifier et supprimer la ressource de B en injectant son identifiant → toutes les opérations doivent renvoyer 404 ou 0 résultat. Lancer également une requête simulant un endpoint compromis (sans middleware) et vérifier que la base de données elle-même bloque l'accès.

**Acceptance Scenarios**:

1. **Given** deux comptes PME A et B avec une entreprise chacun, **When** le compte A demande l'entreprise de B par identifiant, **Then** la réponse est 404.
2. **Given** un endpoint listant les ressources, **When** A appelle l'endpoint, **Then** seules les ressources de A figurent dans la réponse, jamais celles de B.
3. **Given** une requête SQL exécutée sans contexte de compte, **When** elle est lancée par l'application, **Then** elle retourne 0 ligne (la couche base de données bloque).

---

### User Story 4 - Rôle Admin avec accès back-office (Priority: P1)

L'équipe ESG Mefali dispose d'un rôle Admin qui n'est rattaché à aucun Account et qui peut accéder aux endpoints du back-office (Module 9) pour maintenir le catalogue (Sources, Fonds, Intermédiaires, Offres, Référentiels, Skills). Un Admin ne peut pas créer de données métier d'une PME, il consulte et modère.

**Why this priority**: Sans Admin, le catalogue n'est pas maintenable et les fonctionnalités dépendantes (sourcing, scoring, matching, etc.) ne peuvent pas exister.

**Independent Test**: Créer manuellement un compte Admin (script seed/CLI), se connecter, accéder à un endpoint admin → succès. Avec un compte PME, accéder au même endpoint → 403. Tenter, depuis le compte Admin, de créer une donnée métier d'une PME → refus.

**Acceptance Scenarios**:

1. **Given** un compte Admin connecté, **When** il appelle un endpoint /admin/..., **Then** la réponse est 200.
2. **Given** un compte PME connecté, **When** il appelle un endpoint /admin/..., **Then** la réponse est 403.
3. **Given** un compte Admin, **When** il tente de créer une entreprise/projet/candidature au nom d'une PME, **Then** la requête est refusée.

---

### User Story 5 - Refresh token rotatif (Priority: P2)

Un utilisateur peut renouveler son jeton d'accès via un jeton de renouvellement, sans avoir à se reconnecter. Chaque utilisation du jeton de renouvellement le rotate (l'ancien est invalidé). En cas de réutilisation détectée, toute la chaîne de jetons est révoquée pour parer un éventuel vol.

**Why this priority**: Améliore l'expérience utilisateur (sessions longues) tout en conservant des jetons d'accès courts pour la sécurité. Important mais pas bloquant pour un MVP fonctionnel.

**Independent Test**: Récupérer un jeton de renouvellement à la connexion, l'utiliser pour obtenir un nouveau jeton d'accès → succès, l'ancien jeton de renouvellement est invalidé. Tenter de réutiliser l'ancien jeton de renouvellement → toute la chaîne est révoquée.

**Acceptance Scenarios**:

1. **Given** un jeton de renouvellement valide, **When** l'utilisateur le présente, **Then** un nouveau jeton d'accès et un nouveau jeton de renouvellement sont retournés et l'ancien est marqué utilisé.
2. **Given** un jeton de renouvellement déjà utilisé, **When** il est représenté, **Then** toute la chaîne de jetons est révoquée et la requête échoue.

---

### User Story 6 - Réinitialisation de mot de passe par email (Priority: P2)

Un utilisateur ayant oublié son mot de passe peut demander un lien de réinitialisation par email. Le lien contient un jeton à usage unique, expirant rapidement. La consommation du jeton permet de définir un nouveau mot de passe respectant la politique. La présence ou absence d'un compte associé à l'email demandé n'est jamais révélée.

**Why this priority**: Indispensable pour ne pas perdre d'utilisateurs en cas d'oubli, mais peut être livré juste après le cœur auth/RLS.

**Independent Test**: Demander une réinitialisation pour un email connu → email envoyé, jeton créé avec expiration courte. Consommer le jeton avec un nouveau mot de passe valide → connexion possible avec le nouveau mot de passe. Demander une réinitialisation pour un email inconnu → réponse identique au cas connu (pas de fuite).

**Acceptance Scenarios**:

1. **Given** un email enregistré, **When** une réinitialisation est demandée, **Then** un email contenant un jeton à usage unique avec expiration courte est envoyé et la réponse API est neutre.
2. **Given** un email inconnu, **When** une réinitialisation est demandée, **Then** la réponse API est strictement identique au cas connu (aucune fuite d'information).
3. **Given** un jeton de réinitialisation valide non expiré, **When** il est consommé avec un nouveau mot de passe conforme, **Then** le mot de passe est mis à jour, le jeton est invalidé et l'utilisateur peut se connecter.
4. **Given** un jeton expiré ou déjà consommé, **When** il est utilisé, **Then** la requête échoue.

---

### User Story 7 - Plusieurs utilisateurs d'un même Account ont des droits équivalents (Priority: P3)

Une PME ayant plusieurs collaborateurs voit chaque utilisateur de son Account disposer des mêmes droits sur les données partagées de l'entreprise (pas de RBAC granulaire en MVP).

**Why this priority**: Acceptable en MVP de n'avoir qu'un utilisateur par Account ; la pluralité est différée.

**Independent Test**: Créer un second AccountUser dans le même Account et vérifier qu'il accède aux mêmes données et opérations que le premier.

**Acceptance Scenarios**:

1. **Given** deux AccountUsers PME dans le même Account, **When** chacun consulte/modifie une ressource métier de l'Account, **Then** les deux ont strictement les mêmes droits.

### Edge Cases

- Inscription avec email valide mais mot de passe juste à la limite (12 caractères exact, ou exactement 11) → règle de longueur strictement appliquée.
- Connexion alors que la base est partiellement indisponible → erreur générique sans fuite, jamais de stack trace.
- Présentation d'un jeton d'accès expiré → 401 et invitation implicite à utiliser le jeton de renouvellement.
- Présentation d'un jeton d'accès dont le secret de signature ne correspond pas → 401.
- Tentative d'inscription Admin via l'endpoint public d'inscription → la création d'un Admin est impossible par cette voie.
- Requête métier sans en-tête d'authentification → 401 systématique avant toute logique applicative.
- Migration de schéma exécutée par un opérateur technique → la couche d'isolation ne doit pas bloquer les opérations de schéma (rôle technique distinct).
- Connexion directe d'un développeur à la base en superuser pour debug → l'isolation reste appliquée pour les requêtes de l'application, le bypass est strictement contrôlé via la couche application.
- Demande de réinitialisation de mot de passe répétée pour le même email en peu de temps → limitation de débit cohérente avec la politique générale.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer une opération d'inscription publique permettant de créer un Account et un AccountUser PME associé.
- **FR-002**: Le système DOIT exposer une opération de connexion par email + mot de passe retournant un jeton d'accès et un jeton de renouvellement.
- **FR-003**: Le système DOIT exposer une opération de renouvellement de jeton d'accès via le jeton de renouvellement.
- **FR-004**: Le système DOIT exposer une opération de déconnexion qui révoque le jeton de renouvellement courant.
- **FR-005**: Le système DOIT exposer une opération de consultation du profil de l'utilisateur courant retournant identifiant utilisateur, identifiant Account, rôle, email, date de création — sans jamais retourner le hash du mot de passe.
- **FR-006**: Le système DOIT stocker les mots de passe sous forme hachée avec un algorithme adaptatif éprouvé et un coût élevé ; jamais en clair.
- **FR-007**: Le système DOIT appliquer une politique de mot de passe minimale : longueur ≥ 12 caractères, présence d'au moins une majuscule, une minuscule et un chiffre.
- **FR-008**: Le système DOIT appliquer une rotation des jetons de renouvellement à chaque utilisation et révoquer en cascade toute la chaîne en cas de réutilisation détectée.
- **FR-009**: Le système DOIT garantir l'isolation multi-tenant au niveau de la base de données pour TOUTES les tables métier portant un identifiant de compte, de telle sorte qu'une requête sans contexte de compte ne retourne aucune ligne.
- **FR-010**: Le système DOIT positionner, à chaque requête authentifiée, le contexte de compte de l'utilisateur courant pour la durée de la transaction de base de données.
- **FR-011**: Le système DOIT autoriser le rôle Admin à accéder aux ressources de tous les Accounts en lecture (et en modification limitée au catalogue), via un mécanisme de bypass contrôlé positionné en début de transaction.
- **FR-012**: Le système DOIT empêcher la création publique d'un compte Admin ; seul un script/commande d'administration permet la création d'un Admin.
- **FR-013**: Le système DOIT refuser, depuis un compte PME, tout accès aux endpoints d'administration (réponse 403).
- **FR-014**: Le système DOIT empêcher un Admin de créer des données métier d'une PME (entreprises, projets, candidatures, etc.) ; il peut consulter et modérer.
- **FR-015**: Le système DOIT répondre 404 (et non 403) à toute tentative d'accès cross-Account afin de ne pas révéler l'existence de la ressource.
- **FR-016**: Le système DOIT répondre de façon strictement identique aux erreurs « email inconnu » et « mot de passe invalide » lors de la connexion.
- **FR-017**: Le système DOIT, côté frontend, protéger les pages authentifiées via un middleware vérifiant la présence et la validité du jeton d'accès et redirigeant vers la page de connexion sinon ; les pages d'administration sont en plus conditionnées au rôle Admin.
- **FR-018**: Le système DOIT exposer un endpoint de vérification de l'isolation, démontrant qu'une requête sans contexte de compte renvoie zéro ligne, accessible uniquement aux Admins (ou désactivé en production selon configuration).
- **FR-019**: Le système DOIT, en cas de migration de schéma, utiliser un rôle technique distinct du rôle applicatif, capable d'effectuer les modifications de schéma sans être empêché par les politiques d'isolation.
- **FR-020**: Le système DOIT exposer un mécanisme de réinitialisation de mot de passe par email avec jeton à usage unique de courte durée, et ne JAMAIS révéler l'existence ou non d'un compte associé à l'email demandé.
- **FR-021**: Le système NE DOIT PAS journaliser de mots de passe en clair, ni de jetons d'accès complets, ni de jetons de renouvellement complets.
- **FR-022**: Le système DOIT inscrire chaque tentative de connexion (succès/échec) et chaque opération sensible (création d'Account, création d'Admin, réinitialisation de mot de passe) au journal d'audit append-only avec source du changement.
- **FR-023**: Le système DOIT garantir que tout endpoint métier exige une authentification valide avant d'exécuter sa logique.
- **FR-024**: Le système DOIT permettre que plusieurs AccountUsers d'un même Account aient strictement les mêmes droits sur les données de cet Account (pas de RBAC granulaire en MVP).
- **FR-025**: Le système DOIT enregistrer la date de dernière connexion réussie pour chaque utilisateur.
- **FR-026**: Le système DOIT transporter le jeton d'accès via un cookie HTTP-only, Secure et SameSite=Strict ; le frontend ne lit jamais le jeton. Les opérations modifiantes sont protégées contre la falsification de requête inter-sites par un mécanisme double-submit (jeton CSRF complémentaire).
- **FR-027**: Le système DOIT donner au jeton de renouvellement une durée de vie de 30 jours, recalculée (glissante) à chaque rotation réussie.
- **FR-028**: Le système DOIT appliquer une limitation de débit : maximum 5 tentatives par minute et par IP sur la connexion et la demande de réinitialisation de mot de passe ; maximum 10 inscriptions par heure et par IP. En cas de dépassement, la réponse est 429 sans révéler l'état d'un compte particulier.
- **FR-029**: Le système DOIT donner au jeton de réinitialisation de mot de passe une durée de vie de 30 minutes et le rendre strictement à usage unique.
- **FR-030**: Le système DOIT garantir que tout AccountUser de rôle Admin a un identifiant de compte (`account_id`) nul ; le bypass de l'isolation s'effectue exclusivement par un mécanisme de session contrôlé par la couche d'API, jamais par appartenance à un Account particulier.

### Key Entities *(include if feature involves data)*

- **Account**: Tenant de la plateforme représentant une PME (ou nul/N-A pour les Admins). Porte l'isolation multi-tenant.
- **AccountUser**: Utilisateur enregistré avec email unique, hash de mot de passe, rôle (`PME` ou `Admin`), rattaché à un Account (sauf Admin). Conserve la date de création, de mise à jour et de dernière connexion.
- **RefreshToken**: Jeton de renouvellement persisté avec hash, date d'émission, date d'expiration, date d'utilisation, date de révocation, et lien vers le jeton parent (chaîne) pour permettre la détection de réutilisation et la révocation en cascade.
- **PasswordResetToken**: Jeton à usage unique pour réinitialisation de mot de passe, avec hash, date d'émission, date d'expiration courte, date de consommation, lien vers l'utilisateur cible.
- **AuditLogEntry** (réutilisé du Module 0) : Trace append-only de chaque action sensible avec source du changement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur un test d'isolation entre 2 comptes PME, 100 % des tentatives d'accès cross-Account (lecture, listing, modification, suppression) retournent un résultat équivalent à « ressource introuvable » ou un ensemble vide.
- **SC-002**: Sur la suite de tests d'authentification (inscription, connexion, renouvellement, déconnexion), 100 % des cas nominaux et d'erreurs spécifiés passent.
- **SC-003**: 100 % des endpoints métier exigent une authentification valide (audit automatisable des routes confirmant l'absence de fuite).
- **SC-004**: La création d'un compte Admin s'effectue en une seule commande administrative documentée.
- **SC-005**: Les réponses d'erreur de connexion pour « email inconnu » et « mot de passe invalide » sont strictement identiques (mêmes code, mêmes corps, mêmes en-têtes), vérifié par test automatisé.
- **SC-006**: Aucun mot de passe en clair, jeton d'accès complet ou jeton de renouvellement complet n'apparaît dans les journaux applicatifs (vérifié par scan automatisé).
- **SC-007**: Une suite de tests d'isolation dédiée couvre au minimum 5 scénarios distincts (lecture, listing, modification, suppression, requête sans contexte) et passe à 100 %.
- **SC-008**: Un utilisateur peut se connecter, obtenir un jeton, le renouveler et accéder à ses données en moins de 3 secondes au total dans des conditions nominales.
- **SC-009**: La réinitialisation de mot de passe est possible en moins de 2 minutes depuis la demande jusqu'à la connexion avec le nouveau mot de passe (hors latence de l'email lui-même).

## Assumptions

- L'authentification se fait par email + mot de passe ; pas de SSO, ni d'OAuth tiers, ni de magic link, ni de 2FA en MVP.
- La plateforme n'a que deux rôles applicatifs : `PME` et `Admin`. Aucun rôle Intermédiaire, Banque ou autre.
- Les Admins sont créés exclusivement par voie d'administration (script ou commande) ; l'inscription publique ne crée que des PME.
- La base de données cible offre un mécanisme natif d'isolation par ligne (Row-Level Security) capable de filtrer toutes les requêtes de l'application en fonction d'un contexte de session.
- La rotation des jetons de renouvellement est requise dès le MVP, le verrouillage de compte après N tentatives est différé.
- La réinitialisation de mot de passe par email est INCLUSE en MVP (option P2) sous forme minimale (jeton mailé à usage unique).
- Les emails transactionnels sont délivrables (un service d'envoi est disponible ou stubbable en environnement de dev).
- Les opérations de migration de schéma sont exécutées par un rôle technique distinct du rôle applicatif.
- Les sessions reposent sur des jetons (pas de session serveur) ; le frontend stocke le jeton d'accès de manière compatible avec la sécurité du navigateur (le mode exact est un détail d'implémentation).
- Les tests automatisés (unitaires, intégration, et end-to-end pour les flux critiques) couvrent au moins 80 % du code livré et incluent une suite dédiée à l'isolation.

## Dependencies

- F01 (fondations) : schéma Alembic 18 tables avec `account_id` NOT NULL sur les tables métier, backend et frontend en place.
- Module 0 — invariants : sourcing, multi-tenant, audit log append-only, versioning, Money typé, UI bottom sheet, plateforme fermée.

## Out of Scope (MVP)

- OTP SMS, magic link, authentification à deux facteurs (TOTP).
- RBAC granulaire intra-PME (Owner / Member / Viewer).
- SSO entreprise.
- OAuth providers tiers (Google, Microsoft, etc.).
- Verrouillage de compte après N tentatives infructueuses.
- Rotation du secret de signature des jetons sans interruption (transition douce).
