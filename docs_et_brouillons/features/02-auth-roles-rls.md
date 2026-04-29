# F02 — Authentification & Rôles PME/Admin (Row-Level Security)

**Phase** : 0 — Fondations transversales
**Modules brainstorm** : 0.2 (Authentification et Rôles)
**Dépendances** : F01
**Estimation** : 2 jours

## Contexte et objectif

Mettre en place l'authentification simple email + mot de passe, deux rôles seulement (`PME` et `Admin`), et **l'isolation multi-tenant stricte** via Row-Level Security PostgreSQL. Aucune feature métier ne doit pouvoir contourner cette isolation : un utilisateur PME ne voit jamais les données d'une autre PME, point.

Les intermédiaires accrédités ne sont **pas** des utilisateurs de la plateforme — ils reçoivent les dossiers et attestations hors-plateforme. Aucun rôle `Intermediaire` n'existe.

## User Stories

### US1 — Inscription d'un nouveau compte PME (P1)
**En tant que** PME africaine francophone,
**je veux** créer un compte avec email + mot de passe,
**afin de** commencer à utiliser la plateforme.

**Test indépendant** : POST `/auth/register` crée un nouvel `Account` + un `AccountUser` rôle `PME`, renvoie un JWT valide. La PME peut ensuite appeler `/me` et récupérer son profil.

**Scénarios** :
1. Email valide + mot de passe ≥ 12 caractères → inscription OK, retour JWT + refresh token.
2. Email déjà utilisé → 409 Conflict avec message clair.
3. Mot de passe faible → 422 avec règles affichées.

### US2 — Connexion email + mot de passe (P1)
**En tant qu'**utilisateur enregistré (PME ou Admin),
**je veux** me connecter avec mes identifiants,
**afin de** accéder à mes données.

**Scénarios** :
1. Identifiants valides → JWT (24h) + refresh token rotatif.
2. Mauvais mot de passe → 401, sans révéler si l'email existe.
3. Compte verrouillé après N tentatives → 423 (post-MVP optionnel).

### US3 — Isolation stricte entre comptes PME (P1)
**En tant que** garant de la confidentialité,
**je veux** qu'un utilisateur PME A qui appelle `GET /entreprises/{id}` avec l'id de l'entreprise de PME B reçoive 404 (pas 403, pour ne pas révéler l'existence),
**afin de** garantir l'isolation multi-tenant absolue.

**Test indépendant** : créer 2 comptes, créer une entreprise sur chacun, vérifier que le compte A ne peut jamais lister/lire/modifier/supprimer les données du compte B, même via injection d'ID, même via SQL brut depuis un endpoint compromis (RLS bloque au niveau Postgres).

### US4 — Rôle Admin avec accès back-office (P1)
**En tant qu'**équipe ESG Mefali,
**je veux** un rôle `Admin` qui n'est pas isolé par `account_id` et peut accéder au back-office (Module 9),
**afin de** maintenir le catalogue (Sources, Fonds, Intermédiaires, Offres, Référentiels, Skills).

**Scénarios** :
1. Admin se connecte → JWT avec claim `role=admin`, peut appeler les endpoints `/admin/...`.
2. PME tente d'appeler `/admin/...` → 403.
3. Admin **ne peut pas** créer de données métier (entreprises, projets, candidatures) — il consulte/modère.

### US5 — Refresh token rotatif (P2)
**En tant qu'**utilisateur,
**je veux** que mon JWT (24h) puisse être renouvelé via un refresh token,
**afin de** ne pas avoir à me reconnecter trop souvent.

