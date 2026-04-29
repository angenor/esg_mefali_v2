# Data Model — F02 Authentification & RLS

**Date**: 2026-04-29
**Feature**: 002-auth-roles-rls

## Vue d'ensemble

F02 modifie 1 table existante (`account_users`) et crée 2 nouvelles tables (`refresh_tokens`, `password_reset_tokens`). Aucune nouvelle entité métier. La principale opération de schéma est l'**activation de RLS** sur toutes les tables `account_id NOT NULL` créées en F01.

## Entité 1 : `account_users` (modifiée)

Table existante (F01). Ajouts :

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `role` | `account_user_role` (enum) | NOT NULL, DEFAULT `'pme'` | `'pme'` ou `'admin'`. |
| `last_login_at` | `timestamptz` | NULL | Date de dernière connexion réussie. |

Modifications :
- `account_id` reste `uuid`. Pour les Admins, `account_id IS NULL` (il faut **lever** la contrainte NOT NULL existante de F01 sur cette colonne pour les admins, ou utiliser un `account_id` réservé "system" — décision : passer `account_id` en NULL-able sur cette table seule, avec contrainte CHECK : `(role = 'pme' AND account_id IS NOT NULL) OR (role = 'admin' AND account_id IS NULL)`).
- `email` : conserver `UNIQUE` (déjà présent en F01).
- `password_hash` : conserver (déjà présent).

Enum SQL :
```sql
CREATE TYPE account_user_role AS ENUM ('pme', 'admin');
```

## Entité 2 : `refresh_tokens` (nouvelle)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | `uuid` | PK, DEFAULT `gen_random_uuid()` | Identifiant interne. |
| `user_id` | `uuid` | NOT NULL, FK → `account_users(id)` ON DELETE CASCADE | Utilisateur cible. |
| `token_hash` | `text` | NOT NULL, UNIQUE | SHA-256 hex du token clair. |
| `parent_id` | `uuid` | NULL, FK → `refresh_tokens(id)` ON DELETE SET NULL | Token précédent dans la chaîne de rotation. |
| `issued_at` | `timestamptz` | NOT NULL, DEFAULT `now()` | Date d'émission. |
| `expires_at` | `timestamptz` | NOT NULL | `issued_at + 30 days`. |
| `used_at` | `timestamptz` | NULL | Date de rotation (consommation). |
| `revoked_at` | `timestamptz` | NULL | Date de révocation explicite (logout, reset password, détection vol). |
| `revoked_reason` | `text` | NULL | `'logout'` \| `'reuse_detected'` \| `'password_reset'` \| `'admin'`. |

Index :
- `idx_refresh_tokens_user_id ON (user_id)`.
- `idx_refresh_tokens_active ON (user_id) WHERE used_at IS NULL AND revoked_at IS NULL AND expires_at > now()` — usage : invalidations en masse.

Cycle de vie :
- **Émission** : login ou refresh successful → ligne créée, `used_at = NULL`, `revoked_at = NULL`.
- **Rotation normale** : ligne marquée `used_at = now()`, nouvelle ligne créée avec `parent_id` = ancien id.
- **Détection de vol** : présentation d'un token avec `used_at IS NOT NULL` → toute la chaîne (parcourue récursivement via `parent_id` dans les deux sens) marquée `revoked_at = now(), revoked_reason = 'reuse_detected'`.
- **Logout** : token courant marqué `revoked_at = now(), revoked_reason = 'logout'`.
- **Reset password** : tous les tokens actifs de l'utilisateur révoqués `'password_reset'`.

RLS : cette table n'a pas de `account_id` direct. La policy se base sur `user_id` :
```sql
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY refresh_tokens_owner ON refresh_tokens
  USING (
    current_setting('app.is_admin', true)::bool IS TRUE
    OR user_id = current_setting('app.current_user_id', true)::uuid
  );
```
Le middleware positionne aussi `app.current_user_id` lors de chaque requête authentifiée.

## Entité 3 : `password_reset_tokens` (nouvelle)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | `uuid` | PK, DEFAULT `gen_random_uuid()` | Identifiant interne. |
| `user_id` | `uuid` | NOT NULL, FK → `account_users(id)` ON DELETE CASCADE | Utilisateur cible. |
| `token_hash` | `text` | NOT NULL, UNIQUE | SHA-256 hex du token clair envoyé par email. |
| `issued_at` | `timestamptz` | NOT NULL, DEFAULT `now()` | Date d'émission. |
| `expires_at` | `timestamptz` | NOT NULL | `issued_at + 30 minutes`. |
| `consumed_at` | `timestamptz` | NULL | Date d'utilisation (devient invalide). |

Index :
- `idx_password_reset_tokens_user_id ON (user_id)`.

RLS : même politique que `refresh_tokens` (par `user_id`).

## Activation RLS sur tables F01 `account_id NOT NULL`

Pour chaque table métier créée en F01 ayant `account_id NOT NULL` (entreprises, projets, candidatures, documents, indicateur_values, scoring_runs, …) :

```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <t>
  USING (
    current_setting('app.is_admin', true)::bool IS TRUE
    OR account_id = current_setting('app.current_account_id', true)::uuid
  )
  WITH CHECK (
    current_setting('app.is_admin', true)::bool IS TRUE
    OR account_id = current_setting('app.current_account_id', true)::uuid
  );
```

Le `WITH CHECK` empêche un utilisateur d'INSERT/UPDATE une ligne avec un `account_id` autre que le sien.

## Rôles SQL

```sql
-- Rôle applicatif : RLS appliquée
CREATE ROLE app_user LOGIN PASSWORD '<env>';
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- Rôle de migration : BYPASS RLS
CREATE ROLE migrator LOGIN PASSWORD '<env>';
GRANT USAGE, CREATE ON SCHEMA public TO migrator;
GRANT ALL ON ALL TABLES IN SCHEMA public TO migrator;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO migrator;
ALTER ROLE migrator BYPASSRLS;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT ALL ON TABLES TO migrator;
```

## Settings de session PostgreSQL utilisés

| Setting | Valeur | Positionné par |
|---------|--------|----------------|
| `app.current_account_id` | UUID de l'`Account` de l'utilisateur courant | Middleware FastAPI au début de chaque requête PME authentifiée. |
| `app.current_user_id` | UUID de l'`AccountUser` courant | Middleware (toujours, PME ou Admin). |
| `app.is_admin` | `'true'` ou absent | Middleware si `role == 'admin'`. |

Toujours via `SET LOCAL` dans la transaction (purge automatique en fin de tx).

## Audit Log

Réutilise `audit_log_entries` (F01). Événements F02 ajoutés (cf. research D-009). Aucune nouvelle colonne nécessaire ; le `event_type` discrimine.
