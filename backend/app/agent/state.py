"""F53 / FR-002 — ``AgentState`` Pydantic v2 strictement validé.

Référence : ``specs/053-agent-langgraph-core/data-model.md`` section 1.

Tous les sous-types utilisent ``model_config = ConfigDict(extra='forbid')``
afin que toute clé inattendue (y compris hallucinations LLM) soit rejetée.

Le ``thread_id`` est validé contre la regex ``^[0-9a-f-]{36}:[0-9a-f-]{36}$``
qui matche le format composite ``{account_uuid}:{conv_uuid}`` (cf. Q2 clarif).
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Types simples + helpers thread_id
# ---------------------------------------------------------------------------

ThreadId = str
"""Alias sémantique : un ``thread_id`` composite ``{account_uuid}:{conv_uuid}``."""

_THREAD_ID_RE = re.compile(r"^[0-9a-f-]{36}:[0-9a-f-]{36}$")


def validate_thread_id_format(thread_id: str) -> None:
    """Lève ``ValueError`` si ``thread_id`` ne matche pas le format composite.

    Format attendu : ``<uuid>:<uuid>`` (séparateur ``:``, deux UUID v4 lowercase).
    """
    if not _THREAD_ID_RE.match(thread_id):
        raise ValueError(
            "thread_id format invalide ; attendu '<account_uuid>:<conv_uuid>'"
        )


def compose_thread_id(*, account_id: UUID, conv_id: UUID) -> str:
    """Compose un ``thread_id`` à partir de deux UUID."""
    return f"{account_id}:{conv_id}"


def extract_account_prefix(thread_id: str) -> UUID:
    """Extrait l'``account_id`` UUID préfixe d'un ``thread_id`` composite.

    Lève ``ValueError`` si le format est invalide ou le préfixe non parseable.
    """
    validate_thread_id_format(thread_id)
    prefix, _, _ = thread_id.partition(":")
    return UUID(prefix)


# ---------------------------------------------------------------------------
# Énumérations
# ---------------------------------------------------------------------------


class Intent(StrEnum):
    """Intent classifié par le nœud ``route`` (FR-004).

    Aligné avec ``app.orchestrator.schemas.Intent`` (Literal). Utilisé en
    StrEnum dans le state pour refléter la sémantique close.
    """

    PROFILAGE = "profilage"
    MUTATION = "mutation"
    ANALYSE = "analyse"
    AIDE = "aide"
    NAVIGATION = "navigation"
    AUTRE = "autre"
    QUESTION_FERMEE = "question_fermee"


class DispatchCategory(StrEnum):
    """Catégorisation du dispatcher (FR-007).

    - ``SSE_ONLY``  : ``ask_*``, ``show_*`` → SSE event vers le frontend.
    - ``DB_MUTATION``: ``update_*``, ``create_*``, ``delete_*`` → écriture DB+audit.
    - ``REINVOKE_LLM``: ``cite_source``, ``search_source``, ``recall_history``
      → résultat injecté en ``ToolMessage`` puis re-routage vers ``call_llm``.
    """

    SSE_ONLY = "sse_only"
    DB_MUTATION = "db_mutation"
    REINVOKE_LLM = "reinvoke_llm"


class ToolCategory(StrEnum):
    """F55 catégorie déclarative d'un tool (FR-002).

    Mapping vers ``DispatchCategory`` :
    - ``ASK``     → ``SSE_ONLY`` (bottom sheet F39)
    - ``SHOW``    → ``SSE_ONLY`` (viz inline F40)
    - ``MUTATION``→ ``DB_MUTATION`` (UPDATE + audit + EventBus)
    - ``READ``    → ``REINVOKE_LLM`` (résultat sérialisé → ToolMessage)
    """

    ASK = "ask"
    SHOW = "show"
    MUTATION = "mutation"
    READ = "read"


def map_tool_to_dispatch_category(tc: ToolCategory) -> DispatchCategory:
    """Mappe ``ToolCategory`` (déclaratif) → ``DispatchCategory`` (runtime)."""
    if tc in (ToolCategory.ASK, ToolCategory.SHOW):
        return DispatchCategory.SSE_ONLY
    if tc == ToolCategory.MUTATION:
        return DispatchCategory.DB_MUTATION
    return DispatchCategory.REINVOKE_LLM


# ---------------------------------------------------------------------------
# Sous-types Pydantic
# ---------------------------------------------------------------------------


class ContextJson(BaseModel):
    """Contexte de page transmis par F13 au runner (FR-002)."""

    model_config = ConfigDict(extra="forbid")

    page_route: str = Field(min_length=1)
    entity_id: UUID | None = None
    mode: Literal["read", "edit"] = "read"
    locale: Literal["fr", "en"] = "fr"


class ToolCall(BaseModel):
    """Tool call brut extrait du LLM (avant validation)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    arguments: dict[str, Any]


