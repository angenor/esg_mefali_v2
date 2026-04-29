# Data Model — F08 Catalogue Fonds, Intermédiaires & Offres

## Vue d'ensemble

4 nouvelles tables PostgreSQL :
- `fonds_source` (FR-001)
- `intermediaire` (FR-002)
- `accreditation` (FR-003)
- `offre` (FR-004)

Toutes sont **globales** (pas de `account_id`). RLS politique : `SELECT` autorisé pour utilisateurs authentifiés sur `status='published'` ; `INSERT/UPDATE/DELETE` réservé au rôle `admin`.

Réutilisation : `Source` (F03/F07), `audit_log` (F04), `Money` JSONB embedded `{amount: Decimal, currency: str}` (F01).

## Table `fonds_source`

| Colonne | Type | Nullable | Notes |
|---------|------|----------|-------|
| `id` | UUID PK | NO | `gen_random_uuid()` |
| `name` | TEXT | NO | unique avec `organisation` |
| `organisation` | TEXT | NO | ex. "Green Climate Fund" |
| `type` | ENUM `fonds_type` | NO | `multilateral, bilateral, regional, national, prive` |
| `thematique` | TEXT[] | NO | ex. `['climat','adaptation']` |
| `instruments` | TEXT[] | NO | ex. `['don','prêt concessionnel','garantie']` |
| `plafond_money` | JSONB | YES | `{amount:Decimal, currency:str}` |
| `plancher_money` | JSONB | YES | idem |
| `eligibilite_geo` | TEXT[] | NO | codes ISO 3166-1 alpha-2 |
| `submission_mode` | ENUM `submission_mode` | NO | `rolling, call_for_proposals` |
| `deadline` | TIMESTAMPTZ | YES | requis si `submission_mode='call_for_proposals'` |
| `referentiel_id` | UUID | YES | FK vers `referentiel` (F09 — nullable MVP) |
| `criteres_json` | JSONB | NO | `[Critere,...]` typé |
| `documents_requis_json` | JSONB | NO | `[{id, label, type}]` |
| `frais_json` | JSONB | NO | `{origination_pct, ...}` |
| `delais_json` | JSONB | NO | `{instruction_jours, decaissement_jours}` |
| `site_url` | TEXT | YES | |
| `contact_json` | JSONB | YES | |
| `source_ids` | UUID[] | NO | FK array vers `source` (F03) ; au moins 1 verified pour publish |
| `version` | INT | NO | défaut 1, F04 |
| `status` | ENUM `entity_status` | NO | `draft, published, archived` |
| `etag` | TEXT | NO | F06 (sha256 du payload + version) |
| `created_at` | TIMESTAMPTZ | NO | `now()` |
| `updated_at` | TIMESTAMPTZ | NO | `now()` |

**Index** : btree(`status`, `type`), GIN(`thematique`, `instruments`, `eligibilite_geo`), trigram GIN sur `name`, `organisation`.
**Contrainte** : `UNIQUE(name, organisation, version)`.
**RLS** : `SELECT` if `status='published'` OR `current_role='admin'` ; `INSERT/UPDATE/DELETE` if `current_role='admin'`.

## Table `intermediaire`

| Colonne | Type | Nullable | Notes |
|---------|------|----------|-------|
| `id` | UUID PK | NO | |
| `name` | TEXT | NO | unique |
| `type` | ENUM `intermediaire_type` | NO | `DAE, NIE, RIE, MIE, banque_locale, dev_carbone, agence_nationale, agence_implem` |
| `pays` | TEXT[] | NO | codes ISO |
| `zone_op` | TEXT | YES | ex. "UEMOA", "CEDEAO", "Afrique de l'Ouest" |
| `contact_json` | JSONB | YES | |
| `frais_json` | JSONB | NO | `{origination_pct, marge_pct}` |
| `delais_json` | JSONB | NO | `{instruction_jours, decaissement_jours}` |
| `criteres_json` | JSONB | NO | `[Critere,...]` typés |
| `documents_requis_json` | JSONB | NO | `[{id, label, type}]` |
| `referentiel_id` | UUID | YES | FK F09 nullable MVP — couche intermédiaire |
| `portail_url` | TEXT | YES | |
| `track_record_json` | JSONB | YES | saisie manuelle MVP |
| `source_ids` | UUID[] | NO | au moins 1 verified pour publish |
| `version` | INT | NO | F04 |
| `status` | ENUM `entity_status` | NO | |
| `etag` | TEXT | NO | F06 |
| `created_at`, `updated_at` | TIMESTAMPTZ | NO | |

**Index** : btree(`status`, `type`), GIN(`pays`), trigram GIN sur `name`.
**Contrainte** : `UNIQUE(name, version)`.
**RLS** : identique à `fonds_source`.

## Table `accreditation`

| Colonne | Type | Nullable | Notes |
|---------|------|----------|-------|
| `id` | UUID PK | NO | |
| `intermediaire_id` | UUID FK → `intermediaire(id)` | NO | |
| `fonds_id` | UUID FK → `fonds_source(id)` | NO | |
| `valid_from` | DATE | NO | |
| `valid_to` | DATE | YES | NULL = encore active |
| `plafond_money` | JSONB | YES | `{amount, currency}` |
| `source_id` | UUID FK → `source(id)` | NO | preuve officielle d'accréditation |
| `notes` | TEXT | YES | |
| `version` | INT | NO | F04 |
| `etag` | TEXT | NO | |
| `created_at`, `updated_at` | TIMESTAMPTZ | NO | |

