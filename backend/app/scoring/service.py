"""F23 — Service d'orchestration du scoring (load → compute → persist → audit).

Charge le référentiel publié + ses indicateurs liés, résout les valeurs PME via
:mod:`app.scoring.value_source`, applique :func:`app.scoring.engine.compute_score`,
persiste le résultat en table ``score_calculation`` et journalise via
``record_audit`` (F04).
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.entreprise.service import get_or_provision_entreprise
from app.scoring.engine import (
    IndicatorRule,
    MissingIndicator,
    ScoreResult,
    compute_score,
)
from app.scoring.value_source import collect_values

logger = logging.getLogger(__name__)


class ReferentielNotFound(Exception):
    """Référentiel inconnu ou non publié."""


class EntityNotAccessible(Exception):
    """Entité non accessible (RLS / cross-tenant)."""


def _load_published_referentiel(db: Session, code: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, code, version, status
            FROM referentiel
            WHERE code = :code
              AND status = 'published'
              AND (valid_to IS NULL OR valid_to > now())
            ORDER BY version DESC
            LIMIT 1
            """
        ),
        {"code": code},
    ).first()
    if row is None:
        return None
    return {"id": row.id, "code": row.code, "version": int(row.version)}


def _load_indicator_rules(
    db: Session, *, referentiel_id: uuid.UUID
) -> list[IndicatorRule]:
    rows = db.execute(
        text(
            """
            SELECT
              i.id          AS indicateur_id,
              i.code        AS indicateur_code,
              i.pillar      AS pillar,
              i.value_type  AS value_type,
              i.enum_values AS enum_values,
              ri.poids      AS poids,
              ri.seuil_min  AS seuil_min,
              ri.seuil_max  AS seuil_max,
              ri.source_id  AS source_id
            FROM referentiel_indicateur ri
            JOIN indicateur i ON i.id = ri.indicateur_id
            WHERE ri.referentiel_id = :rid
              AND i.status = 'published'
            ORDER BY i.code
            """
        ),
        {"rid": str(referentiel_id)},
    ).fetchall()

    rules: list[IndicatorRule] = []
    for r in rows:
        rules.append(
            IndicatorRule(
                indicateur_id=r.indicateur_id,
                indicateur_code=r.indicateur_code,
                pillar=(r.pillar or "").strip(),
                value_type=r.value_type or "numeric",
                weight=float(r.poids or 0),
                source_id=r.source_id,
                seuil_min=r.seuil_min,
                seuil_max=r.seuil_max,
                enum_values=r.enum_values,
            )
        )
    return rules


def _load_entity_values(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    rules: list[IndicatorRule],
) -> tuple[dict[str, Any], dict[str, str]]:
    """MVP : ne sait lire que `entreprise`. Pour `projet` → tous unmapped."""
    if entity_type == "entreprise":
        ent = get_or_provision_entreprise(db, account_id=account_id)
        if ent.id != entity_id:
            raise EntityNotAccessible("entreprise hors tenant")
        codes = [r.indicateur_code for r in rules]
        return collect_values(indicateur_codes=codes, entreprise=ent)

    # projet (MVP) : pas de mapping → unmapped systématique.
    return ({}, {r.indicateur_code: "value_source_unmapped" for r in rules})


def _retag_unmapped(result: ScoreResult, unmapped: dict[str, str]) -> ScoreResult:
    """Met à jour la `reason` des indicateurs manquants présents dans `unmapped`."""
    if not unmapped:
        return result
    new_missing: list[MissingIndicator] = []
    for m in result.indicateurs_manquants:
        if m.indicateur_code in unmapped:
            new_missing.append(
                MissingIndicator(
                    indicateur_id=m.indicateur_id,
                    indicateur_code=m.indicateur_code,
                    pillar=m.pillar,
                    reason=unmapped[m.indicateur_code],
                )
            )
        else:
            new_missing.append(m)
    return ScoreResult(
        score_global=result.score_global,
        scores_by_pillar=result.scores_by_pillar,
        coverage_ratio=result.coverage_ratio,
        indicateurs_couverts=result.indicateurs_couverts,
        indicateurs_manquants=new_missing,
        sources_used=result.sources_used,
    )


def _serialize_details(result: ScoreResult) -> dict[str, Any]:
    return {
        "indicateurs_couverts": [
            {
                k: (str(v) if isinstance(v, uuid.UUID) else v)
                for k, v in asdict(c).items()
            }
            for c in result.indicateurs_couverts
        ],
        "indicateurs_manquants": [
            {
                k: (str(v) if isinstance(v, uuid.UUID) else v)
                for k, v in asdict(m).items()
            }
            for m in result.indicateurs_manquants
        ],
        "sources_used": [str(s) for s in result.sources_used],
    }


def _json_dumps(obj: Any) -> str:
    def _default(o: Any) -> Any:
        if isinstance(o, uuid.UUID):
            return str(o)
        try:
            return float(o)
        except Exception:
            return str(o)

    return json.dumps(obj, default=_default)


