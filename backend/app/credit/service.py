"""F29 - CreditScoringService.

Orchestration :
- collecte (``submit_credit_data``, ``submit_mobile_money_csv``),
- calcul (``recompute_score`` avec advisory lock + audit append-only),
- lecture (``get_latest_score``, ``get_methodology``).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import SourceOfChange, record_audit
from app.credit.csv_parser import parse_statement
from app.credit.engine import (
    DEFAULT_METHODOLOGY,
    ScoringInputs,
    compute_full_score,
)
from app.credit.schemas import CreditDataKind


class CreditScoreNotFound(Exception):
    """Aucun score n'a encore ete calcule pour cette entreprise."""


class MethodologyNotFound(Exception):
    """Methodologie introuvable (version inexistante)."""


class EntrepriseRequired(Exception):
    """Le calcul exige un entreprise_id valide."""


# --------------------------------------------------------------------------- #
# Lookups defensifs (None-safe sur tables potentiellement absentes)            #
# --------------------------------------------------------------------------- #


def _table_exists(db: Session, table: str) -> bool:
    row = db.execute(
        text("SELECT to_regclass(:t) AS r"), {"t": table}
    ).fetchone()
    return bool(row and row.r is not None)


def _latest_esg(db: Session, entreprise_id: UUID) -> float | None:
    if not _table_exists(db, "score_calculation"):
        return None
    row = db.execute(
        text(
            """
            SELECT score_global FROM score_calculation
            WHERE entity_type='entreprise' AND entity_id=:e
              AND score_global IS NOT NULL
            ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"e": str(entreprise_id)},
    ).fetchone()
    return float(row.score_global) if row and row.score_global is not None else None


def _latest_carbone(db: Session, entreprise_id: UUID) -> float | None:
    if not _table_exists(db, "carbon_footprint"):
        return None
    row = db.execute(
        text(
            """
            SELECT total_tco2e FROM carbon_footprint
            WHERE entreprise_id=:e
            ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"e": str(entreprise_id)},
    ).fetchone()
    return float(row.total_tco2e) if row and row.total_tco2e is not None else None


def _entreprise_basics(
    db: Session, entreprise_id: UUID
) -> dict[str, Any]:
    """Retourne {anciennete_years, employes} (None si donnees absentes)."""
    out: dict[str, Any] = {"anciennete_years": None, "employes": None}
    if not _table_exists(db, "entreprise"):
        return out
    try:
        row = db.execute(
            text("SELECT created_at FROM entreprise WHERE id=:e"),
            {"e": str(entreprise_id)},
        ).fetchone()
    except Exception:  # noqa: BLE001
        return out
    if row is None:
        return out
    if getattr(row, "created_at", None):
        ref = row.created_at
        ref_aware = ref if ref.tzinfo else ref.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - ref_aware
        out["anciennete_years"] = max(0.0, delta.days / 365.25)
    return out


def _projets_verts_count(db: Session, entreprise_id: UUID) -> int | None:
    if not _table_exists(db, "projet"):
        return None
    try:
        row = db.execute(
            text(
                """
                SELECT COUNT(*) AS n FROM projet
                WHERE entreprise_id=:e
                  AND COALESCE(LOWER(type::text), '') LIKE '%vert%'
                """
            ),
            {"e": str(entreprise_id)},
        ).fetchone()
    except Exception:  # noqa: BLE001
        return None
    return int(row.n) if row else 0


