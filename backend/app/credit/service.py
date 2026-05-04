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
from app.credit.eligibility_catalog import EligibilityRule, active_catalog
from app.credit.subscore_mapping import FACTOR_TO_BUCKET, SUBSCORE_BUCKETS


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
# F48 - Sous-scores derives (vue, pas de stockage)                             #
# --------------------------------------------------------------------------- #


def compute_subscores(
    facteurs: list[dict[str, Any]] | None,
) -> dict[str, int | None] | None:
    """Agrege les facteurs en 4 sous-scores normalises 0-100.

    Pour chaque bucket, calcule la moyenne ponderee des contributions des
    facteurs presents (poids defini dans ``FACTOR_TO_BUCKET``).
    - Bucket sans facteur disponible -> ``None``.
    - Aucun facteur exploitable -> retourne ``None`` (pas de sous-scores).
    - Facteur non liste -> ignore (degradation gracieuse).
    """
    if not facteurs:
        return None

    bucket_acc: dict[str, list[tuple[float, float]]] = {b: [] for b in SUBSCORE_BUCKETS}
    any_mapped = False
    for f in facteurs:
        name = f.get("name") if isinstance(f, dict) else None
        if not isinstance(name, str):
            continue
        mapping = FACTOR_TO_BUCKET.get(name)
        if mapping is None:
            continue
        bucket, weight = mapping
        # Si le facteur n'a pas pu etre calcule (donnee absente), value est None
        # et contribution=0 — on ignore pour ne pas tirer le bucket vers le bas.
        if f.get("value") is None:
            continue
        contribution = f.get("contribution")
        if contribution is None:
            continue
        try:
            contrib_val = float(contribution)
        except (TypeError, ValueError):
            continue
        bucket_acc[bucket].append((contrib_val, weight))
        any_mapped = True

    if not any_mapped:
        return None

    out: dict[str, int | None] = {}
    for bucket in SUBSCORE_BUCKETS:
        items = bucket_acc[bucket]
        if not items:
            out[bucket] = None
            continue
        total_weight = sum(w for _, w in items)
        if total_weight <= 0:
            out[bucket] = None
            continue
        # contribution = value*weight (cf engine), deja sur echelle [0..1*weight].
        # On ramene chaque contribution au "score normalise du facteur" : c/w * 100,
        # puis on prend la moyenne ponderee par les poids du bucket.
        weighted_sum = 0.0
        for contrib, w in items:
            facteur_norm = (contrib / w) * 100.0 if w > 0 else 0.0
            weighted_sum += facteur_norm * w
        avg = weighted_sum / total_weight
        out[bucket] = max(0, min(100, round(avg)))
    return out


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
        "subscores": compute_subscores(result["facteurs"]),
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
        "subscores": compute_subscores(facteurs if isinstance(facteurs, list) else None),
    }


# --------------------------------------------------------------------------- #
# F48 - Historique (US7)                                                      #
# --------------------------------------------------------------------------- #


