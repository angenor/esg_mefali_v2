"""F58 — Kill-switch admin par tool (FR-007, FR-008, FR-009).

Repository pour la table ``agent_tool_status`` + cache TTL 30 s in-memory
afin d'éviter une query par tour. Toute mutation invalide le cache et
journalise dans ``audit_log`` (P3 append-only).

La table est globale (pas de RLS) ; les endpoints admin sont gated par
``require_admin``. Non-admin reçoit 404 (P2 convention).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


_CACHE_TTL_S: Final[float] = 30.0
_DISABLED_CACHE: dict[str, tuple[float, frozenset[str]]] = {}
_CACHE_KEY = "global"  # table globale → 1 seule entrée cache


@dataclass(frozen=True)
class ToolStatusRow:
    """Représentation lecture d'une ligne ``agent_tool_status``."""

    tool_name: str
    enabled: bool
    disabled_at: datetime | None
    disabled_by: UUID | None
    reason: str | None


def _reset_cache() -> None:
    """Réservé aux tests."""
    _DISABLED_CACHE.clear()


def cache_invalidate() -> None:
    """Force l'invalidation du cache (appelé après chaque mutation)."""
    _DISABLED_CACHE.clear()


def get_disabled_tools(db: Session) -> set[str]:
    """Retourne l'ensemble des ``tool_name`` actuellement désactivés.

    Cache TTL 30 s in-memory pour rester sous la barre du tour de chat.
    Best-effort : retourne un set vide si la requête échoue (jamais bloquant).
    """
    cached = _DISABLED_CACHE.get(_CACHE_KEY)
    if cached is not None:
        ts, names = cached
        if (monotonic() - ts) < _CACHE_TTL_S:
            return set(names)
    try:
        rows = (
            db.execute(
                text(
                    "SELECT tool_name FROM agent_tool_status "
                    "WHERE enabled = false"
                )
            )
            .mappings()
            .all()
        )
        names = frozenset(str(r.get("tool_name") or "") for r in rows if r.get("tool_name"))
    except Exception:  # noqa: BLE001
        logger.debug("get_disabled_tools failed", exc_info=True)
        names = frozenset()
    _DISABLED_CACHE[_CACHE_KEY] = (monotonic(), names)
    return set(names)


def disable_tool(
    db: Session,
    tool_name: str,
    *,
    admin_user_id: UUID,
    reason: str,
) -> None:
    """Désactive un tool (INSERT ON CONFLICT UPDATE) + audit log.

    Best-effort sur l'audit (s'il échoue, l'opération principale passe).
    """
    now = datetime.now(UTC)
    try:
        db.execute(
            text(
                """
                INSERT INTO agent_tool_status
                  (tool_name, enabled, disabled_at, disabled_by, reason, updated_at)
                VALUES (:name, false, :now, :uid, :reason, :now)
                ON CONFLICT (tool_name) DO UPDATE SET
                  enabled = false,
                  disabled_at = :now,
                  disabled_by = :uid,
                  reason = :reason,
                  updated_at = :now
                """
            ),
            {
                "name": tool_name,
                "now": now,
                "uid": admin_user_id,
                "reason": reason,
            },
        )
    except Exception:
        logger.exception("disable_tool failed for %s", tool_name)
        raise
    _audit_tool_status(
        db,
        action="disable",
        tool_name=tool_name,
        admin_user_id=admin_user_id,
        reason=reason,
    )
    cache_invalidate()


def enable_tool(
    db: Session,
    tool_name: str,
    *,
    admin_user_id: UUID,
) -> None:
    """Réactive un tool + audit log."""
    now = datetime.now(UTC)
    try:
        db.execute(
            text(
                """
                INSERT INTO agent_tool_status
                  (tool_name, enabled, disabled_at, disabled_by, reason, updated_at)
                VALUES (:name, true, NULL, NULL, NULL, :now)
                ON CONFLICT (tool_name) DO UPDATE SET
                  enabled = true,
                  disabled_at = NULL,
                  disabled_by = NULL,
                  reason = NULL,
                  updated_at = :now
                """
            ),
            {"name": tool_name, "now": now},
        )
    except Exception:
        logger.exception("enable_tool failed for %s", tool_name)
        raise
    _audit_tool_status(
        db,
        action="enable",
        tool_name=tool_name,
        admin_user_id=admin_user_id,
        reason=None,
    )
    cache_invalidate()


def list_tools_status(db: Session) -> list[ToolStatusRow]:
    """Retourne la liste complète des entrées ``agent_tool_status``."""
    try:
        rows = (
            db.execute(
                text(
                    "SELECT tool_name, enabled, disabled_at, disabled_by, reason "
                    "FROM agent_tool_status ORDER BY tool_name"
                )
            )
            .mappings()
            .all()
        )
        return [
            ToolStatusRow(
                tool_name=str(r.get("tool_name") or ""),
                enabled=bool(r.get("enabled")),
                disabled_at=r.get("disabled_at"),
                disabled_by=r.get("disabled_by"),
                reason=r.get("reason"),
            )
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        logger.debug("list_tools_status failed", exc_info=True)
        return []


def _audit_tool_status(
    db: Session,
    *,
    action: str,
    tool_name: str,
    admin_user_id: UUID,
    reason: str | None,
) -> None:
    """Audit log de la mutation kill-switch (best-effort).

    On utilise un SAVEPOINT (BEGIN/EXCEPT/ROLLBACK TO) pour isoler l'éventuelle
    erreur sur audit_log : si l'INSERT échoue (schéma différent, FK), le
    SAVEPOINT est rolled back et la transaction principale (l'upsert
    agent_tool_status) reste valide.
    """
    try:
        with db.begin_nested():
            db.execute(
                text(
                    """
                    INSERT INTO audit_log
                      (account_id, entity_type, entity_id, field,
                       old_value, new_value, source_of_change,
                       timestamp, created_at, updated_at, version)
                    SELECT
                      au.account_id, 'agent_tool_status',
                      gen_random_uuid(), 'enabled',
                      to_jsonb(:old::text), to_jsonb(:new::text),
                      'admin', :now, :now, :now, 1
                    FROM account_user au WHERE au.id = :uid
                    """
                ),
                {
                    "old": "true" if action == "disable" else "false",
                    "new": "false" if action == "disable" else "true",
                    "uid": admin_user_id,
                    "now": datetime.now(UTC),
                },
            )
    except Exception:  # noqa: BLE001
        logger.debug("audit_log insert skipped (table may differ)", exc_info=True)


__all__ = [
    "ToolStatusRow",
    "_CACHE_TTL_S",
    "_reset_cache",
    "cache_invalidate",
    "disable_tool",
    "enable_tool",
    "get_disabled_tools",
    "list_tools_status",
]
