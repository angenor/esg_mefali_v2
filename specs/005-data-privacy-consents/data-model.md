# Phase 1 — Data Model : F05

## Enum partagés

```python
# app/core/currencies.py
class Currency(str, Enum):
    XOF = "XOF"
    EUR = "EUR"
    USD = "USD"
    GHS = "GHS"
    NGN = "NGN"
    MAD = "MAD"
    GBP = "GBP"

PEG_FCFA_EUR: Decimal = Decimal("655.957")
```

```python
# app/schemas/consent.py
class ConsentKind(str, Enum):
    MOBILE_MONEY = "mobile_money"
    EXPLOITATION_PHOTOS = "exploitation_photos"
    PUBLIC_ATTESTATION = "public_attestation"
    LONG_HISTORY = "long_history"
    MARKETING = "marketing"
```

## Table `consent`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `account_id` | UUID | NOT NULL, FK `account(id)` ON DELETE CASCADE |
| `consent_kind` | TEXT | NOT NULL, CHECK ∈ enum `ConsentKind` |
| `given` | BOOL | NOT NULL, default false |
| `given_at` | TIMESTAMPTZ | NULL |
| `withdrawn_at` | TIMESTAMPTZ | NULL |
| `source_of_change` | TEXT | NOT NULL, CHECK ∈ {manual, llm, import, admin} |
| `created_at` | TIMESTAMPTZ | NOT NULL default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL default now() |

- UNIQUE(account_id, consent_kind).
- Index `idx_consent_account` on `account_id`.
- RLS : `USING (account_id = current_setting('app.current_account_id')::uuid)`.
- Trigger BEFORE UPDATE → bump `updated_at`.

## Table `deletion_request`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | UUID | PK |
| `account_id` | UUID | NOT NULL, FK `account(id)` ON DELETE CASCADE, UNIQUE (un seul actif/compte) |
| `requested_at` | TIMESTAMPTZ | NOT NULL default now() |
| `effective_at` | TIMESTAMPTZ | NOT NULL, GENERATED ALWAYS AS (`requested_at + interval '30 days'`) STORED |
| `status` | TEXT | NOT NULL, CHECK ∈ {requested, cancelled, executed} |
| `cancelled_at` | TIMESTAMPTZ | NULL |
| `executed_at` | TIMESTAMPTZ | NULL |

- RLS PME : SELECT/INSERT/UPDATE limited to own account_id.
- Transition d'état : `requested → cancelled` (par PME jusqu'à `effective_at`), `requested → executed` (par job admin à effective_at atteint).

## Table `privacy_policy_version`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | UUID | PK |
| `version` | TEXT | NOT NULL UNIQUE (semver `1.0.0`, `1.1.0`, `2.0.0`) |
| `published_at` | TIMESTAMPTZ | NOT NULL default now() |
| `is_major` | BOOL | NOT NULL default false |
| `content_md` | TEXT | NOT NULL |
| `created_by_admin_id` | UUID | NOT NULL, FK `account(id)` |
| `source_ids` | UUID[] | optional refs to F03 sources |

- RLS : SELECT public (anon + authenticated), INSERT via `publish_new_version` SECURITY DEFINER (admin only).
- Helper `publish_new_version(content_md, version, is_major)` (F04) crée + audit_log entry source_of_change='admin'.

## Table `consent_acceptance`

| Colonne | Type | Contraintes |
|---|---|---|
| `account_id` | UUID | PK part 1, FK `account(id)` ON DELETE CASCADE |
| `policy_version_id` | UUID | PK part 2, FK `privacy_policy_version(id)` |
| `accepted_at` | TIMESTAMPTZ | NOT NULL default now() |

- RLS PME : SELECT/INSERT pour son account_id uniquement.

## Table `fx_rate`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | UUID | PK |
| `currency_from` | TEXT | NOT NULL, CHECK ∈ Currency |
| `currency_to` | TEXT | NOT NULL, CHECK ∈ Currency |
| `rate` | NUMERIC(20, 10) | NOT NULL CHECK > 0 |
| `captured_at` | TIMESTAMPTZ | NOT NULL default now() |
| `valid_from` | TIMESTAMPTZ | NOT NULL default now() |
| `valid_to` | TIMESTAMPTZ | NULL |
| `is_peg` | BOOL | NOT NULL default false |
| `peg_source_id` | UUID | NULL, FK `source(id)` ; NOT NULL si `is_peg=true` |
| `provider` | TEXT | NULL (`exchangerate-api.com` ou `bceao_decree`) |

- Index `idx_fx_rate_pair_captured` on (currency_from, currency_to, captured_at DESC).
- CHECK : `currency_from <> currency_to`.
- Seed migration `005h` : insère ligne peg `(EUR, XOF, 655.957, is_peg=true, peg_source_id=<bceao_source_uuid>)` et inverse.
- RLS : SELECT public authenticated, INSERT via fonction SECURITY DEFINER admin.

## Table `scheduled_job_run`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | UUID | PK |
| `job_name` | TEXT | NOT NULL CHECK ∈ {purge_pending_deletions, refresh_fx_rates, alert_stale_fx} |
| `run_date` | DATE | NOT NULL |
| `status` | TEXT | NOT NULL CHECK ∈ {running, success, failed} |
| `message` | TEXT | NULL |
| `started_at` | TIMESTAMPTZ | NOT NULL default now() |
| `finished_at` | TIMESTAMPTZ | NULL |

- UNIQUE(job_name, run_date) → idempotence.
- Pas multi-tenant (table interne admin) ; RLS DISABLE, GRANT SELECT/INSERT/UPDATE au rôle `app_scheduler` only.

## Pydantic types

```python
# app/schemas/money.py
class Money(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    amount: Decimal = Field(..., ge=0)
    currency: Currency

    @field_serializer('amount')
    def _ser_amount(self, v: Decimal) -> str:
        return format(v, 'f')
```

## Extension du trigger F04

```sql
CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'audit_log is append-only';
  END IF;
  IF TG_OP = 'UPDATE' THEN
    -- RTBF exception: only user_id column may change, only in purge context
    IF current_setting('app.purge_context', true) IS DISTINCT FROM 'on' THEN
      RAISE EXCEPTION 'audit_log is append-only';
    END IF;
    IF NEW.account_id IS DISTINCT FROM OLD.account_id
       OR NEW.timestamp IS DISTINCT FROM OLD.timestamp
       OR NEW.entity_type IS DISTINCT FROM OLD.entity_type
       OR NEW.entity_id IS DISTINCT FROM OLD.entity_id
       OR NEW.field IS DISTINCT FROM OLD.field
       OR NEW.old_value IS DISTINCT FROM OLD.old_value
       OR NEW.new_value IS DISTINCT FROM OLD.new_value
       OR NEW.source_of_change IS DISTINCT FROM OLD.source_of_change THEN
      RAISE EXCEPTION 'audit_log purge context: only user_id may be updated';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Relations clés

```text
account 1──N consent
account 1──0..1 deletion_request
account 1──N consent_acceptance N──1 privacy_policy_version
fx_rate N──0..1 source (peg only)
scheduled_job_run (standalone, admin)
```
