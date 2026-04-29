"""F25 — Service de matching projet <-> offre."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.matching.heuristics import (
    LayerScore,
    eval_critere_json,
    eval_geo,
    eval_instruments,
    eval_money_range,
    eval_thematique,
    score_layer,
)
from app.matching.schemas import (
    ComparatorRow,
    CritereMatch,
    MatchDetail,
    OfferMatch,
)
from app.schemas.money import Money


class ProjetNotFound(Exception):
    """Projet inconnu ou hors-tenant."""


class OffreNotFound(Exception):
    """Offre inconnue, non publiée, ou sans accréditation active."""


def _load_projet(
    db: Session, *, account_id: UUID, projet_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, account_id, montant_recherche_amount, montant_recherche_currency,
                   types_impact, localisation_pays_iso2, structure_financement_arr
            FROM projet
            WHERE id = CAST(:pid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            """
        ),
        {"pid": str(projet_id), "aid": str(account_id)},
    ).mappings().first()
    if row is None:
        return None
    return dict(row)


def _load_offres_published(
    db: Session, *, fonds_id: UUID | None = None
) -> list[dict[str, Any]]:
    where_extra = "AND o.fonds_id = CAST(:fid AS UUID)" if fonds_id else ""
    sql = f"""
        SELECT
            o.id            AS offre_id,
            o.name          AS offre_name,
            o.deadline      AS offre_deadline,
            o.criteres_offre_specifiques AS offre_criteres,
            o.documents_specifiques      AS offre_documents,
            o.frais_specifiques          AS offre_frais,
            o.delais_specifiques         AS offre_delais,
            f.id            AS fonds_id,
            f.name          AS fonds_name,
            f.thematique    AS fonds_thematique,
            f.instruments   AS fonds_instruments,
            f.plafond_money AS fonds_plafond,
            f.plancher_money AS fonds_plancher,
            f.eligibilite_geo AS fonds_geo,
            f.criteres_json AS fonds_criteres,
            f.documents_requis_json AS fonds_documents,
            f.frais_json    AS fonds_frais,
            f.delais_json   AS fonds_delais,
            f.source_ids    AS fonds_source_ids,
            i.id            AS intermediaire_id,
            i.name          AS intermediaire_name,
            i.pays          AS intermediaire_pays,
            i.criteres_json AS intermediaire_criteres,
            i.documents_requis_json AS intermediaire_documents,
            i.frais_json    AS intermediaire_frais,
            i.delais_json   AS intermediaire_delais,
            i.source_ids    AS intermediaire_source_ids
        FROM offre o
        JOIN fonds_source f ON f.id = o.fonds_id AND f.status = 'published'
        LEFT JOIN intermediaire i ON i.id = o.intermediaire_id AND i.status = 'published'
        WHERE o.status = 'published'
          AND (
            o.intermediaire_id IS NULL
            OR EXISTS (
              SELECT 1 FROM accreditation a
              WHERE a.intermediaire_id = o.intermediaire_id
                AND a.fonds_id = o.fonds_id
                AND a.status = 'published'
                AND (a.valid_to IS NULL OR a.valid_to > now())
            )
          )
          {where_extra}
        ORDER BY o.created_at DESC
    """
    params: dict[str, str] = {}
    if fonds_id:
        params["fid"] = str(fonds_id)
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _safe_money(value: Any) -> Money | None:
    if not isinstance(value, dict):
        return None
    amt = value.get("amount")
    cur = value.get("currency")
    if amt is None or cur is None:
        return None
    try:
        return Money(amount=Decimal(str(amt)), currency=cur)
    except Exception:
        return None


def _safe_int(value: Any, *keys: str) -> int | None:
    if not isinstance(value, dict):
        return None
    for k in keys:
        if value.get(k) is not None:
            try:
                return int(value[k])
            except (TypeError, ValueError):
                return None
    return None


def _merge_documents(fonds_docs: Any, intermediaire_docs: Any, offre_docs: Any) -> list[str]:
    out: dict[str, None] = {}
    for src in (
        _safe_list(fonds_docs),
        _safe_list(intermediaire_docs),
        _safe_list(offre_docs),
    ):
        for d in src:
            label = None
            if isinstance(d, str):
                label = d
            elif isinstance(d, dict):
                label = d.get("label") or d.get("name") or d.get("code")
            if label:
                out.setdefault(str(label), None)
    return list(out.keys())


