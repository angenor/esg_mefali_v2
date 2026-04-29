# Data Model — F06 Back-Office Skeleton

F06 n'introduit **pas** de tables métier nouvelles côté plateforme finale. Une seule table de **démonstration** (`demo_indicator`) est ajoutée pour valider le workflow draft→published, le versioning F04 et l'audit `source_of_change='admin'`. Cette table sera **dépréciée par F09** (Indicateur réel) puis supprimée par migration.

## 1. Table `demo_indicator` (démo F06, superseded par F09)

| Colonne | Type | Contraintes | Note |
|---------|------|-------------|------|
| `id` | UUID | PK, default `gen_random_uuid()` | |
| `name` | TEXT | NOT NULL | indexé (trigram GIN) |
| `external_id` | TEXT | UNIQUE, NULL allowed | indexé (trigram GIN) |
| `publisher` | TEXT | NULL allowed | indexé (trigram GIN) |
| `description` | TEXT | NULL allowed | |
| `unit` | TEXT | NULL allowed | |
| `source_id` | UUID | NOT NULL, FK `sources(id)` | gate P1 |
| `status` | enum_status | NOT NULL, default `'draft'` | `draft|published|outdated|pending` (F01) |
| `version` | INT | NOT NULL, default 1 | F04 versioning + ETag |
| `valid_from` | TIMESTAMPTZ | NOT NULL, default `now()` | F04 |
| `valid_to` | TIMESTAMPTZ | NULL | F04 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `created_by` | UUID | NOT NULL, FK `users(id)` | |
| `published_by` | UUID | NULL, FK `users(id)` | rempli au passage `published` |

### Index

- `idx_demo_indicator_status` BTREE sur `(status)`.
- `idx_demo_indicator_created_at_id` BTREE sur `(created_at DESC, id DESC)` — keyset pagination.
- `idx_demo_indicator_name_trgm` GIN sur `name gin_trgm_ops`.
- `idx_demo_indicator_publisher_trgm` GIN sur `publisher gin_trgm_ops`.
- `idx_demo_indicator_external_id_trgm` GIN sur `external_id gin_trgm_ops`.

### Politique RLS

Cohérence F02 — les tables catalogue n'ont pas de `account_id` (donnée partagée) mais restreignent l'écriture aux admins :

```sql
ALTER TABLE demo_indicator ENABLE ROW LEVEL SECURITY;

CREATE POLICY demo_indicator_read ON demo_indicator
  FOR SELECT USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');

CREATE POLICY demo_indicator_write ON demo_indicator
  FOR ALL USING (current_setting('app.is_admin', true) = 'true')
            WITH CHECK (current_setting('app.is_admin', true) = 'true');
```

### Versioning

Réutilise le mécanisme F04 : à toute modification d'un objet `published`, la procédure `publish_new_version(entity_type, entity_id, payload)` :

1. Clôt l'enregistrement courant (`valid_to = now()`, `status='outdated'`).
2. Insère un nouvel enregistrement (`version = old.version + 1`, `valid_from = now()`, `status='draft'` ou `published` selon contexte).
3. Vérifie `If-Match` (412 sinon).
4. Appelle `audit_log.write_event(...)` avec `source_of_change='admin'`.

## 2. Registry (mémoire applicative, pas de DB)

```python
@dataclass(frozen=True)
class EntitySpec:
    name: str                         # "demo_indicator", "sources", "indicateurs"
    table: type[Base]                 # SQLAlchemy ORM model
    read_schema: type[BaseModel]      # Pydantic read
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    sources_relation: Callable[[Any], Iterable[Source]]  # pour gate publish
    searchable_fields: tuple[str, ...] = ("name", "publisher", "external_id")
    sidebar_section: str = ""        # libellé sidebar
```

Le registry est instancié au boot ; F06 enregistre `demo_indicator`. F07-F20 ajoutent leurs entités via `registry.register(...)`.

## 3. Lifecycle d'un objet catalogue (état machine)

```
draft ──── publish() ────► published
  ▲                         │
  │ edit (forbidden direct) │ edit
  │                         ▼
  │                       (publish_new_version → new draft v_n+1)
  │
outdated ◄───────────────── ancien enregistrement
pending → utilisé par F03 pour les Sources (F06 lit ce statut)
```

- Transitions autorisées via API admin :
  - `(none) → draft` : POST create.
  - `draft → draft` : PUT update.
  - `draft → published` : POST `/publish`, gate sources verified.
  - `published → (new draft v_n+1)` : PUT update sur published, via `publish_new_version`, ancienne version → `outdated`.
  - `(jamais) published → draft` : interdit ; on crée v_n+1.
  - `(jamais) → pending` : statut réservé sources F03, non écrit par F06.

## 4. audit_log (existant F04, F06 l'utilise)

F06 n'altère pas la structure. Chaque mutation back-office écrit :

```
{
  user_id: <admin>,
  account_id: NULL,                  # opérations catalogue, pas tenant
  timestamp: now(),
  entity_type: 'demo_indicator',     # ou autre nom enregistré
  entity_id: <uuid>,
  field: NULL | <field>,
  old_value: <jsonb>,
  new_value: <jsonb>,
  source_of_change: 'admin'
}
```

`account_id NULL` est admis car l'audit F04 supporte les actions cross-tenant administratives ; vérifier que le schéma F04 le permet (sinon ajout migration F06 pour `ALTER COLUMN account_id DROP NOT NULL` — point à confirmer en quickstart).