def list_history(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Retourne les ``limit`` derniers scores tries desc par computed_at.

    RLS-aware via filtre SQL ``account_id``.
    """
    rows = db.execute(
        text(
            """
            SELECT id, combine, solvabilite, impact_vert, facteurs,
                   methodologie_version, coherence_warning, computed_at
            FROM credit_score
            WHERE entreprise_id=:e AND account_id=:a
            ORDER BY computed_at DESC
            LIMIT :lim
            """
        ),
        {"e": str(entreprise_id), "a": str(account_id), "lim": int(limit)},
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        facteurs = row.facteurs
        if isinstance(facteurs, str):
            try:
                facteurs = json.loads(facteurs)
            except ValueError:
                facteurs = []
        out.append(
            {
                "id": row.id,
                "combine": int(row.combine),
                "solvabilite": int(row.solvabilite),
                "impact_vert": int(row.impact_vert),
                "subscores": compute_subscores(
                    facteurs if isinstance(facteurs, list) else None
                ),
                "methodologie_version": int(row.methodologie_version),
                "coherence_warning": bool(row.coherence_warning),
                "computed_at": row.computed_at,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# F48 - Eligibility (US3)                                                     #
# --------------------------------------------------------------------------- #


def _entreprise_profile(
    db: Session, account_id: UUID, entreprise_id: UUID
) -> dict[str, Any]:
    """Retourne {secteur_code, taille_label} pour l'evaluation eligibility."""
    out: dict[str, Any] = {"secteur_code": None, "taille_label": None}
    if not _table_exists(db, "entreprise"):
        return out
    try:
        row = db.execute(
            text(
                """
                SELECT secteur_code, taille_effectifs
                FROM entreprise
                WHERE id=:e AND account_id=:a
                """
            ),
            {"e": str(entreprise_id), "a": str(account_id)},
        ).fetchone()
    except Exception:  # noqa: BLE001
        return out
    if row is None:
        return out
    out["secteur_code"] = row.secteur_code
    eff = row.taille_effectifs
    if eff is not None:
        if eff < 10:
            out["taille_label"] = "tpe"
        elif eff < 250:
            out["taille_label"] = "pme"
        else:
            out["taille_label"] = "eti"
    else:
        out["taille_label"] = "pme"  # defaut si non renseigne
    return out


_SIZE_ORDER = {"tpe": 0, "pme": 1, "eti": 2}


def _eval_rule(
    rule: EligibilityRule,
    score: dict[str, Any] | None,
    profile: dict[str, Any],
) -> dict[str, Any]:
    criteria: list[dict[str, Any]] = []
    has_incomplete = False

    if score is None:
        # Aucun score -> tous les criteres deviennent incomplete
        if rule.min_combine_score is not None:
            criteria.append(
                {
                    "code": "min_combine_score",
                    "label": f"Score credit >= {rule.min_combine_score}",
                    "threshold": str(rule.min_combine_score),
                    "actual": None,
                    "met": False,
                    "blocking": True,
                }
            )
            has_incomplete = True
        return {
            "rule": rule,
            "status": "incomplete",
            "primary_reason": "Score credit non calcule",
            "criteria": criteria,
        }

    combine = int(score.get("combine") or 0)
    subscores = score.get("subscores") or {}

    # Critere score combine
    if rule.min_combine_score is not None:
        met = combine >= rule.min_combine_score
        criteria.append(
            {
                "code": "min_combine_score",
                "label": f"Score credit >= {rule.min_combine_score}",
                "threshold": str(rule.min_combine_score),
                "actual": str(combine),
                "met": met,
                "blocking": True,
            }
        )

    # Sous-score ESG
    if rule.min_subscore_engagement_esg is not None:
        actual = subscores.get("engagement_esg")
        if actual is None:
            criteria.append(
                {
                    "code": "min_subscore_engagement_esg",
                    "label": f"Engagement ESG >= {rule.min_subscore_engagement_esg}",
                    "threshold": str(rule.min_subscore_engagement_esg),
                    "actual": None,
                    "met": False,
                    "blocking": True,
                }
            )
            has_incomplete = True
        else:
            met = int(actual) >= rule.min_subscore_engagement_esg
            criteria.append(
                {
                    "code": "min_subscore_engagement_esg",
                    "label": f"Engagement ESG >= {rule.min_subscore_engagement_esg}",
                    "threshold": str(rule.min_subscore_engagement_esg),
                    "actual": str(int(actual)),
                    "met": met,
                    "blocking": True,
                }
            )

    # Sous-score solidite financiere
    if rule.min_subscore_solidite_financiere is not None:
        actual = subscores.get("solidite_financiere")
        if actual is None:
            criteria.append(
                {
                    "code": "min_subscore_solidite_financiere",
                    "label": (
                        f"Solidite financiere >= "
                        f"{rule.min_subscore_solidite_financiere}"
                    ),
                    "threshold": str(rule.min_subscore_solidite_financiere),
                    "actual": None,
                    "met": False,
                    "blocking": True,
                }
            )
            has_incomplete = True
        else:
            met = int(actual) >= rule.min_subscore_solidite_financiere
            criteria.append(
                {
                    "code": "min_subscore_solidite_financiere",
                    "label": (
                        f"Solidite financiere >= "
                        f"{rule.min_subscore_solidite_financiere}"
                    ),
                    "threshold": str(rule.min_subscore_solidite_financiere),
                    "actual": str(int(actual)),
                    "met": met,
                    "blocking": True,
                }
            )

    # Secteurs exclus
    secteur = profile.get("secteur_code") or ""
    if rule.excluded_sectors:
        excluded = secteur.lower() in {s.lower() for s in rule.excluded_sectors}
        criteria.append(
            {
                "code": "excluded_sectors",
                "label": "Secteur non exclu",
                "threshold": "none",
                "actual": secteur or "non_renseigne",
                "met": not excluded,
                "blocking": True,
            }
        )

    # Taille minimum
    if rule.required_min_size is not None:
        size = profile.get("taille_label") or "pme"
        met = _SIZE_ORDER.get(size, 0) >= _SIZE_ORDER.get(rule.required_min_size, 0)
        criteria.append(
            {
                "code": "required_min_size",
                "label": f"Taille minimum {rule.required_min_size}",
                "threshold": rule.required_min_size,
                "actual": size,
                "met": met,
                "blocking": True,
            }
        )

    # Determiner statut
    if has_incomplete:
        primary = next(
            (
                c["label"] + " : donnee manquante"
                for c in criteria
                if not c["met"] and c["actual"] is None
            ),
            "Donnees insuffisantes",
        )
        return {
            "rule": rule,
            "status": "incomplete",
            "primary_reason": primary,
            "criteria": criteria,
        }

    blocking_failed = [c for c in criteria if not c["met"] and c["blocking"]]
    if blocking_failed:
        primary = blocking_failed[0]["label"]
        return {
            "rule": rule,
            "status": "not_eligible",
            "primary_reason": primary,
            "criteria": criteria,
        }

    return {
        "rule": rule,
        "status": "eligible",
        "primary_reason": None,
        "criteria": criteria,
    }


def evaluate_eligibility(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID,
) -> dict[str, Any]:
    """Evalue l'eligibilite de la PME au catalogue actif."""
    catalog = active_catalog()
    try:
        score = get_latest_score(
            db, account_id=account_id, entreprise_id=entreprise_id
        )
    except CreditScoreNotFound:
        score = None

    profile = _entreprise_profile(db, account_id, entreprise_id)

    items: list[dict[str, Any]] = []
    for rule in catalog:
        evaluated = _eval_rule(rule, score, profile)
        rule_obj = evaluated["rule"]
        items.append(
            {
                "code": rule_obj.code,
                "label": rule_obj.label,
                "description": rule_obj.description,
                "status": evaluated["status"],
                "primary_reason": evaluated["primary_reason"],
                "criteria": evaluated["criteria"],
                "matching_offer_query": rule_obj.matching_offer_query,
                "source_id": rule_obj.source_id,
                "version": rule_obj.version,
                "valid_from": rule_obj.valid_from,
                "valid_to": rule_obj.valid_to,
            }
        )
    catalog_version_max = max((r.version for r in catalog), default=0)
    return {
        "items": items,
        "evaluated_at": datetime.now(UTC),
        "catalog_version_max": catalog_version_max,
    }


# --------------------------------------------------------------------------- #
# F48 - Recommendations (US4)                                                 #
# --------------------------------------------------------------------------- #


def _has_action_item_table(db: Session) -> bool:
    return _table_exists(db, "action_item")


def list_recommendations(
    db: Session,
    *,
    account_id: UUID,
    entreprise_id: UUID,
    limit: int = 5,
) -> dict[str, Any]:
    """Selectionne les top-N actions F45 ciblant les sous-scores faibles.

    Strategie (clarif Q1) : tri ASC des sous-scores, on prend les actions
    rattachees au bucket le plus faible, puis on elargit aux suivants tant
    qu'on n'atteint pas ``limit``. Filtre par impact > 0, tri desc par impact.
    """
    if not _has_action_item_table(db):
        return {"items": [], "selected_subscores": []}

    # Score courant pour identifier les buckets faibles
    try:
        score = get_latest_score(
            db, account_id=account_id, entreprise_id=entreprise_id
        )
    except CreditScoreNotFound:
        return {"items": [], "selected_subscores": []}

    subscores = score.get("subscores") or {}
    # Trier les buckets par valeur (None traite comme 0 = priorite max)
    ranked_buckets = sorted(
        SUBSCORE_BUCKETS,
        key=lambda b: (
            subscores.get(b) if subscores.get(b) is not None else -1
        ),
    )

    # Verifier que les colonnes F45 sont presentes (graceful skip sinon)
    try:
        has_cols = db.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name='action_item'
                  AND column_name IN ('target_subscore',
                                      'estimated_credit_points_impact')
                """
            )
        ).fetchall()
    except Exception:  # noqa: BLE001
        return {"items": [], "selected_subscores": []}
    if len({r.column_name for r in has_cols}) < 2:
        return {"items": [], "selected_subscores": []}

    selected: list[dict[str, Any]] = []
    selected_subscores: list[str] = []
    for bucket in ranked_buckets:
        if len(selected) >= limit:
            break
        try:
            rows = db.execute(
                text(
                    """
                    SELECT id, title, description, target_subscore,
                           estimated_credit_points_impact
                    FROM action_item
                    WHERE account_id=:a
                      AND target_subscore=:b
                      AND estimated_credit_points_impact > 0
                    ORDER BY estimated_credit_points_impact DESC
                    """
                ),
                {"a": str(account_id), "b": bucket},
            ).fetchall()
        except Exception:  # noqa: BLE001
            return {"items": [], "selected_subscores": []}
        if not rows:
            continue
        selected_subscores.append(bucket)
        for r in rows:
            if len(selected) >= limit:
                break
            selected.append(
                {
                    "step_id": r.id,
                    "title": r.title,
                    "description": r.description,
                    "target_subscore": r.target_subscore,
                    "estimated_credit_points_impact": int(
                        r.estimated_credit_points_impact
                    ),
                }
            )
    # Tri global desc par impact
    selected.sort(
        key=lambda x: x["estimated_credit_points_impact"], reverse=True
    )
    return {"items": selected[:limit], "selected_subscores": selected_subscores}