class ValidatedToolCall(BaseModel):
    """Tool call validé Pydantic strict (P9, FR-006)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    id: str
    name: str
    # arguments est un BaseModel typé selon le schéma du tool
    arguments: BaseModel
    schema_version: str = "v1"


class ToolDispatchResult(BaseModel):
    """Résultat du dispatcher (FR-007 / F55 enrichi).

    Variantes mutuellement exclusives via ``kind`` :
    - ``frontend_event``  : ASK / SHOW (output = arguments validés)
    - ``mutation_result`` : MUTATION (entity_type/entity_id/fields_updated/audit_log_id)
    - ``tool_message``    : READ (output['content'] = JSON sérialisé)
    - ``error``           : erreur fail-safe (error_summary obligatoire)
    """

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    tool_name: str
    category: DispatchCategory
    status: Literal[
        "ok",
        "error",
        "skipped",
        "rate_limited",
        "cancelled_by_user",
        "confirmation_expired",
        "pending_confirmation",
    ]
    kind: Literal[
        "frontend_event", "mutation_result", "tool_message", "error"
    ] | None = None
    output: dict[str, Any] | None = None
    error_summary: str | None = None
    db_audit_id: UUID | None = None
    # F55 — mutation_result enrichis
    entity_type: str | None = None
    entity_id: UUID | None = None
    fields_updated: list[str] | None = None
    audit_log_id: UUID | None = None
    is_dry_run: bool = False
    duration_ms: int | None = None

    @model_validator(mode="after")
    def _kind_consistency(self) -> ToolDispatchResult:
        """Cohérence kind ↔ champs (FR-003)."""
        if self.kind == "mutation_result" and self.status == "ok":
            if not (self.entity_type and self.entity_id):
                raise ValueError(
                    "mutation_result requires entity_type+entity_id when status=ok"
                )
        if self.kind == "error" and self.status != "ok":
            if not self.error_summary:
                raise ValueError("error kind requires error_summary")
        return self


class MutationResult(BaseModel):
    """Retour standardisé d'un handler ``@mutation_handler`` (F55 / FR-006)."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str
    entity_id: UUID
    fields_updated: list[str] = Field(default_factory=list)
    snapshot: dict[str, Any] | None = None
    audit_log_id: UUID | None = None


class RateLimitDecision(BaseModel):
    """Décision du rate limiter (FR-010)."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    remaining: int = 0
    reset_at: datetime | None = None
    reason: Literal["ok", "exceeded", "store_unavailable"] = "ok"


class PendingConfirmation(BaseModel):
    """Confirmation en attente (FR-012). Persistée dans agent_run.metadata."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    expires_at: datetime


_AGENT_ERROR_CODES = Literal[
    "validation_error",
    "dispatch_error",
    "llm_error",
    "timeout",
    "cancelled",
    "internal",
]


class AgentError(BaseModel):
    """Erreur accumulée durant un tour (FR-002)."""

    model_config = ConfigDict(extra="forbid")

    node_name: str
    code: _AGENT_ERROR_CODES
    message: str
    details: dict[str, Any] | None = None
    retriable: bool = False


# ---------------------------------------------------------------------------
# Reducers LangGraph
# ---------------------------------------------------------------------------


def _append(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    """Reducer LangGraph : concatène deux listes (None-safe).

    Utilisé pour les listes que les nœuds enrichissent en append-only :
    ``tool_calls``, ``validated_calls``, ``dispatch_results``, ``errors``.
    """
    base: list[Any] = list(left) if left else []
    if right:
        base.extend(right)
    return base


# ---------------------------------------------------------------------------
# AgentState (FR-002)
# ---------------------------------------------------------------------------


class AgentState(BaseModel):
    """Structure d'état circulant dans le graph LangGraph (FR-002).

    Strictement validé Pydantic v2 (``extra='forbid'``).
    """

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    # Identité multi-tenant ----------------------------------------------------
    thread_id: str
    account_id: UUID
    user_id: UUID

    # Entrée utilisateur -------------------------------------------------------
    user_message: str = Field(min_length=1, max_length=4000)
    context_json: ContextJson

    # Routing ------------------------------------------------------------------
    intent: Intent | None = None

    # Prompt système (alimenté par F54) ---------------------------------------
    system_prompt: str = ""

    # Historique LangChain -----------------------------------------------------
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Tools sélectionnés pour ce tour (≤ LLM_AGENT_MAX_TOOLS) -----------------
    available_tools: list[str] = Field(default_factory=list)

    # Réponse LLM courante (avant validation) ----------------------------------
    llm_response_text: str = ""

    # Tool calls accumulés -----------------------------------------------------
    tool_calls: Annotated[list[ToolCall], _append] = Field(default_factory=list)
    validated_calls: Annotated[list[ValidatedToolCall], _append] = Field(
        default_factory=list
    )
    dispatch_results: Annotated[list[ToolDispatchResult], _append] = Field(
        default_factory=list
    )

    # Texte assistant final ----------------------------------------------------
    final_text: str = ""

    # Compteurs ----------------------------------------------------------------
    retry_count: int = Field(default=0, ge=0)
    reinvoke_count: int = Field(default=0, ge=0)

    # F55 — Compteurs / mode dispatch ------------------------------------------
    tool_calls_count_in_turn: int = Field(default=0, ge=0)
    dry_run: bool = False
    pending_confirmations: dict[str, PendingConfirmation] = Field(default_factory=dict)
    agent_run_id: UUID | None = None

    # Erreurs accumulées -------------------------------------------------------
    errors: Annotated[list[AgentError], _append] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("thread_id")
    @classmethod
    def _check_thread_id(cls, v: str) -> str:
        validate_thread_id_format(v)
        return v


__all__ = [
    "AgentError",
    "AgentState",
    "ContextJson",
    "DispatchCategory",
    "Intent",
    "MutationResult",
    "PendingConfirmation",
    "RateLimitDecision",
    "ThreadId",
    "ToolCall",
    "ToolCategory",
    "ToolDispatchResult",
    "ValidatedToolCall",
    "compose_thread_id",
    "extract_account_prefix",
    "map_tool_to_dispatch_category",
    "validate_thread_id_format",
]
