# F14 — Data Model

Une seule entité nouvelle : `ToolCallLog`. Aucun changement aux entités existantes.

## Entité : ToolCallLog (table `tool_call_log`)

Journal append-only de chaque appel de tool effectué par le pipeline F14.

### Colonnes

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | Identifiant unique du log |
| `account_id` | `UUID` | NOT NULL, FK → `account(id)` | Tenant isolé (RLS) |
| `user_id` | `UUID` | NULL | Auteur du message déclencheur (NULL si système) |
| `thread_id` | `UUID` | NOT NULL, FK → `chat_thread(id)` | Fil de conversation |
| `message_id` | `UUID` | NULL, FK → `chat_message(id)` | Message assistant produit |
| `tool_name` | `TEXT` | NOT NULL | Nom du tool (clé dans `TOOL_REGISTRY`) |
| `arguments_json` | `JSONB` | NOT NULL DEFAULT `'{}'::jsonb` | Payload validé fourni par le LLM |
| `result_json` | `JSONB` | NULL | Résultat retourné par le handler |
| `status` | `TEXT` | NOT NULL, CHECK IN (`'ok'`, `'validation_error'`, `'handler_error'`, `'timeout'`) | État final |
| `latency_ms` | `INT` | NOT NULL, CHECK ≥ 0 | Durée totale (validation + handler) |
| `retries` | `INT` | NOT NULL DEFAULT 0, CHECK [0, 2] | Nombre de retries effectués |
| `model` | `TEXT` | NULL | Modèle LLM utilisé (`LLM_MODEL`) |
| `prompt_tokens` | `INT` | NULL, CHECK ≥ 0 | Tokens consommés en prompt |
| `completion_tokens` | `INT` | NULL, CHECK ≥ 0 | Tokens consommés en complétion |
| `is_retry_overhead` | `BOOLEAN` | NOT NULL DEFAULT FALSE | TRUE si la ligne représente le coût d'un retry (NFR-003) |
| `error_detail` | `JSONB` | NULL | Si `validation_error` : `{field, received, expected}` ; si `handler_error` : `{type, message}` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | Horodatage de l'insertion |

### Index

- PRIMARY KEY `(id)`.
- INDEX `(account_id, created_at DESC)` — accès admin trié par tenant.
- INDEX `(thread_id, created_at DESC)` — vue par fil.
- INDEX `(tool_name, status)` — agrégation pour eval (F35).

### RLS

```sql
ALTER TABLE tool_call_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_call_log FORCE ROW LEVEL SECURITY;

CREATE POLICY tool_call_log_tenant_isolation ON tool_call_log
  USING (account_id = current_setting('app.account_id', true)::uuid);
```

### Append-only (P3)

- Aucune fonction du code ne fait `UPDATE` ni `DELETE` sur cette table.
- Test introspecte `app/` et vérifie qu'aucun `update(ToolCallLog)` / `delete(ToolCallLog)` n'apparaît.

### Rétention (clarification Q3)

- 12 mois append-only en stockage chaud.
- Au-delà : tâche batch externe (out of MVP scope) ; F14 n'introduit ni purge ni archivage automatique.

### Volumes attendus

- ~10 PME × ~5 messages × ~2 tools = **~100 lignes/jour** en MVP.
- ~36 500 lignes à 12 mois — aucun risque de saturation.

## Schémas Pydantic exposés (F14)

Dans `backend/app/orchestrator/schemas.py` (créé via tasks T2/T3) :

- `ToolCallLogCreate` (insertion interne) — strict `extra='forbid'`.
- `ToolCallLogRead` (admin GET) — tous champs.
- `ToolCallStatus = Literal['ok', 'validation_error', 'handler_error', 'timeout']`.
- `ValidationErrorDetail = {field: str, received: Any, expected: str}`.

## Diagramme

```
chat_thread (F13)
    │ 1
    │ N
    └──< chat_message (F13)
              │ 0..1
              │ N
              └──< tool_call_log  (F14, NOUVEAU)
```

## Migration Alembic

Fichier : `backend/alembic/versions/20260429_xxxx_add_tool_call_log.py`.

Opérations : `op.create_table`, `op.create_index` ×3, `op.execute("ALTER TABLE ... ENABLE ROW LEVEL SECURITY")`, `op.execute("CREATE POLICY ...")`. `downgrade()` : `op.execute("DROP POLICY ...")`, `op.drop_index` ×3, `op.drop_table`. Pas de suppression de données existantes (table neuve).
