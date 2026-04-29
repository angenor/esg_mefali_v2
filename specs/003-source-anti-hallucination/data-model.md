# Phase 1 — Data Model: Source & Sourçage Anti-Hallucination

**Feature**: 003-source-anti-hallucination
**Date**: 2026-04-29

## 1. Enum `source_verification_status`

```sql
CREATE TYPE source_verification_status AS ENUM (
  'pending',
  'verified',
  'outdated',
  'rejected'
);
```

## 2. Table `source` (catalogue global, lecture publique unitaire FR-004)

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` | |
| `url` | `text` | NOT NULL, CHECK (`url ~ '^https?://'`) | URL officielle |
| `title` | `text` | NOT NULL | |
| `publisher` | `text` | NOT NULL | GCF / IFC / BCEAO / BOAD / GRI / etc. |
| `version` | `text` | NULL | Ex. "v2.1" du référentiel |
| `date_publi` | `date` | NULL | Date officielle de publication |
| `page` | `text` | NULL | Ex. "p. 14" |
| `section` | `text` | NULL | Ex. "Annexe B" |
| `captured_at` | `timestamptz` | NOT NULL, default `now()` | |
| `captured_by` | `uuid` | NOT NULL, FK `account_user(id)` | Admin créateur |
| `verified_by` | `uuid` | NULL, FK `account_user(id)` | Admin valideur, NULL tant que `pending` |
| `verified_at` | `timestamptz` | NULL | Renseigné à la transition |
| `verification_status` | `source_verification_status` | NOT NULL, default `'pending'` | |
| `notes` | `text` | NULL | Notes admin libres |
| `embedding` | `vector(1024)` | NULL (NOT NULL après `verified`) | Voyage `voyage-3.5` |
| `tsv` | `tsvector` | GENERATED ALWAYS AS (`to_tsvector('french', coalesce(title,'') || ' ' || coalesce(publisher,'') || ' ' || coalesce(notes,''))`) STORED | |
| `status_version` | `bigint` | NOT NULL, default 1 | Incrémenté à chaque transition pour invalidation cache middleware |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | |
| `updated_at` | `timestamptz` | NOT NULL, default `now()` | trigger update |

**Contraintes & triggers** :

- `CHECK (verification_status <> 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL AND embedding IS NOT NULL))` — interdit `verified` sans valideur, date, embedding.
- Trigger `BEFORE UPDATE` : si transition vers `verified`, REJECT si `NEW.verified_by = OLD.captured_by` (double validation, FR-013).
- Trigger `BEFORE UPDATE` : à toute modification de `verification_status`, incrémenter `status_version` et insérer dans le journal d'audit (consommé par F04).
- Indexes :
  - `CREATE INDEX source_tsv_gin ON source USING gin(tsv);` (R1, full-text)
  - `CREATE INDEX source_embedding_ivf ON source USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);` (R1, vectoriel)
  - `CREATE INDEX source_status_idx ON source(verification_status);`
  - `CREATE INDEX source_publisher_idx ON source(publisher);`

**RLS** :

- `source` est globale : pas de RLS PME (catalogue partagé). Lecture admin contrôlée via RBAC F02 (`role IN ('admin','superadmin')`). Lecture unitaire publique autorisée pour `GET /sources/{id}` (besoin du picto F04 + page F30).

## 3. Table `unsourced_claim_log` (RLS par `account_id` FR-007)

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` | |
| `account_id` | `uuid` | NOT NULL, FK `account(id)` | Tenant |
| `user_id` | `uuid` | NULL, FK `account_user(id)` | NULL pour appel système |
| `claim_text` | `text` | NOT NULL | |
| `claim_text_normalized` | `text` | GENERATED ALWAYS AS (lower(trim(claim_text))) STORED | Pour agrégation |
| `context_json` | `jsonb` | NOT NULL, default `'{}'::jsonb` | Contexte LLM (intent, message id, tour) |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | |

- Index `(account_id, claim_text_normalized)` pour agrégation FR-011.
- RLS : `USING (account_id = current_setting('app.account_id')::uuid)` (réutilise pattern F02).
- `INSERT` accordé à `app_user` ; `UPDATE`/`DELETE` REVOKE (append-only, P3).

## 4. Vues `v_<entity>_verified`

Pour chaque table catalogue (créée ici si non existante en F01, sinon préparation par migration ALTER) : `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `document_requis`, `referentiel`.

```sql
CREATE OR REPLACE VIEW v_indicateur_verified AS
SELECT i.*
FROM indicateur i
JOIN source s ON s.id = i.source_id
WHERE s.verification_status = 'verified';
```

(idem pour les 6 autres entités)

**Contrainte FK NOT NULL préparée** : pour chaque entité catalogue déjà en base, `ALTER TABLE <entity> ADD COLUMN IF NOT EXISTS source_id uuid REFERENCES source(id) ON DELETE RESTRICT;` puis `ALTER TABLE <entity> ALTER COLUMN source_id SET NOT NULL;` (échoue si données non backfillées — la migration documente la procédure pour Phase 1 catalogue F07/F09).

## 5. Compteur `source_status_version` global

- Géré comme colonne par-source (cf. table `source`) ; le middleware combine `max(source_status_version) FROM source WHERE id = ANY(cited_ids)` dans la clé de cache.

## 6. State machine de `source.verification_status`

```
pending ──(admin B ≠ A valide + embedding OK)──▶ verified
pending ──(admin rejette)────────────────────▶ rejected
verified ──(admin marque obsolète)───────────▶ outdated
verified ──(amendement majeur)────────────────▶ pending  (rare ; recompute embedding nécessaire)
outdated ──(admin re-valide nouvelle version)─▶ verified
rejected ──── (terminal ; nouvelle source à créer)
```

Toute transition incrémente `status_version`, met à jour `updated_at`, insère une trace audit (`source_of_change = 'admin'`).

## 7. Décision middleware (en mémoire, non persistée)

```python
class LLMValidationDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    accepted: bool
    reason_code: Literal['ok','no_citation','source_not_verified','source_not_found','heuristic_match_no_tool'] | None
    cited_source_ids: tuple[UUID, ...]
    detected_units: tuple[str, ...]
```

Cache : `TTLCache(maxsize=10000, ttl=300)` ; clé `sha256(message_text + sorted(cited_ids) + max(status_versions))`.

## 8. Schéma Pydantic des tools (cf. contracts/)

- `CiteSourceInput { source_id: UUID }` → `Source` ou `ToolError(code='not_verified'|'not_found')`.
- `SearchSourceInput { query: str (1..256), publisher: str | None, k: int = 10 (1..50) }` → `list[Source]` (uniquement `verified`).
- `FlagUnsourcedInput { claim: str (1..2000), context: dict[str, Any] }` → `{ id: UUID }`.

## 9. Relations (résumé)

- `source 1 — N indicateur` (NOT NULL, RESTRICT)
- `source 1 — N critere` (NOT NULL, RESTRICT)
- `source 1 — N formule` (NOT NULL, RESTRICT)
- `source 1 — N seuil` (NOT NULL, RESTRICT)
- `source 1 — N facteur_emission` (NOT NULL, RESTRICT)
- `source 1 — N document_requis` (NOT NULL, RESTRICT)
- `source 1 — N referentiel` (NOT NULL, RESTRICT)
- `account 1 — N unsourced_claim_log`
- `account_user 1 — N source` (captured_by, verified_by)
