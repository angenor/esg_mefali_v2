# Phase 1 — Data Model

## Table `attestations`

| Colonne | Type | Contrainte | Description |
|---------|------|------------|-------------|
| `id` | UUID | PK, default `gen_random_uuid()` | Identifiant interne. |
| `account_id` | UUID | NOT NULL, FK `accounts(id)` | Tenant — RLS. |
| `entreprise_id` | UUID | NOT NULL, FK `entreprises(id)` | PME émettrice. |
| `public_id` | UUID | NOT NULL, UNIQUE, default `gen_random_uuid()` | Identifiant public exposé sur `/verify/`. |
| `scores_inclus_json` | JSONB | NOT NULL | Snapshot canonique des scores inclus. |
| `referentiels_versions_json` | JSONB | NOT NULL | Map `code_referentiel -> version`. |
| `file_path` | TEXT | NOT NULL | Chemin relatif sous le storage local. |
| `signature_ed25519` | TEXT | NOT NULL | Hex (128 chars). |
| `pubkey_fingerprint` | TEXT | NOT NULL | Sha256 hex (64 chars) de la clé publique utilisée. |
| `hash_document` | TEXT | NOT NULL | Sha256 hex du document JSON canonique signé. |
| `generated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | Émission. |
| `generated_by` | UUID | NOT NULL, FK `accounts(id)` | Utilisateur ayant déclenché. |
| `valid_until` | TIMESTAMPTZ | NOT NULL | Borne d'expiration. |
| `revoked_at` | TIMESTAMPTZ | NULL | Date de révocation. |
| `revoked_by` | UUID | NULL, FK `accounts(id)` | Acteur de la révocation. |
| `revoked_reason` | TEXT | NULL | Motif libre, jamais exposé sur la page publique. |
| `version` | INT | NOT NULL, default 1 | Compteur. |

### Indices

- `UNIQUE(public_id)`
- `INDEX idx_attestations_account_id (account_id)`
- `INDEX idx_attestations_entreprise_id (entreprise_id)`
- `INDEX idx_attestations_valid_until (valid_until) WHERE revoked_at IS NULL`

### RLS (PostgreSQL)

```sql
ALTER TABLE attestations ENABLE ROW LEVEL SECURITY;

CREATE POLICY attestations_tenant ON attestations
  USING (account_id = current_setting('app.current_account_id')::uuid);
```

Les endpoints publics `/verify/{public_id}` utilisent un helper applicatif
`get_attestation_by_public_id` qui contourne le RLS en mode lecture seule (settings de session
sans `app.current_account_id` + requête directe via session admin/superuser scoped au RO).

### Statut dérivé

```python
status = (
    "revoked" if revoked_at is not None
    else "expired" if valid_until < now_utc()
    else "active"
)
```

## Snapshots `scores_inclus_json`

Schéma exemple (synthétique) :

```json
{
  "solvability": {"score": 72, "band": "B", "engine_version": "1.0.0"},
  "esg": {
    "esg_uemoa_pme_v1": {"score": 64, "version": "2025-09"},
    "esg_iso26000_v1":  {"score": 58, "version": "2024-11"}
  }
}
```

## Document JSON signé

Forme canonique (clés triées lexicographiquement, sans espaces, UTF-8) — exemple synthétique :

```json
{
  "entreprise_name": "<nom déclaratif>",
  "generated_at": "2026-04-29T10:00:00+00:00",
  "public_id": "<uuid>",
  "referentiels_versions": { "esg_uemoa_pme_v1": "2025-09" },
  "scores": { "solvability": { "score": 72 } },
  "schema_version": "v1",
  "valid_until": "2026-10-29T10:00:00+00:00"
}
```

Le hash sha256 du document encodé UTF-8 est stocké dans `hash_document`. La signature Ed25519 est
calculée sur les bytes UTF-8 du document (Ed25519 hash en interne).

## Audit log

Événements émis via `record_audit` :

| event | source_of_change | acteur |
|-------|------------------|--------|
| `attestation.generated` | manual | PME |
| `attestation.revoked` | manual | PME |
| `attestation.revoked` | admin | admin |
