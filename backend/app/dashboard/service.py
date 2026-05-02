"""F32 — Service dashboard PME (lecture seule).

Construit l'agrégat ``DashboardSummaryOut`` et l'export complet ``DataExportOut``
pour un compte PME donné. Toutes les requêtes filtrent par ``account_id`` et
s'appuient sur le RLS Postgres (F02) comme garde-fou complémentaire.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dashboard.schemas import (
    ActionStepEntry,
    AttestationBlock,
    AttestationItem,
    CandidatureBlock,
    CandidatureItem,
    CarbonEntry,
    CreditScoreEntry,
    DashboardSummaryOut,
    DataExportOut,
    RapportBlock,
    RapportItem,
    ScoreEntry,
)

logger = logging.getLogger(__name__)

_TOP_N = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_serialize_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_value(x) for k, x in v.items()}
    return v


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    mapping = row._mapping if hasattr(row, "_mapping") else dict(row)
    return {k: _serialize_value(v) for k, v in mapping.items()}


# ---------------------------------------------------------------------------
# Summary blocks
# ---------------------------------------------------------------------------


def _latest_scores(db: Session, account_id: uuid.UUID) -> list[ScoreEntry]:
    sql = text(
        """
        SELECT DISTINCT ON (referentiel_code)
               referentiel_code, referentiel_version,
               score_global, coverage_ratio, computed_at
        FROM score_calculation
        WHERE account_id = :aid AND entity_type = 'entreprise'
        ORDER BY referentiel_code, computed_at DESC
        """
    )
    rows = db.execute(sql, {"aid": str(account_id)}).all()
    return [ScoreEntry(**dict(r._mapping)) for r in rows]


def _latest_carbon(db: Session, account_id: uuid.UUID) -> list[CarbonEntry]:
    sql = text(
        """
        SELECT DISTINCT ON (year)
               year, total_tco2e, computed_at
        FROM carbon_footprint
        WHERE account_id = :aid
        ORDER BY year DESC, computed_at DESC
        LIMIT 5
        """
    )
    rows = db.execute(sql, {"aid": str(account_id)}).all()
    return [CarbonEntry(**dict(r._mapping)) for r in rows]


def _latest_credit_score(
    db: Session, account_id: uuid.UUID
) -> CreditScoreEntry | None:
    sql = text(
        """
        SELECT solvabilite, impact_vert, combine,
               methodologie_version, coherence_warning, computed_at
        FROM credit_score
        WHERE account_id = :aid
        ORDER BY computed_at DESC
        LIMIT 1
        """
    )
    row = db.execute(sql, {"aid": str(account_id)}).first()
    if row is None:
        return None
    return CreditScoreEntry(**dict(row._mapping))


def _candidatures_block(db: Session, account_id: uuid.UUID) -> CandidatureBlock:
    counters_sql = text(
        """
        SELECT COALESCE(statut, 'inconnu') AS statut, COUNT(*) AS n
        FROM candidature
        WHERE account_id = :aid AND deleted_at IS NULL
        GROUP BY COALESCE(statut, 'inconnu')
        """
    )
    counters_rows = db.execute(counters_sql, {"aid": str(account_id)}).all()
    counters = {r._mapping["statut"]: int(r._mapping["n"]) for r in counters_rows}
    total = sum(counters.values())

    recent_sql = text(
        """
        SELECT id, projet_id, offre_id, statut, soumission_at, created_at
        FROM candidature
        WHERE account_id = :aid AND deleted_at IS NULL
        ORDER BY COALESCE(soumission_at, created_at) DESC NULLS LAST
        LIMIT :lim
        """
    )
    recent_rows = db.execute(
        recent_sql, {"aid": str(account_id), "lim": _TOP_N}
    ).all()
    recent = [CandidatureItem(**dict(r._mapping)) for r in recent_rows]

    return CandidatureBlock(counters_by_statut=counters, total=total, recent=recent)


def _rapports_block(db: Session, account_id: uuid.UUID) -> RapportBlock:
    total_sql = text(
        "SELECT COUNT(*) AS n FROM rapport_genere WHERE account_id = :aid"
    )
    total = int(db.execute(total_sql, {"aid": str(account_id)}).scalar() or 0)

    recent_sql = text(
        """
        SELECT id, entity_type, entity_id, referentiels, language, generated_at
        FROM rapport_genere
        WHERE account_id = :aid
        ORDER BY generated_at DESC
        LIMIT :lim
        """
    )
    rows = db.execute(recent_sql, {"aid": str(account_id), "lim": _TOP_N}).all()
    recent = [RapportItem(**dict(r._mapping)) for r in rows]
    return RapportBlock(total=total, recent=recent)


def _attestations_block(db: Session, account_id: uuid.UUID) -> AttestationBlock:
    counters_sql = text(
        """
        SELECT
          SUM(CASE WHEN revoked_at IS NULL THEN 1 ELSE 0 END) AS active,
          SUM(CASE WHEN revoked_at IS NOT NULL THEN 1 ELSE 0 END) AS revoked
        FROM attestation
        WHERE account_id = :aid
        """
    )
    row = db.execute(counters_sql, {"aid": str(account_id)}).first()
    active = int((row._mapping["active"] if row is not None else 0) or 0)
    revoked = int((row._mapping["revoked"] if row is not None else 0) or 0)

    recent_sql = text(
        """
        SELECT id, public_id, generated_at, valid_until, revoked_at
        FROM attestation
        WHERE account_id = :aid
        ORDER BY generated_at DESC
        LIMIT :lim
        """
    )
    rows = db.execute(recent_sql, {"aid": str(account_id), "lim": _TOP_N}).all()
    recent = [AttestationItem(**dict(r._mapping)) for r in rows]
    return AttestationBlock(active=active, revoked=revoked, recent=recent)


def _next_actions(db: Session, account_id: uuid.UUID) -> list[ActionStepEntry]:
    sql = text(
        """
        SELECT s.id, s.title, s.category, s.priority, s.status, s.horizon_at
        FROM action_step s
        JOIN action_plan p ON p.id = s.plan_id
        WHERE p.account_id = :aid
          AND s.status IN ('todo', 'doing')
        ORDER BY s.horizon_at ASC, s.priority ASC
        LIMIT :lim
        """
    )
    rows = db.execute(sql, {"aid": str(account_id), "lim": _TOP_N}).all()
    return [ActionStepEntry(**dict(r._mapping)) for r in rows]


def build_summary(db: Session, account_id: uuid.UUID) -> DashboardSummaryOut:
    """Construit l'agrégat dashboard pour ``account_id``."""
    return DashboardSummaryOut(
        account_id=account_id,
        scores=_latest_scores(db, account_id),
        carbon=_latest_carbon(db, account_id),
        credit_score=_latest_credit_score(db, account_id),
        candidatures=_candidatures_block(db, account_id),
        rapports=_rapports_block(db, account_id),
        attestations=_attestations_block(db, account_id),
        next_actions=_next_actions(db, account_id),
        generated_at=datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# Export complet
# ---------------------------------------------------------------------------


def _select_all_dicts(
    db: Session, sql: str, params: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = db.execute(text(sql), params).all()
    return [_row_to_dict(r) for r in rows]


def build_export(db: Session, account_id: uuid.UUID) -> DataExportOut:
    """Construit l'export JSON complet pour ``account_id`` (RLS strict)."""
    aid = {"aid": str(account_id)}

    account_row = db.execute(
        text("SELECT id, name FROM account WHERE id = :aid"), aid
    ).first()
    account = _row_to_dict(account_row) if account_row else {"id": str(account_id)}

    entreprise_row = db.execute(
        text(
            """
            SELECT id, account_id, name, secteur, taille_ca_amount,
                   taille_ca_currency, taille_effectifs, localisation,
                   gouvernance, version, created_at, updated_at
            FROM entreprise
            WHERE account_id = :aid AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        aid,
    ).first()
    entreprise = _row_to_dict(entreprise_row) if entreprise_row else None

    projets = _select_all_dicts(
        db,
        """
        SELECT id, account_id, entreprise_id, nom, description, type_impact,
               maturite, montant_recherche_amount, montant_recherche_currency,
               structure_financement, localisation, statut, version,
               created_at, updated_at
        FROM projet
        WHERE account_id = :aid AND deleted_at IS NULL
        ORDER BY created_at ASC
        """,
        aid,
    )

    candidatures = _select_all_dicts(
        db,
        """
        SELECT id, account_id, projet_id, offre_id, statut,
               soumission_at, version, created_at, updated_at
        FROM candidature
        WHERE account_id = :aid AND deleted_at IS NULL
        ORDER BY created_at ASC
        """,
        aid,
    )

    scores = _select_all_dicts(
        db,
        """
        SELECT id, account_id, entity_type, entity_id, referentiel_code,
               referentiel_version, score_global, scores_by_pillar,
               coverage_ratio, computed_at
        FROM score_calculation
        WHERE account_id = :aid
        ORDER BY computed_at ASC
        """,
        aid,
    )

    carbon = _select_all_dicts(
        db,
        """
        SELECT id, account_id, entreprise_id, year, total_tco2e,
               by_scope_json, computed_at, version
        FROM carbon_footprint
        WHERE account_id = :aid
        ORDER BY computed_at ASC
        """,
        aid,
    )

    credit_row = db.execute(
        text(
            """
            SELECT id, account_id, entreprise_id, solvabilite, impact_vert,
                   combine, methodologie_version, coherence_warning, computed_at
            FROM credit_score
            WHERE account_id = :aid
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        aid,
    ).first()
    credit_score = _row_to_dict(credit_row) if credit_row else None

    rapports = _select_all_dicts(
        db,
        """
        SELECT id, account_id, entity_type, entity_id, referentiels,
               language, file_path, file_size_bytes, generated_at
        FROM rapport_genere
        WHERE account_id = :aid
        ORDER BY generated_at ASC
        """,
        aid,
    )

    attestations = _select_all_dicts(
        db,
        """
        SELECT id, account_id, entreprise_id, public_id, generated_at,
               valid_until, revoked_at, revoked_reason, version
        FROM attestation
        WHERE account_id = :aid
        ORDER BY generated_at ASC
        """,
        aid,
    )

    consents = _select_all_dicts(
        db,
        """
        SELECT id, account_id, consent_kind, given, given_at, withdrawn_at,
               source_of_change, created_at, updated_at
        FROM consent
        WHERE account_id = :aid
        ORDER BY created_at ASC
        """,
        aid,
    )

    action_plan = _select_all_dicts(
        db,
        """
        SELECT p.id AS plan_id, p.horizon_months, p.version, p.generated_at,
               s.id AS step_id, s.title, s.description, s.category,
               s.priority, s.status, s.horizon_at
        FROM action_plan p
        LEFT JOIN action_step s ON s.plan_id = p.id
        WHERE p.account_id = :aid
        ORDER BY p.generated_at ASC, s.horizon_at ASC NULLS LAST
        """,
        aid,
    )

    return DataExportOut(
        account=account,
        entreprise=entreprise,
        projets=projets,
        candidatures=candidatures,
        scores=scores,
        carbon=carbon,
        credit_score=credit_score,
        rapports=rapports,
        attestations=attestations,
        consents=consents,
        action_plan=action_plan,
        exported_at=datetime.now(tz=UTC),
    )
