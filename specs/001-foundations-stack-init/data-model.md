# Data Model — F01 Initial Schema

**Date** : 2026-04-29
**Statut** : Phase 1 design

## Conventions communes

- **PK** : `id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY` sur toutes les tables.
- **Timestamps** : `created_at TIMESTAMP NOT NULL DEFAULT now()`, `updated_at TIMESTAMP NOT NULL DEFAULT now()` sur toutes les tables.
- **Auteur** : `created_by UUID NULL REFERENCES account_user(id)` sur toutes les tables sauf `account` et `account_user` (NULL autorisé pour créations système).
- **Versioning** : `version INT NOT NULL DEFAULT 1` sur toutes les tables.
- **Soft delete** : `deleted_at TIMESTAMP NULL` sur les tables MÉTIER (entreprise, projet, candidature, chat_message, account_user). PAS sur audit_log (append-only) ni sur tables CATALOGUE en F01.
- **Multi-tenant** : `account_id UUID NOT NULL REFERENCES account(id)` + index sur les tables MÉTIER.
- **Money** : pour chaque champ monétaire `<champ>` → `<champ>_amount NUMERIC(18,2) NULL` + `<champ>_currency CHAR(3) NULL` + `CHECK ((amount IS NULL AND currency IS NULL) OR (amount IS NOT NULL AND currency IS NOT NULL AND char_length(currency)=3))`.
- **Source** : `source_id UUID NULL REFERENCES source(id)` sur les tables qui en F03 deviendront NOT NULL : indicateur, critere, facteur_emission, document_requis, accreditation, template.

## Tables MÉTIER (avec `account_id`)

### `account`
> Racine multi-tenant. PAS d'`account_id` (c'est lui-même la racine).

| Colonne | Type | Contraintes |
|---------|------|-------------|
| id | UUID | PK |
| name | TEXT | NOT NULL |
| created_at, updated_at | TIMESTAMP | NOT NULL DEFAULT now() |

### `account_user`

| Colonne | Type | Contraintes |
|---------|------|-------------|
| id | UUID | PK |
| account_id | UUID | NOT NULL, FK account, INDEX |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NULL (rempli en F02) |
| role | TEXT | NULL (sera enum {pme, admin} en F02) |
| created_at, updated_at | TIMESTAMP | NOT NULL DEFAULT now() |
| version | INT | NOT NULL DEFAULT 1 |
| deleted_at | TIMESTAMP | NULL |

### `entreprise` (1 par account)

| Colonne | Type |
|---------|------|
| id | UUID PK |
| account_id | UUID NOT NULL FK INDEX |
| name | TEXT NOT NULL |
| secteur | TEXT NULL |
| taille_ca_amount | NUMERIC(18,2) NULL |
| taille_ca_currency | CHAR(3) NULL |
| taille_effectifs | INT NULL |
| localisation | TEXT NULL |
| gouvernance | TEXT NULL |
| pratiques_actuelles_json | JSONB NULL |
| version | INT NOT NULL DEFAULT 1 |
| created_at, updated_at | TIMESTAMP NOT NULL |
| created_by | UUID NULL FK account_user |
| deleted_at | TIMESTAMP NULL |

CHECK Money sur `taille_ca_*`.

### `projet`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| account_id | UUID NOT NULL FK INDEX |
| entreprise_id | UUID NOT NULL FK entreprise |
| nom | TEXT NOT NULL |
| description | TEXT NULL |
| type_impact | TEXT NULL |
| maturite | TEXT NULL |
| montant_recherche_amount | NUMERIC(18,2) NULL |
| montant_recherche_currency | CHAR(3) NULL |
| structure_financement | TEXT NULL |
| indicateurs_impact_json | JSONB NULL |
| localisation | TEXT NULL |
| statut | TEXT NULL |
| version | INT NOT NULL DEFAULT 1 |
| common (created_at, updated_at, created_by, deleted_at) |

CHECK Money sur `montant_recherche_*`.

### `candidature`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| account_id | UUID NOT NULL FK INDEX |
| projet_id | UUID NOT NULL FK projet |
| offre_id | UUID NOT NULL FK offre |
| statut | TEXT NULL |
| snapshot_json | JSONB NULL (exigence P4 : immuable à la soumission) |
| soumission_at | TIMESTAMP NULL |
| version | INT NOT NULL DEFAULT 1 |
| common |

### `chat_message`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| account_id | UUID NOT NULL FK INDEX |
| user_id | UUID NULL FK account_user |
| role | TEXT NOT NULL (user/assistant/system/tool) |
| content | TEXT NOT NULL |
| payload_json | JSONB NULL |
| embedding | VECTOR(1024) NULL |
| created_at | TIMESTAMP NOT NULL DEFAULT now() |
| updated_at | TIMESTAMP NOT NULL DEFAULT now() |
| version | INT NOT NULL DEFAULT 1 |
| deleted_at | TIMESTAMP NULL |

### `audit_log` (append-only, P3)
> AUCUN `deleted_at`. AUCUN `updated_at`. Triggers en F04.

