# Quickstart — F56 Agent Sourcing Enforcement

**Audience**: backend dev intégrant F56 dans un environnement local.

## Prereqs

- F53 (LangGraph core) merged on main — provides `app/agent/graph.py`, state, checkpointer.
- F54 (context-builder) merged — provides `app/agent/prompts/identity.py` + `invariants.py`.
- F55 (dispatcher) merged — provides `app/agent/dispatcher.py`, `sse_bridge.py`, `tool_call_log` table.
- F03 / F07 — `source` table populated with at least 10 verified sources (one ADEME, one BOAD, one GCF for testing).
- Voyage AI `VOYAGE_API_KEY` set in `.env`.

## Local setup

```bash
# 1. Postgres (only Docker service)
make db-up
docker compose ps  # ensure healthy

# 2. Apply F56 migration
cd backend && source .venv/bin/activate
alembic upgrade head  # should land at 0035_f56_unsourced_flag_and_sourcing_columns

# 3. Verify schema
psql -h localhost -U postgres -d esg_mefali -c '\d unsourced_flag'
psql -h localhost -U postgres -d esg_mefali -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'agent_run' AND column_name = 'sourcing_status'"
psql -h localhost -U postgres -d esg_mefali -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'chat_message' AND column_name = 'sources'"

# 4. Verify pgvector index on source.embedding
psql -h localhost -U postgres -d esg_mefali -c "\di+ source*"

# 5. Set sourcing mode (defaults to strict)
echo "LLM_AGENT_SOURCING_MODE=permissive" >> .env  # for local dev

# 6. Backend
make backend
# uvicorn app.main:app --reload --port 8010

# 7. Frontend
make frontend
# nuxt dev --port 3001
```

## Smoke test (manual)

```bash
# 1. Open chat F41 at http://localhost:3001/chat
# 2. Send: "Quel est le facteur ADEME pour le diesel ?"
# 3. Expect: assistant calls search_source → cite_source → composes a sourced response.
# 4. Inspect SSE stream:
curl -N http://localhost:8010/v1/agent/runs/{run_id}/stream
# events:
#  data: {"event":"text_delta","data":{"chunk":"Le facteur ADEME"}}
#  ...
#  data: {"event":"message_done","data":{"message_id":"...","sources":[{"source_id":"...","title":"ADEME Base Carbone","citation_index":1,...}]}}
```

## Three modes — runtime behavior

### Mode `strict` (default prod)

```text
turn 0:
  user: "Le seuil GCF pour les PME est de combien ?"
  LLM: emits "Le seuil GCF pour les PME est de 50 M USD."
  validator detects 1 unsourced claim → decision=retry
  retry msg appended: "Tu as affirmé un seuil sans citer. Utilise cite_source ou flag_unsourced ou reformule."
  state.sourcing_retry_count = 1

turn 1 (retry):
  LLM: emits "Le seuil GCF pour les PME est de 50 M USD." + cite_source(source_id=GCF-PSGI-2023)
  validator passes → decision=accept
  agent_run.sourcing_status = 'retried_ok'
  message_done: payload.sources = [{source_id: GCF-PSGI-2023, ...}]
```

### Mode `permissive` (staging/dev)

```text
turn 0:
  user: same question
  LLM: emits unsourced claim
  validator: decision=annotate
  auto-flag rollup: INSERT into unsourced_flag (ON CONFLICT DO NOTHING)
  SSE: emit unsourced_claim event with span
  message_done: payload.sources = [], degraded=true
  Frontend: yellow warning chip on the unsourced span
```

### Mode `off` (CI tests)

```text
validator does not run.
Frontend renders message normally without any source chips.
WARNING: refused at boot if ENVIRONMENT=production.
```

## How to add a verified Source for testing

```sql
-- Postgres psql (admin role)
SET ROLE app_admin;
INSERT INTO source
  (id, url, canonical_url, title, publisher, version, date_publi, page, section,
   captured_at, captured_by, verified_by, verified_at, verification_status,
   embedding, status_version, created_at, updated_at)
VALUES
  (gen_random_uuid(),
   'https://base-carbone.ademe.fr/diesel-2024',
   'https://base-carbone.ademe.fr/diesel-2024',
   'ADEME Base Carbone v23.5 — Diesel',
   'ADEME',
   '23.5',
   '2024-01-15',
   'p.45',
   'Diesel',
   now(), '<admin-user-uuid>', '<admin-user-uuid>', now(),
   'verified',
   array_fill(0.01, ARRAY[1024])::vector,  -- placeholder embedding (replace with real Voyage)
   1, now(), now()
  );
```

For the embedding column, in real flow use `app.embeddings_client.embed(query='ADEME Base Carbone diesel')` to get a 1024-dim Voyage vector.

## Test the validator

```bash
cd backend && source .venv/bin/activate
pytest tests/unit/test_sourcing_detector.py -v
pytest tests/unit/test_sourcing_validator.py -v
pytest tests/integration/test_compose_response_retry.py -v
pytest tests/integration/test_sourcing_e2e_strict.py -v
pytest tests/perf/test_sourcing_perf.py -v -m perf  # NFR-001/008
pytest tests/llm_eval/sourcing_eval.py -v           # FR-015 / NFR-003 — golden set
```

## Inspect metrics

```bash
# As admin (Bearer token from /admin/auth)
curl -H "Authorization: Bearer <admin-token>" http://localhost:8010/admin/agent/metrics/sourcing?period=7d
```

## Frontend visual check

- Chat at `http://localhost:3001/chat` :
  - Send a sourceable question.
  - Inspect the assistant message — superscripts numbered `¹²³` should appear after cited spans.
  - Click a superscript → popover with title, publisher, URL, "Ouvrir le PDF" button.
- Extension sidepanel (F52) `chrome://extensions/` :
  - Open sidepanel ; same chat behavior, simplified rendering.

## Troubleshooting

| Symptom                                          | Likely cause / fix                                                             |
|--------------------------------------------------|--------------------------------------------------------------------------------|
| `LLM_AGENT_SOURCING_MODE=off` rejected at boot   | Set `ENVIRONMENT=dev` in `.env` for local dev, or use `permissive`.            |
| `cite_source(source_id=...)` returns `source_not_found` | Source not in DB; insert one (see above) or use search_source.          |
| `cite_source(...)` returns `source_unverified`   | Source exists but status = `pending`/`outdated`; admin must verify in F07 UI.  |
| `search_source` returns `degraded=true`          | Voyage API down; ILIKE fallback used. Check `VOYAGE_API_KEY` and network.       |
| Validator latency > 100 ms                       | Profile with `pytest tests/perf -k validator`. Likely whitelist regex compilation; cache should be at module level. |
| `unsourced_flag` INSERT fails with duplicate     | Expected (dedup ON CONFLICT). Check that the SQL uses `ON CONFLICT DO NOTHING`. |
| Frontend chips not rendering                     | Check `payload.sources` in DevTools Network → SSE stream. If empty, validator did not run or `cite_source` was not invoked. |

## Roll back

```bash
cd backend && source .venv/bin/activate
alembic downgrade 0034_f55_audit_tool_call_extensions
```

This drops `unsourced_flag`, removes `agent_run.sourcing_status`, removes `chat_message.sources`, drops embedding indexes. Idempotent.