def compute_and_persist(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Calcule, persiste, audite, retourne le détail complet."""
    ref = _load_published_referentiel(db, referentiel_code)
    if ref is None:
        raise ReferentielNotFound(referentiel_code)

    rules = _load_indicator_rules(db, referentiel_id=ref["id"])

    values, unmapped = _load_entity_values(
        db,
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        rules=rules,
    )

    result = compute_score(rules=rules, values=values)
    result = _retag_unmapped(result, unmapped)

    computed_at = datetime.now(UTC)
    score_id = uuid.uuid4()

    db.execute(
        text(
            """
            INSERT INTO score_calculation (
              id, account_id, entity_type, entity_id,
              referentiel_id, referentiel_version, referentiel_code,
              score_global, scores_by_pillar, details_json, coverage_ratio,
              computed_at, computed_by
            ) VALUES (
              CAST(:id AS UUID), CAST(:aid AS UUID), :etype, CAST(:eid AS UUID),
              CAST(:rid AS UUID), :rversion, :rcode,
              :score, CAST(:pillars AS JSONB), CAST(:details AS JSONB), :coverage,
              :computed_at, CAST(:uid AS UUID)
            )
            """
        ),
        {
            "id": str(score_id),
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
            "rid": str(ref["id"]),
            "rversion": ref["version"],
            "rcode": ref["code"],
            "score": result.score_global,
            "pillars": _json_dumps(result.scores_by_pillar),
            "details": _json_dumps(_serialize_details(result)),
            "coverage": result.coverage_ratio,
            "computed_at": computed_at,
            "uid": str(user_id) if user_id else None,
        },
    )

    record_audit(
        db,
        entity_type="score_calculation",
        entity_id=score_id,
        field="compute",
        new={
            "referentiel_code": ref["code"],
            "score_global": (
                float(result.score_global)
                if result.score_global is not None
                else None
            ),
            "coverage_ratio": (
                float(result.coverage_ratio)
                if result.coverage_ratio is not None
                else None
            ),
        },
        source_of_change=SourceOfChange.MANUAL,
        user_id=user_id,
        account_id=account_id,
    )

    return {
        "score_id": score_id,
        "referentiel_code": ref["code"],
        "referentiel_id": ref["id"],
        "referentiel_version": ref["version"],
        "score_global": result.score_global,
        "scores_by_pillar": dict(result.scores_by_pillar),
        "coverage_ratio": result.coverage_ratio,
        "computed_at": computed_at,
        "indicateurs_couverts": [
            {
                "indicateur_id": c.indicateur_id,
                "indicateur_code": c.indicateur_code,
                "pillar": c.pillar,
                "value": c.value,
                "normalized_value": c.normalized_value,
                "weight": c.weight,
                "contribution": c.contribution,
                "source_id": c.source_id,
            }
            for c in result.indicateurs_couverts
        ],
        "indicateurs_manquants": [
            {
                "indicateur_id": m.indicateur_id,
                "indicateur_code": m.indicateur_code,
                "pillar": m.pillar,
                "reason": m.reason,
            }
            for m in result.indicateurs_manquants
        ],
        "sources_used": list(result.sources_used),
    }


def get_latest_score_detail(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, referentiel_id, referentiel_version, referentiel_code,
                   score_global, scores_by_pillar, details_json, coverage_ratio,
                   computed_at
            FROM score_calculation
            WHERE account_id = CAST(:aid AS UUID)
              AND entity_type = :etype
              AND entity_id = CAST(:eid AS UUID)
              AND referentiel_code = :rcode
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        {
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
            "rcode": referentiel_code,
        },
    ).first()
    if row is None:
        return None
    details = row.details_json or {}
    return {
        "score_id": row.id,
        "referentiel_code": row.referentiel_code,
        "referentiel_id": row.referentiel_id,
        "referentiel_version": int(row.referentiel_version),
        "score_global": (
            float(row.score_global) if row.score_global is not None else None
        ),
        "scores_by_pillar": dict(row.scores_by_pillar or {}),
        "coverage_ratio": (
            float(row.coverage_ratio) if row.coverage_ratio is not None else None
        ),
        "computed_at": row.computed_at,
        "indicateurs_couverts": list(details.get("indicateurs_couverts", [])),
        "indicateurs_manquants": list(details.get("indicateurs_manquants", [])),
        "sources_used": list(details.get("sources_used", [])),
    }


def list_latest_scores(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (referentiel_id)
                referentiel_id, referentiel_version, referentiel_code,
                score_global, scores_by_pillar, coverage_ratio, computed_at
            FROM score_calculation
            WHERE account_id = CAST(:aid AS UUID)
              AND entity_type = :etype
              AND entity_id = CAST(:eid AS UUID)
            ORDER BY referentiel_id, computed_at DESC
            """
        ),
        {
            "aid": str(account_id),
            "etype": entity_type,
            "eid": str(entity_id),
        },
    ).fetchall()
    return [
        {
            "referentiel_code": r.referentiel_code,
            "referentiel_id": r.referentiel_id,
            "referentiel_version": int(r.referentiel_version),
            "score_global": (
                float(r.score_global) if r.score_global is not None else None
            ),
            "scores_by_pillar": dict(r.scores_by_pillar or {}),
            "coverage_ratio": (
                float(r.coverage_ratio) if r.coverage_ratio is not None else None
            ),
            "computed_at": r.computed_at,
        }
        for r in rows
    ]
