# Phase 1 — Data Model : F52

**Feature** : Notifications, Paramètres, Exports & Panneau d'extension
**Date** : 2026-05-05

Toutes les tables nouvelles portent `account_id UUID NOT NULL` + politique RLS standard `USING (account_id = current_setting('app.current_account_id')::uuid)` (P2). Toute mutation (sauf `last_ping_at`) écrit dans `audit_log` (P3).

---

## Tables nouvelles

### `notification_preference`

Préférences utilisateur par couple (kind, canal). Consultée par le pipeline d'envoi de notifications avant chaque émission.

| Colonne | Type | Contraintes | Notes |
|---------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | |
| `account_id` | `UUID` | NOT NULL, FK `account` | RLS |
| `user_id` | `UUID` | NOT NULL, FK `account_user` | |
| `kind` | `notification_kind` (enum partagé F38) | NOT NULL | `deadline_j_minus_30`, `deadline_j_minus_7`, `deadline_j_minus_1`, `candidature_inactive`, `offre_recommandee`, `system`, etc. |
| `channel` | `notification_channel` enum | NOT NULL | `email`, `in_app` |
| `enabled` | `BOOLEAN` | NOT NULL, default `TRUE` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |

Contraintes : `UNIQUE (user_id, kind, channel)`. Index : `(account_id, user_id)`.

Comportement : à la première lecture, le service auto-instancie les rows manquants à `enabled=true` pour fournir une vue complète au front. Mutation par batch via `PATCH /me/notification-preferences`.

---

### `account_deletion_request`

Demande de suppression de compte avec délai de grâce de 30 jours.

| Colonne | Type | Contraintes | Notes |
|---------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `account_id` | `UUID` | NOT NULL, FK `account` | RLS |
| `user_id` | `UUID` | NOT NULL, FK `account_user` | initiateur |
| `requested_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |
| `scheduled_for` | `TIMESTAMPTZ` | NOT NULL | calculé `requested_at + interval '30 days'` |
| `status` | `deletion_status` enum | NOT NULL, default `pending` | `pending`, `cancelled`, `executed` |
| `reason_motif` | `TEXT` | NULL | motif libre optionnel |
| `confirmation_text` | `TEXT` | NOT NULL | preuve = raison sociale exacte saisie |
| `cancelled_at` | `TIMESTAMPTZ` | NULL | |
| `executed_at` | `TIMESTAMPTZ` | NULL | |

Contraintes : `UNIQUE (account_id) WHERE status = 'pending'` (au plus une requête active par compte). Index : `(status, scheduled_for)` pour le job de purge.

Transitions : `pending → cancelled` (par l'utilisateur), `pending → executed` (par le job de purge), aucune autre transition.

---

### `extension_ping`

Présence et version de l'extension détectée pour un utilisateur.

| Colonne | Type | Contraintes | Notes |
|---------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `account_id` | `UUID` | NOT NULL, FK `account` | RLS |
| `user_id` | `UUID` | NOT NULL, FK `account_user` | |
| `extension_version` | `TEXT` | NOT NULL | semver `0.x.y` |
| `user_agent_summary` | `TEXT` | NULL | nom + version navigateur, normalisé |
| `last_ping_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |

Contraintes : `UNIQUE (user_id)` (UPSERT à chaque ping). Index : `(account_id, last_ping_at)`.

---

### `export_artifact` *(si non préexistant — sinon étendu)*

Historique des exports/rapports générés pour `/dashboard/exports`.

| Colonne | Type | Contraintes | Notes |
|---------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `account_id` | `UUID` | NOT NULL, FK `account` | RLS |
| `user_id` | `UUID` | NOT NULL, FK `account_user` | générateur |
| `type` | `export_type` enum | NOT NULL | `rgpd_full`, `report_pdf`, `attestation_pdf`, `dossier_pdf`, etc. |
| `format` | `TEXT` | NOT NULL | `pdf`, `json` |
| `size_bytes` | `BIGINT` | NULL | renseigné post-génération |
| `status` | `export_status` enum | NOT NULL, default `pending` | `pending`, `ready`, `expired`, `failed` |
| `signed_url` | `TEXT` | NULL | non journalisé en clair en audit |
| `signed_url_expires_at` | `TIMESTAMPTZ` | NULL | par défaut `created_at + 7 j` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |
| `ready_at` | `TIMESTAMPTZ` | NULL | |
| `delivered_via` | `TEXT` | NULL | `inapp` \| `email` (bascule > 100 Mo) |