**Index** : btree(`intermediaire_id`, `fonds_id`, `valid_from`), btree(`fonds_id`, `valid_from`), btree(`valid_to`).
**RLS** : `SELECT` ouvert authentifiés ; `INSERT/UPDATE/DELETE` admin.
**Helper SQL** :
```sql
CREATE OR REPLACE FUNCTION accreditation_is_active(
  acc accreditation, at TIMESTAMPTZ DEFAULT now()
) RETURNS BOOLEAN AS $$
  SELECT acc.valid_from <= at::date
     AND (acc.valid_to IS NULL OR acc.valid_to >= at::date)
$$ LANGUAGE sql IMMUTABLE;
```

## Table `offre`

| Colonne | Type | Nullable | Notes |
|---------|------|----------|-------|
| `id` | UUID PK | NO | |
| `fonds_id` | UUID FK | NO | |
| `intermediaire_id` | UUID FK | NO | |
| `name` | TEXT | NO | nom commercial ex. "GCF via BOAD" |
| `accepted_languages` | TEXT[] | NO | défaut `['fr']` ; whitelist `['fr','en']` MVP |
| `deadline` | TIMESTAMPTZ | YES | override de `fonds.deadline` |
| `criteres_offre_specifiques` | JSONB | NO | `[Critere,...]` |
| `documents_specifiques` | JSONB | NO | `[Document,...]` |
| `frais_specifiques` | JSONB | NO | `{...}` |
| `delais_specifiques` | JSONB | NO | `{...}` |
| `effective_snapshot_hash` | TEXT | YES | sha256 du dernier snapshot calculé (pour diff) |
| `needs_refresh` | BOOLEAN | NO | défaut `false` |
| `source_ids` | UUID[] | NO | au moins 1 verified pour publish |
| `version` | INT | NO | F04 |
| `status` | ENUM `entity_status` étendu : `draft, published, archived, outdated` | NO | |
| `etag` | TEXT | NO | F06 |
| `created_at`, `updated_at` | TIMESTAMPTZ | NO | |

**Contraintes** :
- `UNIQUE(fonds_id, intermediaire_id, name)` (FR-018).
- CHECK applicatif (service couche): `EXISTS accreditation active WHERE intermediaire_id+fonds_id` au moment de `INSERT` et de `publish`.
**Index** : btree(`status`, `fonds_id`, `intermediaire_id`), btree(`needs_refresh`), btree(`deadline`).
**RLS** : `SELECT` if `status='published'` OR `current_role='admin'` ; `INSERT/UPDATE/DELETE` admin.

## Schéma Pydantic JSONB `Critere`

```python
class Critere(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str = Field(min_length=1, max_length=100)
    operator: Literal['eq','min','max','in','not_in','contains']
    value: Any  # validé en cross-field selon operator
    unit: str | None = None
    source_id: UUID
```

## Schéma `Document`

```python
class Document(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str
    label: str
    type: Literal['identite','financier','technique','esg','juridique','autre']
    required: bool = True
    source_id: UUID | None = None
```

## Schéma réponse `/effective`

```python
class EffectiveLayer(BaseModel):
    criteres: list[Critere]
    documents: list[Document]
    frais: dict
    delais: dict
    referentiel: dict | None
    deadline: datetime | None

class EffectiveResponse(BaseModel):
    fonds_layer: EffectiveLayer
    intermediaire_layer: EffectiveLayer
    criteres_effectifs: list[Critere]
    documents_effectifs: list[Document]
    frais_effectifs: Money
    delais_effectifs_jours: int
    referentiel_effectif: dict
    accepted_languages: list[Literal['fr','en']]
    deadline: datetime | None
    effective_warning: list[str] = []
```

## Transitions d'état (Offre)

```
draft ──publish──► published
                    │
                    ├──fonds/inter modifié──► (needs_refresh=true) [reste published]
                    │
                    ├──aucune accreditation active──► outdated [via lazy/recheck]
                    │
                    └──admin archive──────► archived
```

## Lien avec entités existantes

- `Source` (F03/F07) : référencée via `source_ids[]` (Fonds, Intermédiaire, Offre) et `source_id` (Accreditation).
- `audit_log` (F04) : INSERT à chaque create/update/publish/soft-delete avec `source_of_change='admin'`, diff JSON.
- `Referentiel` (F09 à venir) : FK nullable MVP.

## Migration Alembic

Fichier : `backend/app/db/alembic/versions/008_xxxx_catalog_fonds_offre.py`
Crée :
1. ENUMs `fonds_type`, `submission_mode`, `intermediaire_type`, étend `entity_status` avec `outdated`.
2. Tables dans l'ordre : `fonds_source`, `intermediaire`, `accreditation`, `offre`.
3. Index (cf §indexation R7).
4. Politiques RLS (`ENABLE ROW LEVEL SECURITY`, `CREATE POLICY ...`).
5. Fonction `accreditation_is_active`.

Downgrade : DROP table dans l'ordre inverse, DROP types ENUM créés.