def _build_fonds_criteres(*, projet: dict[str, Any], offre_row: dict[str, Any]) -> list[CritereMatch]:
    criteres: list[CritereMatch] = []
    criteres.append(
        eval_money_range(
            projet_amount=projet.get("montant_recherche_amount"),
            projet_currency=projet.get("montant_recherche_currency"),
            plancher=offre_row.get("fonds_plancher"),
            plafond=offre_row.get("fonds_plafond"),
        )
    )
    criteres.append(
        eval_geo(
            projet_pays_iso2=projet.get("localisation_pays_iso2"),
            eligibilite_geo=offre_row.get("fonds_geo") or [],
        )
    )
    criteres.append(
        eval_thematique(
            projet_types_impact=projet.get("types_impact") or [],
            fonds_thematique=offre_row.get("fonds_thematique") or [],
        )
    )
    criteres.append(
        eval_instruments(
            projet_structure=projet.get("structure_financement_arr") or [],
            fonds_instruments=offre_row.get("fonds_instruments") or [],
        )
    )
    raw: list[Any] = []
    raw.extend(_safe_list(offre_row.get("fonds_criteres")))
    raw.extend(_safe_list(offre_row.get("offre_criteres")))
    for c in raw:
        if isinstance(c, dict):
            criteres.append(eval_critere_json(c))
    return criteres


def _build_intermediaire_criteres(
    *, projet: dict[str, Any], offre_row: dict[str, Any]
) -> list[CritereMatch]:
    criteres: list[CritereMatch] = []
    if offre_row.get("intermediaire_id") is None:
        return criteres
    pays = offre_row.get("intermediaire_pays") or []
    criteres.append(
        eval_geo(
            projet_pays_iso2=projet.get("localisation_pays_iso2"),
            eligibilite_geo=pays,
        )
    )
    raw = _safe_list(offre_row.get("intermediaire_criteres"))
    for c in raw:
        if isinstance(c, dict):
            criteres.append(eval_critere_json(c))
    return criteres


def _compute_match(
    *, projet: dict[str, Any], offre_row: dict[str, Any]
) -> tuple[LayerScore, LayerScore]:
    fonds = score_layer(_build_fonds_criteres(projet=projet, offre_row=offre_row))
    inter = score_layer(_build_intermediaire_criteres(projet=projet, offre_row=offre_row))
    return fonds, inter


def _as_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _to_offer_match(
    *, offre_row: dict[str, Any], fonds: LayerScore, inter: LayerScore
) -> OfferMatch:
    deadline = offre_row.get("offre_deadline")
    return OfferMatch(
        offre_id=_as_uuid(offre_row["offre_id"]),
        fonds_id=_as_uuid(offre_row["fonds_id"]),
        intermediaire_id=_as_uuid(offre_row.get("intermediaire_id")),
        fonds_score=fonds.score,
        intermediaire_score=inter.score,
        score_global=min(fonds.score, inter.score),
        libelle=str(offre_row.get("offre_name") or offre_row.get("fonds_name") or ""),
        deadline_iso=deadline.isoformat() if deadline is not None else None,
    )


def _sort_key(item: tuple[OfferMatch, dict[str, Any]]) -> tuple[float, float, float]:
    om, row = item
    deadline = row.get("offre_deadline")
    deadline_key = deadline.timestamp() if deadline is not None else float("inf")
    return (-om.score_global, -om.fonds_score, deadline_key)


def match(
    db: Session, *, account_id: UUID, projet_id: UUID, max: int = 10
) -> list[OfferMatch]:
    projet = _load_projet(db, account_id=account_id, projet_id=projet_id)
    if projet is None:
        raise ProjetNotFound(str(projet_id))
    offres = _load_offres_published(db)
    pairs: list[tuple[OfferMatch, dict[str, Any]]] = []
    for offre_row in offres:
        f, i = _compute_match(projet=projet, offre_row=offre_row)
        pairs.append((_to_offer_match(offre_row=offre_row, fonds=f, inter=i), offre_row))
    pairs.sort(key=_sort_key)
    return [p[0] for p in pairs[:max]]


def detail(
    db: Session, *, account_id: UUID, projet_id: UUID, offre_id: UUID
) -> MatchDetail:
    projet = _load_projet(db, account_id=account_id, projet_id=projet_id)
    if projet is None:
        raise ProjetNotFound(str(projet_id))
    offres = [
        o for o in _load_offres_published(db) if str(o.get("offre_id")) == str(offre_id)
    ]
    if not offres:
        raise OffreNotFound(str(offre_id))
    offre_row = offres[0]
    fonds_score, inter_score = _compute_match(projet=projet, offre_row=offre_row)
    docs = _merge_documents(
        offre_row.get("fonds_documents"),
        offre_row.get("intermediaire_documents"),
        offre_row.get("offre_documents"),
    )
    frais = (
        _safe_money(offre_row.get("offre_frais"))
        or _safe_money(offre_row.get("intermediaire_frais"))
        or _safe_money(offre_row.get("fonds_frais"))
    )
    delais = (
        _safe_int(offre_row.get("offre_delais"), "instruction_jours", "delais_jours")
        or _safe_int(offre_row.get("intermediaire_delais"), "instruction_jours", "delais_jours")
        or _safe_int(offre_row.get("fonds_delais"), "instruction_jours", "delais_jours")
    )
    return MatchDetail(
        offre_id=_as_uuid(offre_row["offre_id"]),
        fonds_id=_as_uuid(offre_row["fonds_id"]),
        intermediaire_id=_as_uuid(offre_row.get("intermediaire_id")),
        fonds_score=fonds_score.score,
        intermediaire_score=inter_score.score,
        score_global=min(fonds_score.score, inter_score.score),
        criteres_couverts_fonds=fonds_score.couverts,
        criteres_manquants_fonds=fonds_score.manquants,
        criteres_couverts_intermediaire=inter_score.couverts,
        criteres_manquants_intermediaire=inter_score.manquants,
        documents_requis=docs,
        frais_effectifs=frais,
        delais_effectifs_jours=delais,
    )