Index : `(account_id, created_at DESC)`. RLS appliquée.

---

## Tables existantes — augmentations

### `account_user_session` *(à confirmer / créer si absent)*

Si la table de sessions n'existe pas encore avec révocation par-session, ajouter `revoked_at TIMESTAMPTZ NULL` et l'index `(user_id, revoked_at)`. Le middleware d'auth lit ce flag et invalide la requête si présent.

### `account_user.email_pending`

Ajouter (si absent) :

- `email_pending TEXT NULL` — adresse en attente de vérification.
- `email_verification_token_hash TEXT NULL`
- `email_verification_sent_at TIMESTAMPTZ NULL`

L'ancien `email` reste actif jusqu'à confirmation. Audit log à chaque transition.

---

## Enums introduits

```sql
CREATE TYPE notification_channel AS ENUM ('email', 'in_app');
CREATE TYPE deletion_status AS ENUM ('pending', 'cancelled', 'executed');
CREATE TYPE export_type AS ENUM ('rgpd_full', 'report_pdf', 'attestation_pdf', 'dossier_pdf');
CREATE TYPE export_status AS ENUM ('pending', 'ready', 'expired', 'failed');
```

`notification_kind` est l'enum **déjà** introduit par F38 ; F52 ne le redéfinit pas.

---

## Politiques RLS (gabarit appliqué à toutes les tables nouvelles)

```sql
ALTER TABLE notification_preference ENABLE ROW LEVEL SECURITY;
CREATE POLICY notification_preference_tenant ON notification_preference
  USING (account_id = current_setting('app.current_account_id')::uuid)
  WITH CHECK (account_id = current_setting('app.current_account_id')::uuid);

-- idem pour account_deletion_request, extension_ping, export_artifact
```

Le rôle applicatif a `INSERT, SELECT, UPDATE` sur toutes ces tables sauf `audit_log` (INSERT only — P3).

---

## Audit (P3)

| Action | `entity` | `field` | `source_of_change` |
|--------|----------|---------|---------------------|
| Modification profil | `account_user` | `name`, `photo_url`, `language` | `manual` |
| Demande de modification e-mail | `account_user` | `email_pending` | `manual` |
| Validation e-mail | `account_user` | `email` | `manual` |
| Mise à jour préférence notifications | `notification_preference` | `enabled` | `manual` |
| Retrait consent | `consent` | `withdrawn_at` | `manual` |
| Révocation session | `account_user_session` | `revoked_at` | `manual` |
| Demande suppression compte | `account_deletion_request` | `status` | `manual` |
| Annulation suppression | `account_deletion_request` | `status` | `manual` |
| Exécution suppression | `account_deletion_request` | `status` | `system` |
| Génération export | `export_artifact` | `status` | `manual` |

---

## Migration Alembic — fichier unique

`backend/alembic/versions/0XXX_f52_notification_preferences_account_deletion_extension_ping.py` :

1. Crée enums `notification_channel`, `deletion_status`, `export_type`, `export_status`.
2. Crée tables `notification_preference`, `account_deletion_request`, `extension_ping`, `export_artifact`.
3. Active RLS + policies.
4. ALTER `account_user` ADD COLUMN `email_pending`, `email_verification_token_hash`, `email_verification_sent_at` (nullable, pas de backfill).
5. ALTER `account_user_session` ADD COLUMN `revoked_at` si absent.

Reversibilité : `downgrade()` drop dans l'ordre inverse, sans data-loss safeguard (migration récente, pas de prod).
