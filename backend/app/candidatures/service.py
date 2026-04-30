"""F34 — Service applicatif ``/me/candidatures``."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.candidatures.schemas import VALID_CANDIDATURE_STATUTS

logger = logging.getLogger(__name__)


class CandidatureNotFoundError(LookupError):
    """Candidature introuvable ou n'appartenant pas à la PME."""


class InvalidCandidatureStatutError(ValueError):
    """Statut hors liste blanche."""


_LIST_LIMIT_HARD = 200


def _progression_from_snapshot(snapshot_json: dict | None) -> int:
    if not isinstance(snapshot_json, dict):
        return 0
    val = snapshot_json.get("progression_pct")
    if isinstance(val, bool):
        return 0
    if not isinstance(val, int):
        return 0
    if val < 0:
        return 0
    if val > 100:
        return 100
    return val


def list_for_account(
    db: Session,
    *,
    account_id: uuid.UUID,
    limit: int = _LIST_LIMIT_HARD,
) -> list[dict]:
    """Liste des candidatures non supprimées de la PME, triées updated_at DESC."""
    capped = max(1, min(_LIST_LIMIT_HARD, int(limit)))
    rows = (
        db.execute(
            text(
                """
                SELECT id, projet_id, offre_id, statut, snapshot_json,
                       created_at, updated_at
                FROM candidature
                WHERE account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT :lim
                """
            ),
            {"aid": str(account_id), "lim": capped},
        )
        .mappings()
        .all()
    )
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "projet_id": r["projet_id"],
                "offre_id": r["offre_id"],
                "statut": r["statut"],
                "progression_pct": _progression_from_snapshot(r["snapshot_json"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return out


def update_status(
    db: Session,
    *,
    candidature_id: uuid.UUID,
    account_id: uuid.UUID,
    user_id: uuid.UUID | None,
    new_statut: str,
) -> dict:
    """Met à jour ``statut`` ; audit ; retourne dict {id, statut, version, updated_at}."""
    if new_statut not in VALID_CANDIDATURE_STATUTS:
        raise InvalidCandidatureStatutError(new_statut)

    row = (
        db.execute(
            text(
                """
                SELECT id, statut, version
                FROM candidature
                WHERE id = CAST(:cid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                """
            ),
            {"cid": str(candidature_id), "aid": str(account_id)},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise CandidatureNotFoundError(str(candidature_id))

    old_statut = row["statut"]
    if old_statut == new_statut:
        cur = (
            db.execute(
                text(
                    "SELECT updated_at, version FROM candidature "
                    "WHERE id = CAST(:cid AS UUID)"
                ),
                {"cid": str(candidature_id)},
            )
            .mappings()
            .first()
        )
        return {
            "id": candidature_id,
            "statut": new_statut,
            "version": cur["version"] if cur else row["version"],
            "updated_at": cur["updated_at"] if cur else datetime.now(tz=UTC),
        }

    now = datetime.now(tz=UTC).replace(tzinfo=None)
    db.execute(
        text(
            """
            UPDATE candidature
            SET statut = :s,
                version = version + 1,
                updated_at = :ts
            WHERE id = CAST(:cid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {
            "s": new_statut,
            "ts": now,
            "cid": str(candidature_id),
            "aid": str(account_id),
        },
    )
    try:
        record_audit(
            db,
            entity_type="candidature",
            entity_id=candidature_id,
            field="statut",
            old=old_statut,
            new=new_statut,
            source_of_change=SourceOfChange.MANUAL,
            user_id=str(user_id) if user_id else None,
            account_id=str(account_id),
        )
    except Exception as exc:  # noqa: BLE001 — audit best-effort
        logger.warning("candidature: audit failed: %s", exc)

    refreshed = (
        db.execute(
            text(
                "SELECT id, statut, version, updated_at "
                "FROM candidature WHERE id = CAST(:cid AS UUID)"
            ),
            {"cid": str(candidature_id)},
        )
        .mappings()
        .first()
    )
    assert refreshed is not None
    return dict(refreshed)