def comparator(
    db: Session, *, account_id: UUID, fonds_id: UUID, projet_id: UUID, limit: int = 5
) -> list[ComparatorRow]:
    projet = _load_projet(db, account_id=account_id, projet_id=projet_id)
    if projet is None:
        raise ProjetNotFound(str(projet_id))
    offres = _load_offres_published(db, fonds_id=fonds_id)
    rows: list[ComparatorRow] = []
    for offre_row in offres:
        fonds_score, inter_score = _compute_match(projet=projet, offre_row=offre_row)
        docs = _merge_documents(
            offre_row.get("fonds_documents"),
            offre_row.get("intermediaire_documents"),
            offre_row.get("offre_documents"),
        )
        frais = (
            _safe_money(offre_row.get("offre_frais"))
            or _safe_money(offre_row.get("intermediaire_frais"))
            or _safe_money(offre_row.get("fonds_frais"))
        )
        delais = (
            _safe_int(offre_row.get("offre_delais"), "instruction_jours", "delais_jours")
            or _safe_int(offre_row.get("intermediaire_delais"), "instruction_jours", "delais_jours")
            or _safe_int(offre_row.get("fonds_delais"), "instruction_jours", "delais_jours")
        )
        rows.append(
            ComparatorRow(
                offre_id=_as_uuid(offre_row["offre_id"]),
                intermediaire_id=_as_uuid(offre_row.get("intermediaire_id")),
                intermediaire_name=str(offre_row.get("intermediaire_name") or "—"),
                fonds_score=fonds_score.score,
                intermediaire_score=inter_score.score,
                score_global=min(fonds_score.score, inter_score.score),
                delais_effectifs_jours=delais,
                frais_effectifs=frais,
                documents_count=len(docs),
            )
        )
    rows.sort(key=lambda r: (-r.score_global, -r.fonds_score))
    return rows[:limit]


def serialize_critere(c: CritereMatch) -> dict[str, Any]:
    d = asdict(c)
    if c.source_id is not None:
        d["source_id"] = str(c.source_id)
    return d


def serialize_money(m: Money | None) -> dict[str, str] | None:
    if m is None:
        return None
    return {"amount": format(m.amount, "f"), "currency": m.currency.value}


def serialize_offer_match(om: OfferMatch) -> dict[str, Any]:
    return {
        "offre_id": str(om.offre_id) if om.offre_id else None,
        "fonds_id": str(om.fonds_id) if om.fonds_id else None,
        "intermediaire_id": str(om.intermediaire_id) if om.intermediaire_id else None,
        "fonds_score": om.fonds_score,
        "intermediaire_score": om.intermediaire_score,
        "score_global": om.score_global,
        "libelle": om.libelle,
        "deadline_iso": om.deadline_iso,
    }


def serialize_match_detail(md: MatchDetail) -> dict[str, Any]:
    return {
        "offre_id": str(md.offre_id) if md.offre_id else None,
        "fonds_id": str(md.fonds_id) if md.fonds_id else None,
        "intermediaire_id": str(md.intermediaire_id) if md.intermediaire_id else None,
        "fonds_score": md.fonds_score,
        "intermediaire_score": md.intermediaire_score,
        "score_global": md.score_global,
        "criteres_couverts_fonds": [serialize_critere(c) for c in md.criteres_couverts_fonds],
        "criteres_manquants_fonds": [serialize_critere(c) for c in md.criteres_manquants_fonds],
        "criteres_couverts_intermediaire": [serialize_critere(c) for c in md.criteres_couverts_intermediaire],
        "criteres_manquants_intermediaire": [serialize_critere(c) for c in md.criteres_manquants_intermediaire],
        "documents_requis": md.documents_requis,
        "frais_effectifs": serialize_money(md.frais_effectifs),
        "delais_effectifs_jours": md.delais_effectifs_jours,
    }


def serialize_comparator_row(row: ComparatorRow) -> dict[str, Any]:
    return {
        "offre_id": str(row.offre_id) if row.offre_id else None,
        "intermediaire_id": str(row.intermediaire_id) if row.intermediaire_id else None,
        "intermediaire_name": row.intermediaire_name,
        "fonds_score": row.fonds_score,
        "intermediaire_score": row.intermediaire_score,
        "score_global": row.score_global,
        "delais_effectifs_jours": row.delais_effectifs_jours,
        "frais_effectifs": serialize_money(row.frais_effectifs),
        "documents_count": row.documents_count,
    }