def _latest_credit_data(
    db: Session, entreprise_id: UUID, kind: str
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT payload_json FROM credit_data
            WHERE entreprise_id=:e AND kind=:k
            ORDER BY uploaded_at DESC LIMIT 1
            """
        ),
        {"e": str(entreprise_id), "k": kind},
    ).fetchone()
    if row is None:
        return None
    payload = row.payload_json
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except ValueError:
            return None
    return payload


# --------------------------------------------------------------------------- #
# Methodologie (Referentiel F09 si seedee, fallback DEFAULT_METHODOLOGY)        #
# --------------------------------------------------------------------------- #


def get_methodology(
    db: Session, version: int | None = None
) -> dict[str, Any]:
    """Retourne la methodologie active (ou la version demandee)."""
    if not _table_exists(db, "referentiel"):
        return DEFAULT_METHODOLOGY
    try:
        if version is None:
            row = db.execute(
                text(
                    """
                    SELECT id, version, status, content_json, description
                    FROM referentiel
                    WHERE kind='credit_scoring_methodology' AND status='published'
                    ORDER BY version DESC LIMIT 1
                    """
                )
            ).fetchone()
        else:
            row = db.execute(
                text(
                    """
                    SELECT id, version, status, content_json, description
                    FROM referentiel
                    WHERE kind='credit_scoring_methodology' AND version=:v
                    LIMIT 1
                    """
                ),
                {"v": version},
            ).fetchone()
    except Exception:  # noqa: BLE001
        if version is not None:
            raise MethodologyNotFound(f"version {version} introuvable") from None
        return DEFAULT_METHODOLOGY
    if row is None:
        if version is not None:
            raise MethodologyNotFound(f"version {version} introuvable")
        return DEFAULT_METHODOLOGY
    content = row.content_json
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            content = None
    if not isinstance(content, dict) or "factors" not in content:
        return DEFAULT_METHODOLOGY
    out = dict(content)
    out["version"] = int(row.version)
    out["referentiel_id"] = str(row.id)
    out["status"] = row.status
    if row.description:
        out["description"] = row.description
    return out


# --------------------------------------------------------------------------- #
# Collecte                                                                     #
# --------------------------------------------------------------------------- #


def submit_credit_data(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID,
    user_id: UUID | None,
    kind: CreditDataKind,
    payload: dict[str, Any],
    valid_until: datetime | None = None,
    consent_id: UUID | None = None,
) -> dict[str, Any]:
    """Persist une ligne credit_data + audit."""
    new_id = uuid.uuid4()
    db.execute(
        text(
            """
            INSERT INTO credit_data
              (id, account_id, entreprise_id, kind, payload_json,
               consent_id, uploaded_at, valid_until)
            VALUES
              (:id, :acc, :ent, :k, CAST(:payload AS JSONB),
               :cid, now(), :until)
            """
        ),
        {
            "id": str(new_id),
            "acc": str(account_id),
            "ent": str(entreprise_id),
            "k": kind.value if isinstance(kind, CreditDataKind) else str(kind),
            "payload": json.dumps(payload, default=str),
            "cid": str(consent_id) if consent_id else None,
            "until": valid_until,
        },
    )
    record_audit(
        db,
        entity_type="credit_data",
        entity_id=new_id,
        field="kind",
        old=None,
        new=kind.value if isinstance(kind, CreditDataKind) else str(kind),
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    db.commit()
    return {
        "id": new_id,
        "kind": kind,
        "payload_json": payload,
        "uploaded_at": datetime.now(UTC),
        "valid_until": valid_until,
    }


def submit_mobile_money_csv(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID,
    user_id: UUID | None,
    raw_bytes: bytes,
    consent_id: UUID | None = None,
) -> dict[str, Any]:
    """Parse un CSV Mobile Money + persist une ligne credit_data(mobile_money)."""
    parsed = parse_statement(raw_bytes)
    return submit_credit_data(
        db,
        account_id=account_id,
        entreprise_id=entreprise_id,
        user_id=user_id,
        kind=CreditDataKind.MOBILE_MONEY,
        payload=parsed,
        consent_id=consent_id,
    )


# --------------------------------------------------------------------------- #
# Calcul                                                                       #
# --------------------------------------------------------------------------- #


def _build_inputs(db: Session, entreprise_id: UUID) -> ScoringInputs:
    declaratif = _latest_credit_data(db, entreprise_id, "declaratif") or {}
    mm = _latest_credit_data(db, entreprise_id, "mobile_money") or {}
    indicators = mm.get("indicators") if isinstance(mm, dict) else None
    indicators = indicators if isinstance(indicators, dict) else {}

    basics = _entreprise_basics(db, entreprise_id)
    paiements = declaratif.get("paiements_reguliers")
    diversification = declaratif.get("diversification_clients")
    employes_decl = declaratif.get("nb_employes")
    employes = (
        basics.get("employes")
        if basics.get("employes") is not None
        else (float(employes_decl) if isinstance(employes_decl, (int, float)) else None)
    )

    return ScoringInputs(
        mm_monthly_mean_xof=indicators.get("monthly_mean_xof"),
        mm_monthly_stdev_xof=indicators.get("monthly_stdev_xof"),
        entreprise_anciennete_years=basics.get("anciennete_years"),
        entreprise_employes=employes,
        paiements_reguliers=(
            bool(paiements) if isinstance(paiements, bool) else None
        ),
        diversification_clients=(
            int(diversification) if isinstance(diversification, int) else None
        ),
        esg_score_global=_latest_esg(db, entreprise_id),
        carbone_total_tco2e=_latest_carbone(db, entreprise_id),
        nb_projets_verts=_projets_verts_count(db, entreprise_id),
        nb_odd_alignes=(
            int(declaratif.get("nb_odd_alignes"))
            if isinstance(declaratif.get("nb_odd_alignes"), int)
            else None
        ),
    )


def _source_map_from_methodology(methodology: dict[str, Any]) -> dict[str, str]:
    source_map: dict[str, str] = {}
    for spec in methodology.get("factors", []):
        if "source_id" in spec and spec["source_id"]:
            source_map[spec["name"]] = str(spec["source_id"])
    return source_map


def recompute_score(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID | None,
    user_id: UUID | None,
) -> dict[str, Any]:
    if entreprise_id is None:
        raise EntrepriseRequired("entreprise_id requis pour recalculer le score")

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"credit_score:{entreprise_id}"},
    )

    methodology = get_methodology(db)
    source_map = _source_map_from_methodology(methodology)
    inputs = _build_inputs(db, entreprise_id)
    result = compute_full_score(
        inputs, methodology=methodology, source_map=source_map
    )

    new_id = uuid.uuid4()
    db.execute(
        text(
            """
            INSERT INTO credit_score
              (id, account_id, entreprise_id, solvabilite, impact_vert,
               combine, facteurs, methodologie_version, coherence_warning,
               computed_at)
            VALUES
              (:id, :acc, :ent, :s, :i, :c, CAST(:f AS JSONB), :v, :w, now())
            """
        ),
        {
            "id": str(new_id),
            "acc": str(account_id),
            "ent": str(entreprise_id),
            "s": result["solvabilite"],
            "i": result["impact_vert"],
            "c": result["combine"],
            "f": json.dumps(result["facteurs"], default=str),
            "v": result["methodologie_version"],
            "w": result["coherence_warning"],
        },
    )
    record_audit(
        db,
        entity_type="credit_score",
        entity_id=new_id,
        field="combine",
        old=None,
        new=result["combine"],
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )
    db.commit()
    return {
        "id": new_id,
        "entreprise_id": entreprise_id,
        "solvabilite": result["solvabilite"],
        "impact_vert": result["impact_vert"],
        "combine": result["combine"],
        "facteurs": result["facteurs"],
        "methodologie_version": result["methodologie_version"],
        "coherence_warning": result["coherence_warning"],
        "computed_at": datetime.now(UTC),
    }


def get_latest_score(
    db: Session, *, account_id: UUID, entreprise_id: UUID | None
) -> dict[str, Any]:
    if entreprise_id is None:
        raise CreditScoreNotFound("entreprise_id requis")
    row = db.execute(
        text(
            """
            SELECT id, entreprise_id, solvabilite, impact_vert, combine,
                   facteurs, methodologie_version, coherence_warning,
                   computed_at
            FROM credit_score
            WHERE entreprise_id=:e AND account_id=:a
            ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"e": str(entreprise_id), "a": str(account_id)},
    ).fetchone()
    if row is None:
        raise CreditScoreNotFound(
            f"aucun score pour entreprise {entreprise_id}"
        )
    facteurs = row.facteurs
    if isinstance(facteurs, str):
        try:
            facteurs = json.loads(facteurs)
        except ValueError:
            facteurs = []
    return {
        "id": row.id,
        "entreprise_id": row.entreprise_id,
        "solvabilite": int(row.solvabilite),
        "impact_vert": int(row.impact_vert),
        "combine": int(row.combine),
        "facteurs": facteurs,
        "methodologie_version": int(row.methodologie_version),
        "coherence_warning": bool(row.coherence_warning),
        "computed_at": row.computed_at,
    }
