# F14 — Quickstart

## Activer le pipeline en local

```bash
cd backend
source .venv/bin/activate
export LLM_STUB=1                # mode sans appel LLM réel (par défaut en tests)
export F14_PIPELINE_ENABLED=1    # active le pipeline F14
uvicorn app.main:app --reload --port 8000
```

Pour utiliser un vrai modèle :

```bash
export LLM_STUB=0
export LLM_API_KEY="sk-or-..."
export LLM_BASE_URL="https://openrouter.ai/api/v1"
export LLM_MODEL="minimax/minimax-m2.7"
```

## Déclarer un tool

```python
# backend/app/orchestrator/fixtures_tools.py
from pydantic import BaseModel, ConfigDict, Field
from app.orchestrator.tool_registry import tool


class ShowSummaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=120)
    bullets: list[str] = Field(..., min_length=1, max_length=5)


@tool(
    name="show_summary_card",
    description="Affiche une carte de synthèse dans le bottom sheet.",
    use_when="L'utilisateur demande un résumé court (3 à 5 points).",
    dont_use_when="L'utilisateur veut une mutation ou une exploration libre.",
    examples_positive=[
        {"title": "Synthèse ESG", "bullets": ["Score 72/100", "Axe E faible"]},
    ],
    examples_negative=[
        {"title": "", "bullets": []},
    ],
    schema=ShowSummaryInput,
)
async def show_summary_card(payload: ShowSummaryInput) -> dict:
    return {"rendered": True, "title": payload.title, "bullets": payload.bullets}
```

Les 5 tools fictifs livrés par F14 (harnais de test) sont dans `app/orchestrator/fixtures_tools.py` :

- `show_summary_card`
- `ask_qcu`
- `ask_yes_no`
- `update_demo_profile`
- `search_demo_source`

## Lancer la suite de tests F14

```bash
cd backend
source .venv/bin/activate
pytest tests/orchestrator/ tests/chat/test_chat_api_pipeline.py -q \
       --cov=app/orchestrator --cov-report=term-missing
```

Cible : couverture ≥ 80 % sur `app/orchestrator/`.

## Lancer le lint

```bash
cd backend
source .venv/bin/activate
ruff check app/ tests/
```

## Migration Alembic

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

## Tester un appel pipeline en bout-en-bout (mode stub)

```bash
curl -N -H "Accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -b "session=..." \
     -d '{"content": "ajoute un projet"}' \
     http://localhost:8000/chat/messages
```

Tu dois voir successivement `thinking`, `tool_call_started`, `tool_call_completed`, `text_delta`, `message_done`.

## Vérifier les logs

```sql
SET app.account_id = '<uuid de votre PME>';
SELECT tool_name, status, retries, latency_ms, created_at
FROM tool_call_log
ORDER BY created_at DESC
LIMIT 20;
```

En dehors d'une session avec `app.account_id` posé, RLS retourne 0 ligne.

## Désactiver le pipeline (rollback rapide)

```bash
export F14_PIPELINE_ENABLED=0
# /chat/messages se comporte comme avant F14
```
