# Phase 1 — Data Model

## Nouvelles tables

### `llm_usage_log`

| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| account_id | UUID | FK accounts(id), NULL autorisé (calls hors-tenant), index |
| user_id | UUID | FK users(id), NULL autorisé, index |
| model | TEXT | NOT NULL (ex. `minimax-m2.7`) |
| prompt_tokens | INTEGER | NOT NULL, CHECK >= 0 |
| completion_tokens | INTEGER | NOT NULL, CHECK >= 0 |
| latency_ms | INTEGER | NOT NULL, CHECK >= 0 |
| status | TEXT | NOT NULL, CHECK IN ('ok', 'retry', 'fallback', 'error') |
| created_at | TIMESTAMPTZ | NOT NULL, default now(), index BRIN |

**RLS**: admin lit tout. PME lit uniquement `account_id = current_account_id()`.

### `llm_pricing`

| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| model | TEXT | NOT NULL, index |
| prompt_per_1k_amount | NUMERIC(20,6) | NOT NULL, Money.amount |
| prompt_per_1k_currency | TEXT | NOT NULL, Money.currency (ex. `USD`) |
| completion_per_1k_amount | NUMERIC(20,6) | NOT NULL |
| completion_per_1k_currency | TEXT | NOT NULL |
| valid_from | TIMESTAMPTZ | NOT NULL |
| valid_to | TIMESTAMPTZ | NULL (open-ended) |
| created_by | UUID | FK users(id), NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

**Index unique partiel**: `(model)` WHERE `valid_to IS NULL` (une seule ligne ouverte par modèle).

**RLS**: admin only.

### `email_delivery_log`

| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| kind | TEXT | NOT NULL, CHECK IN ('reset_password', 'attestation_revoked', 'attestation_regenerated', 'support_notification') |
| recipient_user_id | UUID | FK users(id), NOT NULL, index |
| account_id | UUID | FK accounts(id), NULL autorisé |
| status | TEXT | NOT NULL, CHECK IN ('queued', 'sent', 'failed', 'bounced') |
| retries | INTEGER | NOT NULL, default 0 |
| last_attempt_at | TIMESTAMPTZ | NULL |
| provider_message_id | TEXT | NULL |
| last_error | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

**RLS**: admin only (ne pas exposer aux PME — bruit opérationnel).

## Colonnes ajoutées sur tables existantes

### `attestations` (table existante F30/F06)

| Colonne | Type | Contraintes |
|---|---|---|
| revoked_at | TIMESTAMPTZ | NULL |
| revoked_by | UUID | FK users(id), NULL |
| revoked_reason | TEXT | NULL, CHECK length >= 10 quand revoked_at NOT NULL |

Trigger ou contrainte applicative : un UPDATE révocation doit remplir simultanément les trois colonnes.

## Réutilisation `audit_log` (F04)

Aucune modification de schéma. Nouveaux usages :

- `entity_type='admin_view'`, `section ∈ {dashboard, projets, candidatures, scores, attestations, llm, audit}` (stocké dans `meta` jsonb si besoin).
- `entity_type='user'`, `action='reset_password_request'`, `source_of_change='admin'`.
- `entity_type='attestation'`, `action='revoke' | 'regenerate'`, `source_of_change='admin'`.
- `entity_type='admin_action'`, `action='mutation_refused'` quand un endpoint admin reçoit une mutation hors whitelist (audit "tentative refusée").

## Validation rules

- `LlmPricing.valid_from < valid_to` quand les deux non null.
- `EmailDeliveryLog.retries ∈ [0, 3]` (post-3 = `failed`).
- `attestations.revoked_reason` longueur ≥ 10 caractères si présent.

## State transitions

### Reset password token

```
created (TTL 1h, status=active)
  → consumed (one-shot, used_at filled)
  → expired (TTL passed without consumption)
```

### Email delivery

```
queued → sent (final OK)
       → failed (3 retries dépassés)
       → bounced (provider webhook)
```

### Attestation revocation

```
issued → revoked (revoked_at, revoked_by, revoked_reason filled)
       (idempotent : seconde révocation refusée 409)
```

## Indexes additionnels recommandés

- `accounts(email gist trigram)`, `accounts(raison_sociale gist trigram)` pour recherche admin.
- `audit_log(entity_id, entity_type)` quand `entity_type='admin_view'` (lecture côté PME).
- `llm_usage_log(account_id, created_at)`.
- `llm_usage_log(created_at)` BRIN.
