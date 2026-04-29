"""F09 US5 — Helper ``get_facteur(code, pays_iso2=None, at=None)``.

Algorithme (FR-007) :
1. Cherche le facteur ``published`` au ``code`` donné, ``pays_iso2`` exact, dont
   ``valid_from_date <= at`` et ``(valid_to_date IS NULL OR valid_to_date >= at)``.
2. Sinon fallback sur ``pays_iso2 IS NULL`` (mondial).
3. Sinon : aucun résultat (None).

Index utilisé : ``idx_facteur_emission_lookup (code, pays_iso2, valid_from_date DESC)``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_facteur(
    db: Session,
    code: str,
    pays_iso2: str | None = None,
    at: date | None = None,
) -> dict[str, Any] | None:
    at = at or date.today()
    code = code.strip()
    pays_clause = ""
    params: dict[str, Any] = {"code": code, "at": at}
    if pays_iso2:
        pays_clause = "AND pays_iso2 = :pays"
        params["pays"] = pays_iso2.upper()
        sql = text(
            f"""
            SELECT * FROM facteur_emission
            WHERE code = :code AND status = 'published'
              {pays_clause}
              AND valid_from_date <= :at
              AND (valid_to_date IS NULL OR valid_to_date >= :at)
            ORDER BY valid_from_date DESC LIMIT 1
            """
        )
        row = db.execute(sql, params).first()
        if row:
            return dict(row._mapping)

    # Fallback : mondial (pays_iso2 IS NULL).
    sql = text(
        """
        SELECT * FROM facteur_emission
        WHERE code = :code AND status = 'published'
          AND pays_iso2 IS NULL
          AND valid_from_date <= :at
          AND (valid_to_date IS NULL OR valid_to_date >= :at)
        ORDER BY valid_from_date DESC LIMIT 1
        """
    )
    row = db.execute(sql, {"code": code, "at": at}).first()
    return dict(row._mapping) if row else None
