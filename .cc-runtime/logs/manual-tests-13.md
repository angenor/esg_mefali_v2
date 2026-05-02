# F13 — Manual tests log (deferred from automated run)

## DB environment blocker

L'environnement Postgres dockerisé partagé (`esg_mefali_postgres`, volume
`esg_mefali_pgdata`) contient un schéma d'un autre projet
(`alembic_version='018_interactive'`, tables `action_items, conversations,
documents, fund_applications, ...`). Aucune table F01-F11 (`account_user`,
`chat_message`, `entreprise`, ...) n'existe.

→ Les tests d'intégration `tests/chat/test_threads_api.py` et
   `tests/chat/test_messages_api.py` ne peuvent pas s'exécuter car
   `account_user` et `chat_thread` n'existent pas dans la base.

→ Le `make db-reset` est nécessaire pour repartir d'un état propre :
   ```
   make db-reset   # drop volume + alembic upgrade head
   ```
   (orchestrateur — à valider hors session F13 car non destructif sur du code
   production mais drop des données de l'autre projet).

## Tests F13 jouables manuellement après db-reset

1. Login PME, capture JWT.
2. `POST /me/chat/threads` → 201, titre par défaut "Conversation du JJ/MM/AAAA".
3. `POST /me/chat/threads/{id}/messages` `{content:"bonjour", context_json:{page:"/"}}`
   → SSE stream avec `text_delta` + `message_done`. En mode stub (`LLM_STUB=1`),
   le contenu est `[F13 stub: LLM non configuré]`.
4. `GET /me/chat/threads/{id}/messages` → 2 lignes (user + assistant), `context_json`
   non-null sur la ligne user.
5. `POST` avec `context_json:{secret:"x"}` → 422.
6. `POST` avec `content` > 32 KB → 413/422.
7. `DELETE /me/chat/threads/{id}` → 204, puis `POST messages` → 409 `thread_archived`.
8. Tenant B `GET /me/chat/threads/{id_de_A}/messages` → 404.
9. `GET /me/events` ouvre une SSE persistante. `await event_bus.publish(...)`
   pousse l'événement uniquement aux abonnés du même `account_id`.

## Tests automatiques exécutés

- `pytest tests/chat/test_event_bus.py tests/chat/test_schemas.py` → **7/7 passed**
  (unitaires : EventBus pub/sub, isolation cross-tenant, schemas Pydantic
  whitelist + size limits).
- `ruff check app/chat tests/chat` → **All checks passed**.
- `pytest tests/unit/` (existant) → **248 passed** (pas de régression sur F01-F11).

## Couverture mesurée (unitaires uniquement)

`pytest --cov=app/chat tests/chat/test_event_bus.py tests/chat/test_schemas.py` :
- `event_bus.py` 90%, `schemas.py` 97%, `__init__.py` 100%.
- `api.py`/`service.py`/`repository.py`/`llm_stream.py`/`embedding_task.py`
  ≈ 30-40 % (DB-dependent, à compléter via les tests d'intégration une fois
  la DB nettoyée).
