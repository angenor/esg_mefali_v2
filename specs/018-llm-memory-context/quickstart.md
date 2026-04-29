# Quickstart — F18 Mémoire Contextuelle LLM

**Date**: 2026-04-29

## Pré-requis

- Backend F13 fonctionnel (chat threads + messages, BackgroundTask embeddings).
- Backend F11 + F12 fonctionnels (profil entreprise + projets).
- Backend F14 fonctionnel (orchestrateur + tool_registry).
- PostgreSQL avec extension `pgvector` activée (table `chat_message.embedding VECTOR(1024)`).
- Variable d'environnement `VOYAGE_API_KEY` exportée pour les tests d'intégration.

## Étapes locales

```bash
cd backend
source .venv/bin/activate

git checkout 018-llm-memory-context

# Aucune nouvelle dépendance F18 (embeddings_client.py et SQLAlchemy déjà installés)

# Appliquer la migration (ajout index ivfflat)
alembic upgrade head

# Vérifier l'index
psql "$DATABASE_URL" -c "\\d chat_message" | grep ivfflat

# Lancer les tests F18
pytest -q --cov=app/chat/memory tests/chat/memory/

# Lint
ruff check app/chat/memory/ tests/chat/memory/
```

## Smoke test manuel

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
print(f"tokens: {bundle.estimated_tokens}")
print(f"expose_recall_history: {bundle.expose_recall_history}")
```

Sortie attendue : un markdown lisible avec les trois sections, un nombre de tokens ≤ 2 000, et un flag selon le volume du thread.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `CONTEXT_TOKEN_BUDGET` | `2000` | Budget tokens du contexte LLM |
| `VOYAGE_API_KEY` | (requis) | Clé d'embedding Voyage AI |
| `VOYAGE_TIMEOUT_SECONDS` | `30` | Timeout HTTP embeddings |

## Vérifier l'intégration F14 (sélecteur d'outils)

Sur un thread de 16+ messages, le tool `recall_history` doit apparaître dans la liste sélectionnée par `app.orchestrator.tool_selector.select_tools()`. Sur un thread de 15 ou moins, il doit être absent.

```bash
pytest -q tests/chat/memory/test_recall_history.py::test_gating_below_threshold
pytest -q tests/chat/memory/test_recall_history.py::test_gating_above_threshold
```

## Commandes utiles

```bash
# Mesurer la latence build_context sur jeu de test
pytest -q tests/chat/memory/test_context_builder.py::test_perf_p95 -s

# Coverage focus F18
pytest --cov=app/chat/memory --cov-report=term-missing tests/chat/memory/
```

## Rollback

La migration `0013_f18_chat_message_embedding_index` est purement additive (création d'index). Le rollback supprime l'index sans perte de données :

```bash
alembic downgrade -1
```
