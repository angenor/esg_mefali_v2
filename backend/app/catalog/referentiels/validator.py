"""F09 US7 — Validateur de cohérence Référentiel pour publish.

Vérifications (FR-005) :
- a. somme des poids = 100 ± 0.01.
- b. toutes les sources liées sont ``verified`` (et au moins 1 source).
- c. tous les indicateurs liés sont ``published``.
- d. ``formula_expression`` non vide si ``formula_type='custom'`` (CHECK DB déjà
   appliqué — répété ici pour message clair).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

POIDS_TOTAL_TARGET = Decimal("100")
POIDS_TOTAL_TOL = Decimal("0.01")


def validate_for_publish(db: Session, referentiel_id: str) -> list[dict[str, Any]]:
    """Returns a list of failure dicts. Empty = ready to publish."""
    failures: list[dict[str, Any]] = []
    ref = db.execute(
        text("SELECT * FROM referentiel WHERE id = CAST(:id AS UUID)"),
        {"id": referentiel_id},
    ).first()
    if not ref:
        return [{"code": "not_found"}]
    ref = dict(ref._mapping)

    # a. weights sum.
    rows = db.execute(
        text(
            "SELECT poids FROM referentiel_indicateur "
            "WHERE referentiel_id = CAST(:id AS UUID)"
        ),
        {"id": referentiel_id},
    ).all()
    if not rows:
        failures.append(
            {"code": "no_indicateurs", "message": "Aucun indicateur attaché."}
        )
    else:
        total = sum((Decimal(str(r[0])) for r in rows), Decimal("0"))
        if abs(total - POIDS_TOTAL_TARGET) > POIDS_TOTAL_TOL:
            failures.append(
                {
                    "code": "weights_sum_invalid",
                    "expected": str(POIDS_TOTAL_TARGET),
                    "actual": str(total),
                }
            )

    # b. sources verified (≥1 source).
    sources_q = db.execute(
        text(
            "SELECT s.id, s.title, s.verification_status FROM source s "
            "JOIN referentiel_source rs ON rs.source_id = s.id "
            "WHERE rs.referentiel_id = CAST(:id AS UUID)"
        ),
        {"id": referentiel_id},
    ).all()
    if not sources_q:
        failures.append({"code": "no_sources", "message": "Aucune source liée."})
    else:
        unverified = [
            {"id": str(s[0]), "label": s[1] or "", "status": s[2]}
            for s in sources_q
            if s[2] != "verified"
        ]
        if unverified:
            failures.append({"code": "sources_not_verified", "missing_sources": unverified})

    # c. indicateurs published.
    unpublished = db.execute(
        text(
            "SELECT i.id, i.code, i.status FROM indicateur i "
            "JOIN referentiel_indicateur ri ON ri.indicateur_id = i.id "
            "WHERE ri.referentiel_id = CAST(:id AS UUID) AND i.status <> 'published'"
        ),
        {"id": referentiel_id},
    ).all()
    if unpublished:
        failures.append(
            {
                "code": "indicateurs_not_published",
                "items": [
                    {"id": str(u[0]), "code": u[1], "status": u[2]} for u in unpublished
                ],
            }
        )

    # d. custom formula non vide (déjà CHECK DB mais re-vérifié).
    if ref["formula_type"] == "custom" and not (ref.get("formula_expression") or "").strip():
        failures.append({"code": "custom_formula_required"})

    return failures
