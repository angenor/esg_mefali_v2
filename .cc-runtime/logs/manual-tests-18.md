# F18 — Manual tests log

**Date**: 2026-04-29
**Branch**: `018-llm-memory-context`

## Périmètre livré (MVP minimal vert)

- US1 (P1) : Profil entreprise + projets injectés à chaque tour — implémenté.
- US2 (P1) : Budget tokens contrôlé + compaction R4 — implémenté + testé unit.
- US3 (P1) : 15 derniers messages préservés — implémenté + testé unit.
- US4 (P2) : Tool `recall_history` enregistré au registry, exécution mockée
  testée. Test d'intégration pgvector (cosinus + RLS) à valider en
  environnement avec Postgres dispo.
- US5 (P1) : Embedding payload `label/title` (FR-008) — implémenté dans
  `embedding_task.py` + testé via `extract_embedding_text`.
- US6 (P1) : Sync édition manuelle (no cache) — testé via
  `test_freshness_no_cache_between_calls`.

## Tests automatiques

```bash
cd backend && source .venv/bin/activate
pytest -q --cov=app/chat/memory tests/chat/memory/
# 91 passed, coverage 92.19% (>= 80% requis)
ruff check app/chat/memory/ tests/chat/memory/
# All checks passed!
```

## Smoke test manuel (ContextBundle)

À exécuter en environnement avec Postgres + entreprise + thread provisionnés :

```python
from uuid import UUID
from app.db import SessionLocal
from app.chat.memory.context_builder import build_context

db = SessionLocal()
bundle = build_context(
    db,
    account_id=UUID("00000000-0000-0000-0000-000000000001"),
    thread_id=UUID("00000000-0000-0000-0000-000000000010"),
)
print(bundle.to_system_message())
print(f"tokens estimés : {bundle.estimated_tokens}")
print(f"expose recall_history : {bundle.expose_recall_history}")
```

## Migration alembic

Migration `0013_f18_chat_message_embedding_index.py` créée :

```sql
CREATE INDEX IF NOT EXISTS idx_chat_message_embedding
  ON chat_message
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
ANALYZE chat_message;
```

À appliquer via `alembic upgrade head`. Rollback `alembic downgrade -1`
supprime simplement l'index.

## Régression F01-F16

- `pytest -q tests/orchestrator/` → 39/39 green (F14 + tool_registry + recall_history nouvellement enregistré).
- `tests/chat/test_messages_api.py` et `test_threads_api.py` échouent
  uniquement à cause de Postgres indisponible (vérifié sur la branche
  pré-F18 par stash : même erreur). **Pas de régression F18**.

## Reportés (post-MVP)

- T029 (branchement `build_context()` dans le flow F14 OpenRouter) :
  laissé pour une PR ciblée afin d'éviter de toucher la composition
  conversation actuelle. Tous les composants sont prêts à l'emploi.
- Test d'intégration pgvector réel sur 50 messages (SC-002 perf p95) :
  nécessite Postgres + extension activée + données de test.
