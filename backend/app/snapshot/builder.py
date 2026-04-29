"""F04 — ``build_candidature_snapshot`` (US6).

Assembles a v1 snapshot dict from a draft Candidature + active référentiel.
Validates against the Pydantic v2 mirror of contracts/snapshot.schema.json
before returning, so callers get a strongly-typed dict.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.snapshot.schema import (
    CandidatureSnapshotV1,
    CritereRef,
    Money,
    OffreRef,
    ReferentielRef,
    SnapshotScores,
    SourceRef,
)
from app.versioning.helpers import get_active


class SnapshotBuilderError(RuntimeError):
    """Raised when the snapshot cannot be assembled (FR-015)."""


def _money(amount: Decimal | float | str | None, currency: str | None) -> Money:
    """Coerce a Money pair into the strict snapshot model (default XOF)."""
    if amount is None:
        amount_s = "0"
    elif isinstance(amount, Decimal):
        amount_s = str(amount)
    else:
        amount_s = str(Decimal(str(amount)))
    return Money(amount=amount_s, currency=currency or "XOF")


def build_candidature_snapshot(
    db: Session,
    *,
    candidature_id: UUID | str,
    score_provider: Any | None = None,
) -> dict[str, Any]:
    """Build and validate a v1 snapshot for ``candidature_id``.

    Args:
        db: SQLAlchemy session (RLS-scoped).
        candidature_id: target candidature (must be a draft, not yet submitted).
        score_provider: callable ``(candidature_row, referentiel_row) -> dict``
            returning ``{'global': Money, 'per_critere': {<critere_id>: Money}}``.
            Defaults to a zero-score stub when None (F23 not yet implemented).

    Returns:
        A dict matching ``contracts/snapshot.schema.json`` v1.

    Raises:
        SnapshotBuilderError: when the candidature, its offre, or an active
            referentiel cannot be resolved (FR-015).
    """
    cand = db.execute(
        text(
            "SELECT id, account_id, projet_id, offre_id, snapshot_json, submitted_at "
            "FROM candidature WHERE id = CAST(:cid AS UUID)"
        ),
        {"cid": str(candidature_id)},
    ).mappings().first()
    if cand is None:
        raise SnapshotBuilderError(f"candidature {candidature_id} not found")

    projet = db.execute(
        text(
            "SELECT id, nom, description, type_impact, maturite, "
            "       montant_recherche_amount, montant_recherche_currency, "
            "       indicateurs_impact_json "
            "FROM projet WHERE id = :pid"
        ),
        {"pid": cand["projet_id"]},
    ).mappings().first()
    if projet is None:
        raise SnapshotBuilderError(f"projet {cand['projet_id']} not found")

    offre = db.execute(
        text("SELECT id FROM offre WHERE id = :oid"),
        {"oid": cand["offre_id"]},
    ).mappings().first()
    if offre is None:
        raise SnapshotBuilderError(f"offre {cand['offre_id']} not found")

    # Critère pins for the offre.
    crits = db.execute(
        text(
            "SELECT id, logical_id, version "
            "FROM critere WHERE offre_id = :oid"
        ),
        {"oid": offre["id"]},
    ).mappings().all()

    # Active référentiel — pick the most recently active one referenced by
    # the offre's critères. If none, raise (FR-015).
    ref_logical_id = db.execute(
        text(
            "SELECT DISTINCT r.logical_id, r.version_num, r.valid_from "
            "FROM referentiel r "
            "JOIN critere c ON c.referentiel_id = r.id "
            "WHERE c.offre_id = :oid "
            "  AND r.valid_to IS NULL "
            "ORDER BY r.valid_from DESC LIMIT 1"
        ),
        {"oid": offre["id"]},
    ).mappings().first()

    if ref_logical_id is None:
        # Fallback: take any active referentiel (single-tenant MVP).
        ref_logical_id = db.execute(
            text(
                "SELECT logical_id, version_num, valid_from "
                "FROM referentiel WHERE valid_to IS NULL "
                "ORDER BY valid_from DESC LIMIT 1"
            )
        ).mappings().first()

    if ref_logical_id is None:
        raise SnapshotBuilderError("no active référentiel found at submission time")

    # Active row to confirm pinning.
    ref_active = get_active(
        db, table="referentiel", logical_id=ref_logical_id["logical_id"]
    )
    if ref_active is None:
        raise SnapshotBuilderError("active référentiel disappeared between queries")

    # Sources cited via critères (best-effort).
    sources: list[SourceRef] = []
    src_rows = db.execute(
        text(
            "SELECT s.id, s.verification_status "
            "FROM source s "
            "JOIN critere c ON c.source_id = s.id "
            "WHERE c.offre_id = :oid"
        ),
        {"oid": offre["id"]},
    ).mappings().all()
    for r in src_rows:
        sources.append(
            SourceRef(source_id=r["id"], verified=str(r["verification_status"]) == "verified")
        )

    # Scores — F23 not yet implemented; default to zero unless provider supplied.
    if score_provider is not None:
        scores_dict = score_provider(cand, ref_active)
        global_money = scores_dict["global"]
        per_critere = scores_dict.get("per_critere", {})
    else:
        global_money = _money("0", "XOF")
        per_critere = {}

    snapshot = CandidatureSnapshotV1(
        schema_version="1",
        referentiel=ReferentielRef(
            logical_id=ref_active["logical_id"],
            version=int(ref_active["version_num"]),
            valid_from=ref_active["valid_from"],
        ),
        offre=OffreRef(
            id=offre["id"],
            criteres=[
                CritereRef(logical_id=c["logical_id"], version=int(c["version"]))
                for c in crits
            ],
        ),
        projet_state={
            "nom": projet["nom"],
            "description": projet["description"],
            "type_impact": projet["type_impact"],
            "maturite": projet["maturite"],
            "montant_recherche_amount": (
                str(projet["montant_recherche_amount"])
                if projet["montant_recherche_amount"] is not None
                else None
            ),
            "montant_recherche_currency": projet["montant_recherche_currency"],
            "indicateurs_impact_json": projet["indicateurs_impact_json"],
        },
        scores=SnapshotScores(**{"global": global_money, "per_critere": per_critere}),
        sources=sources,
    )

    return snapshot.model_dump(mode="json", by_alias=True)
