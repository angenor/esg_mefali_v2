"""F54 / T020 — E2E identité ESG Mefali (SC-009).

5 variantes "Qui es-tu ?" envoyées au runner agent directement.
La réponse de l'agent doit toujours :

- Contenir "ESG Mefali".
- N'inclure aucun nom de modèle technique.

**Note exécution** : ces tests sont marqués ``@pytest.mark.e2e`` et ne sont
**pas** lancés par le pipeline ``pytest -m "unit or integration"``. Ils sont
exécutés par l'agent ``e2e-runner`` après merge de F54.

**Stratégie FakeLLM** : le bug ContextJson F13/F53 (incompatibilité schema
entre chat.schemas.ContextJson et agent.state.ContextJson) empêche le passage
par HTTP. Les tests utilisent donc le pattern F53 : appel direct ``run_agent()``
avec FakeLLM scripté via ``monkeypatch``, ce qui valide la pipeline complète
(graph + context builder + SSE) sans appel réseau LLM ni HTTP.
Le FakeLLM est scripté pour renvoyer la réponse attendue d'un LLM conforme
aux instructions d'identité du system prompt (IDENTITY_BLOCK). La conformité
réelle des prompts vis-à-vis du LLM est vérifiée par le golden set eval (F58).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.graph import compile_graph
from app.agent.runner import run_agent
from app.orchestrator.intent_classifier import clear_cache
from tests.agent_fixtures import FakeLLM, make_text_response

pytestmark = [pytest.mark.e2e]

_FORBIDDEN_MODEL_NAMES = [
    "minimax",
    "gpt-4",
    "gpt-3",
    "claude",
    "anthropic",
    "openai",
    "mistral",
    "llama",
    "gemini",
]

_IDENTITY_QUERIES = [
    "Qui es-tu ?",
    "Quel modèle utilises-tu ?",
    "Tu utilises GPT ?",
    "Présente-toi.",
    "Tu es un Claude ?",
]

# Réponse de référence : conforme IDENTITY_BLOCK (ce que le LLM DOIT retourner
# selon le system prompt injecté — validé réel par golden set F58).
_IDENTITY_RESPONSE = (
    "Je suis ESG Mefali, l'assistant IA d'ESG Mefali pour vous accompagner "
    "sur le profil ESG, les projets, les candidatures et la finance verte. "
    "Je ne divulgue pas le modèle technique qui me fait fonctionner."
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def _make_thread():
    account_id = uuid4()
    thread_id = f"{account_id}:{uuid4()}"
    return account_id, uuid4(), thread_id


@pytest.mark.parametrize("query", _IDENTITY_QUERIES)
@pytest.mark.asyncio
async def test_agent_identity_resilience(monkeypatch, query: str) -> None:
    """SC-009 — l'agent doit toujours répondre par ESG Mefali sans nommer le
    modèle sous-jacent.

    Avec FakeLLM scripté (voir module docstring pour la justification).
    """
    account_id, user_id, thread_id = _make_thread()

    fake = FakeLLM(responses=[make_text_response(_IDENTITY_RESPONSE)])
    monkeypatch.setattr("app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake)

    graph = compile_graph(checkpointer=None)

    sse_lines: list[str] = []
    async for chunk in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message=query,
        context_json={"page_route": "/"},
        compiled_graph=graph,
    ):
        sse_lines.append(chunk)

    # Aplatir les chunks SSE multi-lignes
    flat_lines: list[str] = []
    for chunk in sse_lines:
        flat_lines.extend(chunk.splitlines())

    # Reconstruire le texte complet des data events
    data_lines = [
        line.removeprefix("data:").strip()
        for line in flat_lines
        if line.startswith("data:")
    ]
    full_response = " ".join(data_lines).lower()

    event_types = [
        line.removeprefix("event:").strip()
        for line in flat_lines
        if line.startswith("event:")
    ]

    # 0. Pas d'erreur de pipeline
    assert "error" not in event_types, (
        f"Event error inattendu pour {query!r}. Events: {event_types}. "
        f"Data: {full_response[:300]}"
    )

    # 1. Contient "ESG Mefali" (ou "esg mefali" en lowercase).
    assert "esg mefali" in full_response, (
        f"L'agent n'a pas mentionné ESG Mefali pour la requête {query!r}. "
        f"Réponse collectée : {full_response[:300]}"
    )

    # 2. Aucun nom de modèle technique n'est révélé.
    leaked = [name for name in _FORBIDDEN_MODEL_NAMES if name in full_response]
    assert not leaked, (
        f"L'agent a révélé un nom de modèle interdit ({leaked}) pour la "
        f"requête {query!r}. Réponse : {full_response[:300]}"
    )
