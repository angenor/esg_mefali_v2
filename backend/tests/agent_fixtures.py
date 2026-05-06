"""F53 — Fixtures et helpers communs aux tests d'agent.

Fournit ``fake_llm_factory`` qui patche ``build_chat_model`` pour retourner
un modèle qui renvoie une séquence de ``AIMessage`` programmable (pas de
call réseau, idempotent — NFR-002).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage


class FakeLLM:
    """Fake LLM scriptable retournant une liste programmable de réponses.

    Compatible avec ``ChatOpenAI.bind_tools`` côté tests : on retourne le
    même objet et ``bind_tools`` est un no-op (le LLM script est défini par le
    test).
    """

    def __init__(self, responses: list[AIMessage] | None = None) -> None:
        self._responses: list[AIMessage] = list(responses or [])
        self._idx = 0

    # ----- Mimic ChatOpenAI shape -----

    @property
    def model_name(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):  # noqa: ARG002
        return self

    async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:  # noqa: ARG002
        if not self._responses:
            return AIMessage(content="")
        if self._idx >= len(self._responses):
            return AIMessage(content="")
        msg = self._responses[self._idx]
        self._idx += 1
        return msg


def make_text_response(text: str) -> AIMessage:
    """Helper : AIMessage texte simple (pas de tool call)."""
    return AIMessage(content=text)


def make_tool_call_response(
    *,
    text: str = "",
    tool_name: str,
    tool_args: dict[str, Any],
    tool_call_id: str | None = None,
) -> AIMessage:
    """Helper : AIMessage avec un tool_call structuré."""
    tcid = tool_call_id or f"call_{uuid4().hex[:8]}"
    return AIMessage(
        content=text,
        tool_calls=[
            {
                "id": tcid,
                "name": tool_name,
                "args": tool_args,
            }
        ],
    )


@pytest.fixture
def fake_llm_factory(monkeypatch):
    """Patch ``app.agent.nodes.call_llm.build_chat_model`` pour retourner un FakeLLM.

    Usage :
        def test_x(fake_llm_factory):
            fake_llm_factory(make_tool_call_response(...))
            # ... le runner utilisera le FakeLLM ...
    """
    fake = FakeLLM()

    def _setup(*responses: AIMessage) -> FakeLLM:
        fake._responses = list(responses)
        fake._idx = 0
        return fake

    def _builder(*args: Any, **kwargs: Any) -> FakeLLM:  # noqa: ARG001
        return fake

    # Patch les usages connus
    monkeypatch.setattr("app.agent.nodes.call_llm.build_chat_model", _builder)

    return _setup


__all__ = [
    "FakeLLM",
    "fake_llm_factory",
    "make_text_response",
    "make_tool_call_response",
]
