# Data Model — F22 Documents Upload & OCR

## Table `document_entreprise`

Mirror exact (avec adaptations) de `document_projet` (F12, migration `0012_f12_projets_documents.py`).

```sql
CREATE TABLE document_entreprise (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id      UUID NOT NULL REFERENCES account(id),
  entreprise_id   UUID NOT NULL REFERENCES entreprise(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  mime_type       TEXT NOT NULL,
  size_bytes      BIGINT NOT NULL,
  type            TEXT NOT NULL,
  storage_path    TEXT NOT NULL,
  text_content    TEXT NULL,
  ocr_status      TEXT NOT NULL DEFAULT 'pending',
  ocr_error       TEXT NULL,
  uploaded_by     UUID NULL REFERENCES account_user(id),
  source_of_change TEXT NOT NULL DEFAULT 'manual',
  version         INT NOT NULL DEFAULT 1,
  deleted_at      TIMESTAMP NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT now(),
  updated_at      TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT chk_document_entreprise_size CHECK (size_bytes BETWEEN 1 AND 26214400),
  CONSTRAINT chk_document_entreprise_type CHECK (
      type IN ('statuts','rapport_activite','facture','contrat','politique','autre')
  ),
  CONSTRAINT chk_document_entreprise_ocr_status CHECK (
      ocr_status IN ('pending','done','deferred','failed')
  ),
  CONSTRAINT chk_document_entreprise_source CHECK (
      source_of_change IN ('manual','llm','import','admin')
  )
);

CREATE INDEX ix_document_entreprise_entreprise_id ON document_entreprise(entreprise_id);
CREATE INDEX ix_document_entreprise_account_id   ON document_entreprise(account_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON document_entreprise TO app_user;
GRANT ALL ON document_entreprise TO migrator;

ALTER TABLE document_entreprise ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_entreprise FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON document_entreprise
USING (
    COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
    OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
)
WITH CHECK (
    COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
    OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
);
```

## Énumérations applicatives

- `DocType` ∈ {`statuts`, `rapport_activite`, `facture`, `contrat`, `politique`, `autre`}.
- `OcrStatus` ∈ {`pending`, `done`, `deferred`, `failed`}.
- `MIME_WHITELIST` = {`application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`}.

## Transitions d'état OCR

```
INSERT ─► pending ─► (extraction sync) ─► done
                 ├──► deferred (image/docx/xlsx, ou PDF sans texte natif)
                 └──► failed (timeout, IO, PDF corrompu)
```

L'utilisateur n'écrit jamais directement `ocr_status`.

## Entité dataclass (Python)

```python
@dataclass(frozen=True)
class DocumentEntrepriseRow:
    id: UUID
    account_id: UUID
    entreprise_id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    type: str
    storage_path: str
    text_content: str | None
    ocr_status: str
    ocr_error: str | None
    uploaded_by: UUID | None
    created_at: datetime | None
```

## Mapping FR → validation

| FR | Validation |
|----|-----------|
| FR-002 | `size_bytes` BETWEEN 1 AND 26214400 (CHECK DB + applicatif) |
| FR-003 | `mime_type` ∈ MIME_WHITELIST (applicatif) |
| FR-004 | COUNT(*) WHERE `entreprise_id=:e AND deleted_at IS NULL` < 50 |
| FR-006 | RLS `tenant_isolation` + filtre `account_id` dans les requêtes service |
| FR-013 | `original_filename` conservé ; `storage_path` reconstruit en interne |

## Relations

- `document_entreprise.entreprise_id` FK vers `entreprise(id)` (F11) `ON DELETE CASCADE`.
- `document_entreprise.account_id` FK vers `account(id)`.
- `document_entreprise.uploaded_by` FK nullable vers `account_user(id)`.