**Scénarios** :
1. POST `/auth/refresh` avec refresh token valide → nouveau JWT + nouveau refresh token (l'ancien est invalidé).
2. Refresh token réutilisé → invalidation de toute la chaîne (détection de vol de token).

### US6 — Tous les utilisateurs d'une PME ont des droits équivalents (P3)
**En tant que** PME avec plusieurs collaborateurs,
**je veux** que chaque utilisateur de mon `Account` ait les mêmes droits sur les données partagées de l'entreprise,
**afin de** ne pas avoir à gérer de la finesse RBAC en MVP (post-MVP).

## Exigences fonctionnelles

- **FR-001** : Endpoints `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/me`.
- **FR-002** : Mots de passe hashés avec bcrypt (cost ≥ 12).
- **FR-003** : JWT signé HS256 (ou RS256), durée 24h, claim minimum `{sub: user_id, account_id, role}`.
- **FR-004** : Refresh tokens stockés en DB, rotation à chaque usage, révocation en cascade en cas de réutilisation détectée.
- **FR-005** : Row-Level Security activée sur **toutes les tables métier** ayant `account_id`. Politique : `USING (account_id = current_setting('app.current_account_id')::uuid)`.
- **FR-006** : Middleware FastAPI qui, à chaque requête authentifiée, fait `SET LOCAL app.current_account_id = '{account_id}'` dans la transaction Postgres.
- **FR-007** : Pour les Admins, une politique RLS permissive ou un bypass via `SET LOCAL app.is_admin = true` + politique `USING (current_setting('app.is_admin')::bool OR account_id = …)`.
- **FR-008** : Le rôle Admin se crée **manuellement en DB** (script seed ou commande CLI) — pas d'inscription publique d'admin.
- **FR-009** : Les pages frontend protégées par middleware Nuxt qui vérifie le JWT et redirige vers `/login` sinon. Les pages admin protégées en plus par check `role === 'admin'`.
- **FR-010** : Endpoint `/me` renvoie `{user_id, account_id, role, email, created_at}` — pas le password_hash, jamais.
- **FR-011** : Un endpoint de test `/admin/_rls_check` (non-prod ou protégé) qui prouve qu'une requête sans `account_id` set retourne 0 ligne — pour valider que RLS est bien activée.

## Exigences non-fonctionnelles

- **NFR-001** : Politique de mot de passe minimum : 12 caractères, présence d'au moins 1 maj/min/chiffre. Pas de blocklist de mots de passe communs en MVP.
- **NFR-002** : Réponses uniformes sur les erreurs d'auth (même status code et message pour "email inconnu" et "mauvais mot de passe") pour ne pas révéler la base.
- **NFR-003** : RLS doit fonctionner même quand un dev se connecte directement à la DB en superuser pour debug — l'app applique le bypass uniquement via l'API.
- **NFR-004** : Pas de logs des mots de passe en clair, pas de logs des JWT entiers, pas de logs des refresh tokens.

## Entités clés

- **AccountUser** étendue : `id, account_id (NULL pour admins), email UNIQUE, password_hash, role ENUM('pme','admin'), created_at, updated_at, last_login_at`.
- **RefreshToken** : `id, user_id, token_hash, issued_at, expires_at, used_at NULL, revoked_at NULL, parent_id NULL` (chaîne pour détecter vol).

## Success Criteria

- **SC-001** : Test d'isolation : 2 comptes créés, 100% des tentatives de cross-account retournent 404 ou 0 résultat.
- **SC-002** : Test d'auth : login + use JWT + refresh + use new JWT — 100% green sur la suite de tests.
- **SC-003** : Aucun endpoint métier n'expose de données sans middleware d'auth (audité par grep des routes FastAPI).
- **SC-004** : Le seed admin fonctionne en une commande (`python -m backend.scripts.seed_admin --email ... --password ...`).

## Hors-scope MVP (post-MVP)

- OTP SMS, magic link, 2FA TOTP.
- RBAC granulaire (Owner / Member / Viewer) intra-PME.
- SSO entreprise.
- OAuth providers (Google, Microsoft).
- Verrouillage de compte après N tentatives.
- Réinitialisation mot de passe par email — **OUI en MVP simple** (FR-012 si vous le souhaitez, sinon différé).
  → **À clarifier** : on inclut ou pas un endpoint `/auth/forgot-password` ? Suggestion : oui, MVP minimal avec token mailé.

## Risques et points de vigilance

- **RLS et migrations** : Alembic doit pouvoir tourner avec un user qui bypass RLS (rôle dédié `migrator`), sinon `ALTER TABLE` échoue. Définir clairement les rôles Postgres (`app_user`, `migrator`).
- **RLS et requêtes Admin** : ne pas confondre "Admin a un account_id NULL" et "Admin bypasse RLS via setting". Le pattern recommandé : `account_id NULL` + politique RLS `USING (current_setting('app.is_admin','f')::bool OR account_id = ...)`.
- **JWT secret rotation** : prévoir une variable `JWT_SECRET_PREVIOUS` pour transition douce sans déconnecter tout le monde (post-MVP).
- **Tests** : impératif d'avoir une suite de tests dédiée RLS (au moins 5 cas) — sans elle, n'importe quelle feature future peut casser l'isolation sans qu'on s'en aperçoive.
