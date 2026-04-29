"""F03 US2 — Tool ``cite_source`` (function-calling LLM).

Use when : tu vas affirmer un chiffre, seuil, critère, formule, facteur d'émission,
document requis ou citer un référentiel ; tu dois prouver la source.

Don't use when : tu écris un texte générique sans donnée chiffrée ESG/financière
ni référence normative.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.source import (
    CiteSourceInput,
    CiteSourceOutput,
    SourceRead,
)


def handle_cite_source(db: Session, payload: CiteSourceInput) -> CiteSourceOutput:
    """Renvoie la Source si verified, sinon ``error='not_verified'`` ou ``'not_found'``."""
    sid: uuid.UUID = payload.source_id
    row = db.execute(
        text(
            "SELECT id, url, title, publisher, version, date_publi, page, section, "
            "captured_at, verified_at, verification_status, notes "
            "FROM source WHERE id = :id"
        ),
        {"id": str(sid)},
    ).mappings().first()
    if row is None:
        return CiteSourceOutput(error="not_found")
    if row["verification_status"] != "verified":
        return CiteSourceOutput(error="not_verified")
    return CiteSourceOutput(source=SourceRead.model_validate(dict(row)))
