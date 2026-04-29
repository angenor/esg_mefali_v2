# Data Model — F07 Catalog Sources Management

## Aperçu

F07 ne crée **aucune nouvelle table**. La table `source` est posée par F03. F07 ajoute uniquement :

1. Une colonne dérivée `canonical_url` (backfillée).
2. Une colonne générée stockée `search_vector` (`tsvector`).
3. Des index (GIN full-text + unique fonctionnel doublon).
4. Une extension Postgres `unaccent` si absente.

Le versioning de la `source` (F04) et l'audit log append-only (F04) sont **réutilisés** sans modification.

## Table `source` (rappel F03 + ajouts F07)

| Colonne | Type | Contrainte | Origine |
|---------|------|------------|---------|
| `id` | UUID | PK | F03 |
| `url` | TEXT | NOT NULL | F03 |
| `canonical_url` | TEXT | NOT NULL (après backfill) | **F07** |
| `title` | TEXT | NOT NULL | F03 |
| `publisher` | TEXT | NOT NULL | F03 |
| `version` | TEXT | NULL | F03 |
| `date_publi` | DATE | NULL | F03 |
| `page` | INTEGER | NULL | F03 |
| `section` | TEXT | NULL | F03 |
| `notes` | TEXT | NULL | F03 |
| `verification_status` | ENUM(`pending`,`verified`,`outdated`) | NOT NULL DEFAULT `'pending'` | F03 |
| `captured_by` | UUID | NOT NULL FK `users(id)` | F03 |
| `verified_by` | UUID | NULL FK `users(id)` | F03 |
| `verified_at` | TIMESTAMPTZ | NULL | F03 |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | F03 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | F03 |
| `current_version` | INTEGER | NOT NULL DEFAULT 1 | F04 |
| `search_vector` | TSVECTOR GENERATED | indexable GIN | **F07** |

### Contraintes ajoutées par F07

- `CHECK (verification_status <> 'verified' OR verified_by IS DISTINCT FROM captured_by)` — garantit la double validation au niveau DB (en plus du contrôle service, double rideau).
- `CREATE UNIQUE INDEX ux_source_canonical_url_page ON source (canonical_url, coalesce(page, 0))` — empêche les doublons.
- `CREATE INDEX idx_source_search_vector ON source USING GIN (search_vector)`.
- `CREATE INDEX idx_source_verification_status ON source (verification_status)`.
- `CREATE INDEX idx_source_publisher ON source (publisher)`.

### Définition `search_vector`

```sql
search_vector TSVECTOR GENERATED ALWAYS AS (
  to_tsvector('french',
    unaccent(coalesce(title,'') || ' ' || coalesce(publisher,'') || ' ' || coalesce(notes,'')))
) STORED;
```

## Transitions d'état (verification_status)

```
pending ──verify(by ≠ captured_by)──► verified
verified ─────mark_outdated()────────► outdated
pending ────────soft_delete()────────► (deleted, only if no FK)
```

Aucune transition de `outdated` → `verified` ni de `verified` → `pending` (création d'une nouvelle source si besoin).

## Versioning (F04, réutilisé)

Helper `versioning.bump_source_version(source_id, by, before, after)` :

- Incrémente `source.current_version`.
- Insère ligne dans `source_version` (table F04) avec `before_json`, `after_json`, `changed_by`, `changed_at`.
- Déclenché uniquement si delta sur `(url, version, publisher)`.

## Audit (F04, réutilisé)

Helper `audit.record(entity='source', entity_id, action, actor, before, after, source_of_change='admin')`.

Actions enregistrées : `source.create`, `source.update`, `source.verify`, `source.mark_outdated`, `source.delete`.

## Modèle de réponse `Impact`

```jsonc
{
  "source_id": "uuid",
  "counters": {
    "indicateurs": 0,
    "criteres": 8,
    "formules": 2,
    "facteurs_emission": 0,
    "documents_requis": 1,
    "referentiels": 1,
    "skills": 2,
    "candidatures": 12
  },
  "has_published_dependents": true,
  "can_delete": false,
  "can_mark_outdated": true
}
```

Endpoint `/impact/{category}?page=&page_size=` retourne :

```jsonc
{
  "category": "criteres",
  "items": [
    { "id": "uuid", "name": "...", "status": "published", "version": 3 }
  ],
  "total": 8, "page": 1, "page_size": 25
}
```

## Modèle de réponse `Unsourced Claims` (US6)

```jsonc
{
  "items": [
    { "claim_text": "...", "occurrences": 12, "first_seen": "...", "last_seen": "...", "sample_context": "..." }
  ],
  "total": 42, "page": 1, "page_size": 25
}
```

(Source : table `unsourced_claim` produite par F03 FR-009, agrégée ici.)
