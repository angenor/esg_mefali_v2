"""F04 — Versioning helpers : ``publish_new_version`` + ``get_active``.

These helpers operate at the SQL level (no ORM dependency) so they can be
applied to any of the seven versioned catalogue tables uniformly.

Postgres invariants enforced by 0004 migration:
- Each row has logical_id (UUID), valid_from (TIMESTAMPTZ NOT NULL),
  valid_to (TIMESTAMPTZ NULL), parent_id (UUID NULL self-FK), version (INT).
- EXCLUDE USING gist guarantees no two rows of the same logical_id overlap
  in [valid_from, valid_to).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.versioning.exceptions import OptimisticLockError


def get_active(
    db: Session,
    *,
    table: str,
    logical_id: UUID | str,
    at_timestamp: datetime | None = None,
) -> dict[str, Any] | None:
    """Return the row of ``table`` active for ``logical_id`` at the given moment.

    ``at_timestamp`` defaults to ``now()``. Result is ``None`` when no version
    is in effect.
    """
    ts = at_timestamp or datetime.now(tz=UTC)
    sql = text(
        f"""
        SELECT * FROM {table}
        WHERE logical_id = CAST(:lid AS UUID)
          AND valid_from <= :ts
          AND (valid_to IS NULL OR valid_to > :ts)
        ORDER BY valid_from DESC
        LIMIT 1
        """  # noqa: S608 — table name from internal whitelist
    )
    row = db.execute(sql, {"lid": str(logical_id), "ts": ts}).mappings().first()
    return dict(row) if row else None


def publish_new_version(
    db: Session,
    *,
    table: str,
    logical_id: UUID | str,
    new_payload: dict[str, Any],
    version_at_load: int,
) -> dict[str, Any]:
    """Atomically close the active version and open a new one.

    - Locks the active row via SELECT ... FOR UPDATE.
    - Raises :class:`OptimisticLockError` if the active row's version differs
      from ``version_at_load`` (HTTP 412 path).
    - Sets ``valid_to = now()`` on the active row, inserts a new row with
      ``version = current.version + 1``, ``parent_id = current.id``,
      ``valid_from = now()``, ``valid_to = NULL``.

    The caller is responsible for the surrounding transaction commit.
    """
    now = datetime.now(tz=UTC)
    version_col = "version_num" if table == "referentiel" else "version"

    sel = text(
        f"""
        SELECT id, {version_col} AS v
        FROM {table}
        WHERE logical_id = CAST(:lid AS UUID) AND valid_to IS NULL
        FOR UPDATE
        """  # noqa: S608
    )
    active = db.execute(sel, {"lid": str(logical_id)}).mappings().first()

    if active is None:
        # No active row -> first publication for this logical_id.
        if version_at_load not in (0, None):
            raise OptimisticLockError(current_version=0, expected=version_at_load)
        new_version = 1
        parent_id = None
    else:
        if int(active["v"]) != int(version_at_load):
            raise OptimisticLockError(
                current_version=int(active["v"]),
                expected=int(version_at_load),
            )
        new_version = int(active["v"]) + 1
        parent_id = active["id"]
        # Close the active row.
        db.execute(
            text(f"UPDATE {table} SET valid_to = :ts WHERE id = :id"),  # noqa: S608
            {"ts": now, "id": active["id"]},
        )

    # Build the INSERT dynamically from new_payload columns.
    columns = list(new_payload.keys())
    fixed_cols = [
        "id",
        "logical_id",
        "parent_id",
        "valid_from",
        "valid_to",
        version_col,
    ]
    payload_cols = [c for c in columns if c not in fixed_cols]
    new_id = uuid4()
    insert_cols = fixed_cols + payload_cols
    placeholders = ", ".join(f":{c}" for c in insert_cols)
    col_list = ", ".join(insert_cols)

    params: dict[str, Any] = {
        "id": str(new_id),
        "logical_id": str(logical_id),
        "parent_id": str(parent_id) if parent_id else None,
        "valid_from": now,
        "valid_to": None,
        version_col: new_version,
    }
    for c in payload_cols:
        params[c] = new_payload[c]

    db.execute(
        text(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"  # noqa: S608
        ),
        params,
    )

    inserted = db.execute(
        text(f"SELECT * FROM {table} WHERE id = :id"),  # noqa: S608
        {"id": str(new_id)},
    ).mappings().first()
    return dict(inserted)
