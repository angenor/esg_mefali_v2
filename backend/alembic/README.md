# Alembic — ESG Mefali

## Coexistence Alembic / LangGraph (F53)

### Tables LangGraph (gérées hors-Alembic)

Les tables suivantes sont **créées et migrées par la lib
`langgraph-checkpoint-postgres`** via `AsyncPostgresSaver.setup()` au boot
backend (mode `LLM_AGENT_MODE=langgraph`) :

- `checkpoints`
- `checkpoint_blobs`
- `checkpoint_writes`
- `checkpoint_migrations`

**Elles ne DOIVENT JAMAIS être versionnées par Alembic.**
Toute tentative de `op.create_table('checkpoints', ...)` casserait le boot.

### Isolation tenant des checkpoints

Pas de RLS native sur ces tables. L'isolation tenant est garantie par le
**`thread_id` composite** :

```
{account_uuid}:{conv_uuid}
```

Le runner (`backend/app/agent/runner.py`) valide que le préfixe
correspond bien à l'`account_id` de la session avant d'invoquer le
checkpointer. Cf. `backend/app/agent/checkpointer.py:validate_thread_id`.

### Tables append-only F53 (Alembic-managed)

Une seule migration F53 ajoute deux tables d'observabilité :

- `agent_run` (un row par tour de chat)
- `agent_run_step` (un row par exécution de nœud)

Ces tables :
- portent `account_id UUID NOT NULL`
- ont des policies RLS `account_id = current_setting('app.current_account_id')::uuid`
- ont les permissions `UPDATE`/`DELETE` révoquées pour `app_user`
- autorisent `UPDATE` du `completed_at` / `status` / `total_*` final
  uniquement via `SET LOCAL ROLE app_admin` côté runner (cf. data-model section 2)

Cette exception au strict append-only est documentée et testée par
`backend/tests/integration/test_agent_migration.py::test_run_append_only`.

## Conventions générales (toutes features)

- Numérotation séquentielle `00XX_<feature>_<purpose>.py`.
- Une migration linéaire (un seul `down_revision`).
- Toujours `op.execute()` pour DDL Postgres-spécifique (RLS, policies, REVOKE,
  `gen_random_uuid()`, etc.) — Alembic ne sait pas les générer en SQL pur.
- Tester chaque migration en local : `make migrate` après `make db-reset`.
- Idempotence souhaitable : `IF NOT EXISTS` partout où c'est possible.
