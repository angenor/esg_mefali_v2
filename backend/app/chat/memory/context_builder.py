"""F18 — Constructeur de contexte LLM (build_context).

Assemble à chaque tour le bundle injecté en system message :

- profil entreprise compact (lecture F11, sans cache),
- projets actifs compacts (lecture F12, sans cache),
- 15 derniers messages user/assistant du thread courant.

Respecte FR-009 (pas de cache) et FR-014 (deny-by-default sur les champs
sensibles via les compactors).

Le rendu markdown final est délégué à :func:`render_bundle` (testable
indépendamment) et la compaction sous budget à
:func:`app.chat.memory.compactors.fit_to_budget`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.chat.memory.compactors import (
    DEFAULT_DESC_LIMIT,
    DEFAULT_MAX_PROJECTS,
    compact_profile,
    compact_projets,
    extract_embedding_text,
    fit_to_budget,
)

DEFAULT_RECENT_LIMIT: int = 15
RECALL_HISTORY_THRESHOLD: int = 15
DEFAULT_TOKEN_BUDGET: int = 2000
MAX_MESSAGE_CONTENT_CHARS: int = 4000


@dataclass(frozen=True)
class ChatMessageView:
    """Vue immuable d'un message pour l'injection contexte.

    ``content`` est éventuellement tronqué (avec marqueur ``[…tronqué…]``)
    si le message original dépasse :data:`MAX_MESSAGE_CONTENT_CHARS`.
    ``payload_label`` est extrait via
    :func:`app.chat.memory.compactors.extract_embedding_text`.
    """

    role: str
    content: str
    payload_label: str | None
    created_at: datetime


@dataclass(frozen=True)
class ContextBundle:
    """Bundle complet retourné par :func:`build_context`."""

    profile: dict[str, Any] | None
    projets: tuple[dict[str, Any], ...]
    recent_messages: tuple[ChatMessageView, ...]
    estimated_tokens: int
    expose_recall_history: bool
    raw_messages_count: int = 0

    def to_system_message(self) -> str:
        """Rendu markdown final injecté en tête de la conversation OpenRouter."""
        return render_bundle(
            self.profile,
            list(self.projets),
            [_view_to_dict(m) for m in self.recent_messages],
        )


# --- Repository helpers (lecture sans cache, FR-009) ---


def _read_profile(db: Session, account_id: UUID) -> dict[str, Any] | None:
    """Lit le profil entreprise via F11 (sans cache)."""
    try:
        from app.entreprise import service as entreprise_service
        from app.entreprise.service import _select_one as entreprise_select_one
    except Exception:
        return None

    try:
        row = entreprise_select_one(db, account_id=account_id)
    except Exception:
        return None
    if row is None:
        return None
    try:
        agg = entreprise_service.aggregate_read(db, row)
    except Exception:
        return _row_to_dict(row)
    return agg if isinstance(agg, dict) else _row_to_dict(row)


def _read_projets(db: Session, account_id: UUID) -> list[dict[str, Any]]:
    """Lit la liste des projets via F12 (sans cache)."""
    try:
        from app.projets import service as projets_service
    except Exception:
        return []

    try:
        rows = projets_service.list_projets(db, account_id=account_id)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if isinstance(row, dict):
            out.append(row)
        else:
            out.append(_row_to_dict(row))
    return out


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Best-effort conversion d'une dataclass / row mapping en dict."""
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "_asdict"):
        return dict(row._asdict())
    if hasattr(row, "__dict__"):
        return {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return {}


def _read_recent_messages(
    db: Session,
    *,
    thread_id: UUID,
    account_id: UUID,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Lit les ``limit`` derniers messages user/assistant + le total."""
    from app.chat import repository as chat_repo

    if hasattr(chat_repo, "list_recent_messages"):
        recent = chat_repo.list_recent_messages(  # type: ignore[attr-defined]
            db, thread_id=thread_id, account_id=account_id, limit=limit
        )
    else:
        recent = chat_repo.list_messages(
            db, thread_id=thread_id, account_id=account_id, limit=limit
        )

    if hasattr(chat_repo, "count_messages_in_thread"):
        total = int(
            chat_repo.count_messages_in_thread(  # type: ignore[attr-defined]
                db, thread_id=thread_id, account_id=account_id
            )
        )
    else:
        total = len(recent or [])

    return list(recent or []), total


# --- Construction des views messages ---


def _truncate_content(content: str | None, limit: int = MAX_MESSAGE_CONTENT_CHARS) -> str:
    if not content:
        return ""
    if len(content) <= limit:
        return content
    marker = "[…tronqué…]"
    return content[: limit - len(marker)] + marker


def _build_message_view(message: dict[str, Any]) -> ChatMessageView | None:
    """Filtre les rôles non system et construit une view immuable."""
    role = message.get("role")
    if role not in ("user", "assistant"):
        return None
    raw_content = message.get("content") or ""
    payload_json = message.get("payload_json")
    label: str | None = None
    if isinstance(payload_json, dict) and payload_json:
        extracted = extract_embedding_text("", payload_json)
        label = extracted or None
    created_at = message.get("created_at") or datetime.now(tz=UTC)
    return ChatMessageView(
        role=str(role),
        content=_truncate_content(raw_content),
        payload_label=label,
        created_at=created_at,
    )


def _view_to_dict(view: ChatMessageView) -> dict[str, Any]:
    return {
        "role": view.role,
        "content": view.content,
        "payload_label": view.payload_label,
        "created_at": view.created_at,
    }


# --- Rendu markdown ---


def _format_money(value: Any) -> str:
    """Formate une Money (``{amount, currency}``) ou retourne str(value)."""
    if isinstance(value, dict) and "amount" in value:
        amount = value.get("amount")
        currency = value.get("currency") or ""
        return f"{amount} {currency}".strip()
    return str(value)


def _render_profile_section(profile: dict[str, Any] | None) -> str | None:
    if not profile:
        return None
    lines: list[str] = ["# Profil entreprise"]
    if "raison_sociale" in profile:
        lines.append(f"Raison sociale : {profile['raison_sociale']}")
    if "forme_juridique" in profile:
        lines.append(f"Forme juridique : {profile['forme_juridique']}")
    if "secteur_activite" in profile:
        lines.append(f"Secteur : {profile['secteur_activite']}")
    if "pays" in profile:
        ville = profile.get("ville")
        if ville:
            lines.append(f"Pays / Ville : {profile['pays']} / {ville}")
        else:
            lines.append(f"Pays : {profile['pays']}")
    if "annee_creation" in profile:
        lines.append(f"Année de création : {profile['annee_creation']}")
    if "effectif_total" in profile:
        lines.append(f"Effectif : {profile['effectif_total']} salariés")
    if "chiffre_affaires" in profile:
        lines.append(f"CA : {_format_money(profile['chiffre_affaires'])}")
    if "description_activite" in profile:
        lines.append(f"Description : {profile['description_activite']}")
    if "indicateurs_esg_synthetiques" in profile:
        lines.append(
            f"Indicateurs ESG synthétiques : {profile['indicateurs_esg_synthetiques']}"
        )
    return "\n".join(lines)


def _render_projects_section(projets: list[dict[str, Any]]) -> str | None:
    if not projets:
        return None
    lines: list[str] = ["# Projets actifs"]
    for projet in projets:
        nom = projet.get("nom") or projet.get("id") or "(sans nom)"
        head_parts: list[str] = [f"- {nom}"]
        if projet.get("statut"):
            head_parts.append(str(projet["statut"]))
        if projet.get("secteur"):
            head_parts.append(str(projet["secteur"]))
        if projet.get("pays"):
            head_parts.append(str(projet["pays"]))
        if projet.get("montant_total"):
            head_parts.append(_format_money(projet["montant_total"]))
        lines.append(" — ".join(head_parts))
        if projet.get("description"):
            lines.append(f"  {projet['description']}")
    return "\n".join(lines)


def _render_messages_section(messages: list[dict[str, Any]]) -> str | None:
    if not messages:
        return None
    lines: list[str] = ["# Conversation récente"]
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content") or ""
        label = msg.get("payload_label")
        if label and not content.strip():
            lines.append(f"[{role}] (payload) {label}")
        elif label:
            lines.append(f"[{role}] {content}")
            lines.append(f"  (payload) {label}")
        else:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def render_bundle(
    profile: dict[str, Any] | None,
    projets: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> str:
    """Rend le bundle en markdown lisible (sections optionnelles)."""
    sections: list[str] = []
    profile_section = _render_profile_section(profile)
    if profile_section:
        sections.append(profile_section)
    projects_section = _render_projects_section(projets)
    if projects_section:
        sections.append(projects_section)
    messages_section = _render_messages_section(messages)
    if messages_section:
        sections.append(messages_section)
    return "\n\n".join(sections)


# --- API publique ---


def build_context(
    db: Session,
    *,
    account_id: UUID,
    thread_id: UUID,
    token_budget: int | None = None,
    recent_limit: int = DEFAULT_RECENT_LIMIT,
) -> ContextBundle:
    """Construit le bundle de contexte pour un tour de conversation.

    Args:
        db: session SQLAlchemy (RLS positionnée par le middleware).
        account_id: compte de la session courante.
        thread_id: thread courant (doit appartenir au compte).
        token_budget: budget tokens cible. ``None`` → ``CONTEXT_TOKEN_BUDGET``.
        recent_limit: nombre de messages récents à inclure (défaut 15).

    Returns:
        ContextBundle immuable, ``estimated_tokens`` <= budget.
    """
    budget = token_budget if token_budget is not None else _resolve_budget()

    # Lecture systématique sans cache (FR-009)
    profile_raw = _read_profile(db, account_id)
    projets_raw = _read_projets(db, account_id)
    recent_raw, total_messages = _read_recent_messages(
        db, thread_id=thread_id, account_id=account_id, limit=recent_limit
    )

    profile_compact = compact_profile(profile_raw, desc_limit=DEFAULT_DESC_LIMIT)
    projets_compact = compact_projets(
        projets_raw, max_n=DEFAULT_MAX_PROJECTS, desc_limit=DEFAULT_DESC_LIMIT
    )
    views = tuple(
        v for v in (_build_message_view(m) for m in recent_raw) if v is not None
    )

    # Compaction sous budget (R4)
    messages_dicts = [_view_to_dict(v) for v in views]
    profile_final, projets_final, messages_final, est_tokens = fit_to_budget(
        profile=profile_compact,
        projets=projets_compact,
        messages=messages_dicts,
        render=render_bundle,
        budget=budget,
    )

    # Reconstruire le tuple de views à partir du subset retenu
    views_final = _rebuild_views(views, len(messages_final))

    expose_recall = total_messages > RECALL_HISTORY_THRESHOLD

    return ContextBundle(
        profile=profile_final,
        projets=tuple(projets_final),
        recent_messages=views_final,
        estimated_tokens=est_tokens,
        expose_recall_history=expose_recall,
        raw_messages_count=total_messages,
    )


def _rebuild_views(
    views: tuple[ChatMessageView, ...], target_len: int
) -> tuple[ChatMessageView, ...]:
    """Conserve les ``target_len`` derniers éléments (ordre chronologique)."""
    if target_len >= len(views):
        return views
    return views[-target_len:]


def _resolve_budget() -> int:
    """Résout le budget par défaut depuis la config ou l'env."""
    try:
        from app.config import get_settings

        settings = get_settings()
        budget = getattr(settings, "CONTEXT_TOKEN_BUDGET", None)
        if isinstance(budget, int) and budget > 0:
            return budget
    except Exception:
        pass
    import os as _os

    raw = _os.environ.get("CONTEXT_TOKEN_BUDGET")
    if raw:
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_TOKEN_BUDGET


__all__ = [
    "DEFAULT_RECENT_LIMIT",
    "DEFAULT_TOKEN_BUDGET",
    "RECALL_HISTORY_THRESHOLD",
    "ChatMessageView",
    "ContextBundle",
    "build_context",
    "render_bundle",
]