| Colonne | Type |
|---------|------|
| id | UUID PK |
| user_id | UUID NULL FK account_user |
| account_id | UUID NULL FK account (nullable car événements système) |
| timestamp | TIMESTAMP NOT NULL DEFAULT now() INDEX |
| entity_type | TEXT NOT NULL |
| entity_id | UUID NOT NULL |
| field | TEXT NULL |
| old_value | JSONB NULL |
| new_value | JSONB NULL |
| source_of_change | TEXT NOT NULL CHECK IN ('manual','llm','import','admin') |

## Tables CATALOGUE / partagées (PAS d'`account_id`)

### `source`
> En F03 deviendra le pilier du sourçage. En F01, table créée mais pas encore enforced.

| Colonne | Type |
|---------|------|
| id | UUID PK |
| url | TEXT NULL |
| title | TEXT NOT NULL |
| publisher | TEXT NULL |
| version | TEXT NULL |
| date_publi | DATE NULL |
| page | TEXT NULL |
| section | TEXT NULL |
| captured_at | TIMESTAMP NULL |
| captured_by | UUID NULL FK account_user |
| verified_by | UUID NULL FK account_user |
| verification_status | TEXT NULL (draft/pending/verified/rejected — enforced F03) |
| created_at, updated_at | TIMESTAMP NOT NULL |
| created_by | UUID NULL |

### `referentiel`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| name | TEXT NOT NULL |
| version | TEXT NOT NULL |
| valid_from | DATE NULL |
| valid_to | DATE NULL |
| status | TEXT NULL |
| common (created_at, updated_at, created_by) |

### `indicateur`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| name | TEXT NOT NULL |
| definition | TEXT NULL |
| unite | TEXT NULL |
| status | TEXT NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| common |

### `critere`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| offre_id | UUID NULL FK offre |
| referentiel_id | UUID NULL FK referentiel |
| expression_json | JSONB NULL |
| indicateur_ids | UUID[] NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| common |

CHECK : exactement un de `offre_id` ou `referentiel_id` non-NULL.

### `fonds_source`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| name | TEXT NOT NULL |
| organisation | TEXT NULL |
| type | TEXT NULL |
| thematique | TEXT NULL |
| instruments | TEXT[] NULL |
| plafond_amount | NUMERIC(18,2) NULL |
| plafond_currency | CHAR(3) NULL |
| plancher_amount | NUMERIC(18,2) NULL |
| plancher_currency | CHAR(3) NULL |
| eligibilite_geo | TEXT[] NULL |
| submission_mode | TEXT NULL |
| version | INT NOT NULL DEFAULT 1 |
| status | TEXT NULL |
| common |

CHECK Money sur `plafond_*` et `plancher_*`.

### `intermediaire`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| name | TEXT NOT NULL |
| type | TEXT NULL |
| pays | TEXT NULL |
| contact | TEXT NULL |
| frais_json | JSONB NULL |
| delais_json | JSONB NULL |
| version | INT NOT NULL DEFAULT 1 |
| status | TEXT NULL |
| common |

### `accreditation`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| intermediaire_id | UUID NOT NULL FK intermediaire |
| fonds_id | UUID NOT NULL FK fonds_source |
| date_debut | DATE NULL |
| date_fin | DATE NULL |
| plafond_amount | NUMERIC(18,2) NULL |
| plafond_currency | CHAR(3) NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| common |

CHECK Money sur `plafond_*`. UNIQUE (intermediaire_id, fonds_id, date_debut).

### `offre`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| fonds_id | UUID NOT NULL FK fonds_source |
| intermediaire_id | UUID NULL FK intermediaire |
| accepted_languages | TEXT[] NULL |
| version | INT NOT NULL DEFAULT 1 |
| status | TEXT NULL |
| common |

### `document_requis`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| fonds_id | UUID NULL FK fonds_source |
| intermediaire_id | UUID NULL FK intermediaire |
| name | TEXT NOT NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| common |

CHECK : au moins un de fonds_id, intermediaire_id non-NULL.

### `facteur_emission`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| name | TEXT NOT NULL |
| valeur | NUMERIC(18,6) NOT NULL |
| unite | TEXT NOT NULL |
| pays | TEXT NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| version | INT NOT NULL DEFAULT 1 |
| common |

### `template`

| Colonne | Type |
|---------|------|
| id | UUID PK |
| offre_id | UUID NOT NULL FK offre |
| name | TEXT NOT NULL |
| structure_json | JSONB NULL |
| source_id | UUID NULL FK source (NOT NULL en F03) |
| common |

## Index

- INDEX BTREE sur `account_id` pour : entreprise, projet, candidature, chat_message, audit_log, account_user.
- INDEX BTREE sur `audit_log.timestamp`, `audit_log.entity_type`, `audit_log.entity_id`.
- INDEX BTREE sur `account_user.email` (UNIQUE déjà).
- INDEX IVFFLAT (à créer en F18) sur `chat_message.embedding` — pas en F01 (ne sert à rien tant qu'aucune ligne).

## Extensions Postgres activées par la migration 0001

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
```

## Décisions de typage rappelées

- Tous les `id` sont UUID v4 générés en base via `gen_random_uuid()`.
- Aucune contrainte CHECK stricte sur `account_user.role` en F01 (F02 enforce {pme, admin}).
- Aucune politique RLS en F01 (F02 active).
- Aucune contrainte `source_id NOT NULL` en F01 (F03 enforce).
- Aucun trigger sur audit_log en F01 (F04 active triggers + révoque UPDATE/DELETE).
