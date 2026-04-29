"""F03 — Source service : workflow pending -> verified -> outdated/rejected.

Chaque transition passe par la DB où :
- Le trigger SQL ``source_double_validation_trg`` interdit
  ``verified_by == captured_by`` lors d'une transition vers ``verified``.
- Le trigger SQL ``source_status_version_trg`` incrémente ``status_version`` et
  insère une trace dans ``audit_log``.

Le service Python ajoute :
- Calcul d'embedding via Voyage AI lors de la transition vers ``verified``
  (FR-016 : échec propre si Voyage indisponible).
- Refus côté Python des transitions interdites (état machine §6 data-model).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import embeddings_client

logger = logging.getLogger(__name__)


class SourceServiceError(RuntimeError):
    """Erreur métier service Source (transitions invalides, embedding KO, …)."""


# Transitions licites issues du data-model §6
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"verified", "rejected"}),
    "verified": frozenset({"outdated", "pending"}),
    "outdated": frozenset({"verified"}),
    "rejected": frozenset(),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _embedding_text_for(row: dict[str, Any]) -> str:
    """Construit le texte servant de base à l'embedding."""
    parts = [
        row.get("title") or "",
        row.get("publisher") or "",
        row.get("notes") or "",
    ]
    return " ".join(p for p in parts if p)


def create_pending(
    db: Session,
    *,
    captured_by: uuid.UUID,
    url: str,
    title: str,
    publisher: str,
    version: str | None = None,
    date_publi: Any = None,
    page: str | None = None,
    section: str | None = None,
    notes: str | None = None,
) -> uuid.UUID:
    """Crée une nouvelle Source en statut ``pending``."""
    if not url.startswith(("http://", "https://")):
        raise SourceServiceError("url must start with http:// or https://")
    sid = uuid.uuid4()
    now = _now()
    db.execute(
        text(
            """
            INSERT INTO source
              (id, url, title, publisher, version, date_publi, page, section,
               notes, captured_at, captured_by, verification_status,
               status_version, created_at, updated_at)
            VALUES
              (:id, :url, :title, :pub, :ver, :dp, :page, :sec,
               :notes, :now, :cb, 'pending', 1, :now, :now)
            """
        ),
        {
            "id": str(sid),
            "url": url,
            "title": title,
            "pub": publisher,
            "ver": version,
            "dp": date_publi,
            "page": page,
            "sec": section,
            "notes": notes,
            "now": now,
            "cb": str(captured_by),
        },
    )
    return sid


def _load_status(db: Session, source_id: uuid.UUID) -> tuple[str, uuid.UUID, str | None]:
    """Renvoie (status, captured_by, embedding_present)."""
    row = db.execute(
        text(
            "SELECT verification_status, captured_by, "
            "(embedding IS NOT NULL) AS has_emb FROM source WHERE id = :id"
        ),
        {"id": str(source_id)},
    ).first()
    if row is None:
        raise SourceServiceError(f"source {source_id} not found")
    return str(row[0]), uuid.UUID(str(row[1])), bool(row[2])


def _check_transition(old: str, new: str) -> None:
    if new not in _ALLOWED_TRANSITIONS.get(old, frozenset()):
        raise SourceServiceError(f"transition not allowed: {old} -> {new}")


def verify(
    db: Session,
    *,
    source_id: uuid.UUID,
    verifier_id: uuid.UUID,
    embedding_func=embeddings_client.embed,
) -> None:
    """Transition pending|outdated -> verified.

    - Calcule l'embedding via Voyage (FR-016 — échec propre si indisponible).
    - La double validation (verifier_id != captured_by) est appliquée par le trigger SQL.
    """
    old, captured_by, _has_emb = _load_status(db, source_id)
    _check_transition(old, "verified")

    if verifier_id == captured_by:
        raise SourceServiceError(
            "double validation required: verifier must differ from captured_by"
        )

    row = db.execute(
        text("SELECT title, publisher, notes FROM source WHERE id = :id"),
        {"id": str(source_id)},
    ).mappings().first()
    text_for_emb = _embedding_text_for(dict(row))

    try:
        emb = embedding_func([text_for_emb])[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("embedding failure for source %s: %s", source_id, exc)
        raise SourceServiceError(f"embedding failure: {exc}") from exc

    db.execute(
        text(
            "UPDATE source SET verification_status = 'verified', "
            "verified_by = :vb, verified_at = :now, embedding = :emb, "
            "updated_at = :now WHERE id = :id"
        ),
        {
            "vb": str(verifier_id),
            "now": _now(),
            "emb": emb,
            "id": str(source_id),
        },
    )


def mark_outdated(db: Session, *, source_id: uuid.UUID) -> None:
    old, _cb, _ = _load_status(db, source_id)
    _check_transition(old, "outdated")
    db.execute(
        text(
            "UPDATE source SET verification_status = 'outdated', "
            "updated_at = :now WHERE id = :id"
        ),
        {"now": _now(), "id": str(source_id)},
    )


def reject(db: Session, *, source_id: uuid.UUID, reason: str | None = None) -> None:
    old, _cb, _ = _load_status(db, source_id)
    _check_transition(old, "rejected")
    db.execute(
        text(
            "UPDATE source SET verification_status = 'rejected', "
            "notes = COALESCE(:reason, notes), updated_at = :now WHERE id = :id"
        ),
        {"reason": f"REJECTED: {reason}" if reason else None, "now": _now(), "id": str(source_id)},
    )
