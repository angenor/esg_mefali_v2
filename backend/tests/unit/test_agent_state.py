"""F53 / T009 — Tests unitaires pour ``app/agent/state.py``.

Couvre FR-002 (AgentState extra='forbid', types stricts).
"""

from __future__ import annotations

import re
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.agent.state import (
    AgentError,
    AgentState,
    ContextJson,
    DispatchCategory,
    Intent,
    ThreadId,
    ToolCall,
    ToolDispatchResult,
    compose_thread_id,
    validate_thread_id_format,
)

pytestmark = pytest.mark.unit


def _valid_thread_id() -> str:
    return f"{uuid4()}:{uuid4()}"


def _ctx() -> ContextJson:
    return ContextJson(page_route="/profil/projets")


def _state(**overrides) -> AgentState:
    base = {
        "thread_id": _valid_thread_id(),
        "account_id": uuid4(),
        "user_id": uuid4(),
        "user_message": "Bonjour",
        "context_json": _ctx(),
    }
    base.update(overrides)
    return AgentState(**base)


class TestAgentStateExtraForbid:
    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            AgentState(
                thread_id=_valid_thread_id(),
                account_id=uuid4(),
                user_id=uuid4(),
                user_message="hi",
                context_json=_ctx(),
                unknown_field="hack",  # type: ignore[call-arg]
            )

    def test_accepts_minimal_required(self) -> None:
        state = _state()
        assert state.intent is None
        assert state.retry_count == 0
        assert state.errors == []
        assert state.tool_calls == []

    def test_user_message_max_4000_chars(self) -> None:
        with pytest.raises(ValidationError):
            _state(user_message="x" * 4001)

    def test_user_message_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            _state(user_message="")


class TestThreadIdComposite:
    def test_compose_format(self) -> None:
        a = uuid4()
        c = uuid4()
        tid = compose_thread_id(account_id=a, conv_id=c)
        assert tid == f"{a}:{c}"

    def test_validate_valid(self) -> None:
        a = uuid4()
        c = uuid4()
        tid = f"{a}:{c}"
        validate_thread_id_format(tid)  # ne lève pas

    @pytest.mark.parametrize(
        "tid",
        [
            "no-colon",
            "shortprefix:also-short",
            f"{uuid4()}",
            f"{uuid4()}:{uuid4()}:{uuid4()}",
            f"BADBAD:{uuid4()}",
        ],
    )
    def test_validate_invalid_format(self, tid: str) -> None:
        with pytest.raises(ValueError):
            validate_thread_id_format(tid)

    def test_thread_id_field_validates(self) -> None:
        with pytest.raises(ValidationError):
            _state(thread_id="invalid-format")

    def test_state_extracts_account_prefix(self) -> None:
        a = uuid4()
        c = uuid4()
        tid = f"{a}:{c}"
        # state must build cleanly when account_id matches the prefix
        _state(thread_id=tid, account_id=a)
        prefix, _, rest = tid.partition(":")
        assert UUID(prefix) == a
        assert UUID(rest) == c


class TestThreadIdRegex:
    def test_pattern_matches_data_model_constraint(self) -> None:
        # data-model section 4 : ^[0-9a-f-]{36}:[0-9a-f-]{36}$
        pattern = re.compile(r"^[0-9a-f-]{36}:[0-9a-f-]{36}$")
        tid = _valid_thread_id()
        assert pattern.match(tid) is not None


class TestIntent:
    @pytest.mark.parametrize(
        "value",
        [
            "profilage",
            "mutation",
            "analyse",
            "aide",
            "navigation",
            "autre",
            "question_fermee",
        ],
    )
    def test_valid_intents(self, value: str) -> None:
        # Intent est StrEnum ; doit accepter valeur littérale
        Intent(value)

    def test_invalid_intent(self) -> None:
        with pytest.raises(ValueError):
            Intent("hallucinated")


class TestContextJson:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ContextJson(page_route="/", extra_field="hack")  # type: ignore[call-arg]

    def test_default_mode_read(self) -> None:
        ctx = ContextJson(page_route="/profil")
        assert ctx.mode == "read"
        assert ctx.locale == "fr"
        assert ctx.entity_id is None

    def test_locale_constrained(self) -> None:
        with pytest.raises(ValidationError):
            ContextJson(page_route="/", locale="de")  # type: ignore[arg-type]


class TestToolCall:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ToolCall(id="x", name="t", arguments={}, extra=1)  # type: ignore[call-arg]

    def test_arguments_dict(self) -> None:
        tc = ToolCall(id="call_1", name="ask_qcu", arguments={"label": "go"})
        assert tc.arguments == {"label": "go"}


class TestDispatchCategory:
    def test_str_values(self) -> None:
        assert DispatchCategory.SSE_ONLY == "sse_only"
        assert DispatchCategory.DB_MUTATION == "db_mutation"
        assert DispatchCategory.REINVOKE_LLM == "reinvoke_llm"


class TestToolDispatchResult:
    def test_minimal(self) -> None:
        r = ToolDispatchResult(
            tool_call_id="x",
            tool_name="ask_qcu",
            category=DispatchCategory.SSE_ONLY,
            status="ok",
        )
        assert r.output is None
        assert r.error_summary is None

    def test_status_constrained(self) -> None:
        with pytest.raises(ValidationError):
            ToolDispatchResult(
                tool_call_id="x",
                tool_name="t",
                category=DispatchCategory.SSE_ONLY,
                status="bogus",  # type: ignore[arg-type]
            )


class TestAgentError:
    def test_default_retriable_false(self) -> None:
        e = AgentError(node_name="route", code="internal", message="oops")
        assert e.retriable is False

    def test_invalid_code(self) -> None:
        with pytest.raises(ValidationError):
            AgentError(node_name="route", code="not-a-real-code", message="x")  # type: ignore[arg-type]


class TestStateReducers:
    def test_messages_default_empty(self) -> None:
        state = _state()
        assert state.messages == []

    def test_dispatch_results_default_empty(self) -> None:
        state = _state()
        assert state.dispatch_results == []


class TestThreadIdAlias:
    def test_threadid_type_alias_present(self) -> None:
        assert ThreadId is str
