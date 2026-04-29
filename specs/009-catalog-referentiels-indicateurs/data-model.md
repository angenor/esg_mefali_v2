# Data Model — F09

Toutes les tables sont catalogue global (pas d'`account_id`), versionnées (F04) et sourcées (F07). Migration Alembic unique : `alembic/versions/XXXX_f09_catalog.py`.

## Enums Postgres

```sql
CREATE TYPE pillar_enum         AS ENUM ('E','S','G','transverse');
CREATE TYPE indicateur_value_type AS ENUM ('numeric','percentage','boolean','enum','text');
CREATE TYPE catalog_status_enum AS ENUM ('draft','published','archived','outdated');
CREATE TYPE referentiel_type    AS ENUM ('fonds','intermediaire','transverse','interne');
CREATE TYPE referentiel_formula AS ENUM ('weighted_sum','custom');
CREATE TYPE critere_owner_type  AS ENUM ('fonds','intermediaire','offre','referentiel');
CREATE TYPE critere_severity    AS ENUM ('blocking','warning','info');
CREATE TYPE document_owner_type AS ENUM ('fonds','intermediaire');
CREATE TYPE document_type_enum  AS ENUM ('juridique','financier','technique','impact','autre');
CREATE TYPE emission_scope      AS ENUM ('1','2','3');
CREATE TYPE emission_categorie  AS ENUM ('energie','transport','dechets','achats','autre');
```

## Tables

### `indicateur`
| col | type | notes |
|---|---|---|
| id | UUID PK |  |
| code | TEXT NOT NULL | UNIQUE, normalisé UPPER_SNAKE_CASE (FR-014) |
| name | TEXT NOT NULL |  |
| definition | TEXT NOT NULL | markdown |
| pillar | pillar_enum NOT NULL |  |
| unite | TEXT NOT NULL |  |
| value_type | indicateur_value_type NOT NULL |  |
| enum_values | JSONB NULL | requis si value_type='enum' (CHECK) |
| version | INT NOT NULL DEFAULT 1 |  |
| status | catalog_status_enum NOT NULL DEFAULT 'draft' |  |
| created_at, updated_at | TIMESTAMPTZ |  |
| etag | TEXT NOT NULL | F06 |

Table jonction sources : `indicateur_source(indicateur_id, source_id)` (FK `source.id` F07).

### `referentiel`
| col | type | notes |
|---|---|---|
| id | UUID PK |  |
| code | TEXT NOT NULL UNIQUE |  |
| name | TEXT NOT NULL |  |
| publisher | TEXT NOT NULL |  |
| type | referentiel_type NOT NULL |  |
| formula_type | referentiel_formula NOT NULL DEFAULT 'weighted_sum' |  |
| formula_expression | TEXT NULL | requis si formula_type='custom' (CHECK) |
| version | INT NOT NULL DEFAULT 1 |  |
| valid_from | DATE NOT NULL |  |
| valid_to | DATE NULL |  |
| status | catalog_status_enum NOT NULL DEFAULT 'draft' |  |
| created_at, updated_at | TIMESTAMPTZ |  |
| etag | TEXT NOT NULL |  |

Table jonction sources : `referentiel_source(referentiel_id, source_id)`.

### `referentiel_indicateur`
| col | type | notes |
|---|---|---|
| referentiel_id | UUID FK referentiel ON DELETE CASCADE |  |
| indicateur_id | UUID FK indicateur ON DELETE RESTRICT |  |
| poids | NUMERIC(8,4) NOT NULL CHECK (poids >= 0) |  |
| seuil_min | NUMERIC(18,6) NULL |  |
| seuil_max | NUMERIC(18,6) NULL |  |
| source_id | UUID FK source NOT NULL |  |
| PRIMARY KEY (referentiel_id, indicateur_id) |  |  |

### `critere`
| col | type | notes |
|---|---|---|
| id | UUID PK |  |
| owner_type | critere_owner_type NOT NULL |  |
| owner_id | UUID NOT NULL | FK polymorphe (validation applicative) |
| expression_json | JSONB NOT NULL | DSL strict (NFR-002) |
| label | TEXT NOT NULL |  |
| severity | critere_severity NOT NULL |  |
| source_id | UUID FK source NOT NULL |  |
| version | INT NOT NULL DEFAULT 1 |  |
| status | catalog_status_enum NOT NULL DEFAULT 'draft' |  |
| created_at, updated_at | TIMESTAMPTZ |  |
| etag | TEXT NOT NULL |  |

Index : `(owner_type, owner_id)` ; `(severity)`.

### `document_requis`
| col | type | notes |
|---|---|---|
| id | UUID PK |  |
| owner_type | document_owner_type NOT NULL |  |
| owner_id | UUID NOT NULL |  |
| name | TEXT NOT NULL |  |
| description | TEXT |  |
| type | document_type_enum NOT NULL |  |
| required_when | JSONB NULL | mini-DSL réutilisé |
| source_id | UUID FK source NOT NULL |  |
| version | INT NOT NULL DEFAULT 1 |  |
| status | catalog_status_enum NOT NULL DEFAULT 'draft' |  |
| etag | TEXT NOT NULL |  |

Index : `(owner_type, owner_id)`.

### `facteur_emission`
| col | type | notes |
|---|---|---|
| id | UUID PK |  |
| code | TEXT NOT NULL |  |
| name | TEXT NOT NULL |  |
| valeur | NUMERIC(18,6) NOT NULL CHECK (valeur >= 0) |  |
| unite | TEXT NOT NULL | ex: 'kgCO2e/kWh' |
| pays_iso2 | CHAR(2) NULL |  |
| scope | emission_scope NOT NULL |  |
| categorie | emission_categorie NOT NULL |  |
| source_id | UUID FK source NOT NULL |  |
| version | INT NOT NULL DEFAULT 1 |  |
| valid_from | DATE NOT NULL |  |
| valid_to | DATE NULL |  |
| status | catalog_status_enum NOT NULL DEFAULT 'draft' |  |
| etag | TEXT NOT NULL |  |
| UNIQUE (code, pays_iso2, valid_from) |  |  |

Index principal :
```sql
CREATE INDEX idx_facteur_emission_lookup
  ON facteur_emission (code, pays_iso2, valid_from DESC);
```

Trigger `BEFORE INSERT` ferme `valid_to` du précédent (cf research R3).

## RLS

```sql
ALTER TABLE indicateur, referentiel, referentiel_indicateur, critere,
            document_requis, facteur_emission ENABLE ROW LEVEL SECURITY;

-- politique générique (à dupliquer par table)
CREATE POLICY p_<table>_admin_or_pme_published ON <table>
  USING (
    current_setting('app.role', true) = 'admin'
    OR (current_setting('app.role', true) = 'pme' AND status = 'published')
  );
```
Tables jonction (`indicateur_source`, `referentiel_source`, `referentiel_indicateur`) héritent via JOIN ; politique RLS qui SELECT joint au parent.

## Audit

Décorateur F04 sur chaque service : émet `audit_event(actor, action, entity, before_json, after_json, source_of_change='admin', occurred_at)`.

## Versioning

`publish_new_version(entity, id, payload, if_match)` (F04) crée v(N+1) `draft` à partir d'une copie ; transition `draft → published` clos précédente version `published → outdated` (uniquement pour facteur_emission, conformément à R3).
