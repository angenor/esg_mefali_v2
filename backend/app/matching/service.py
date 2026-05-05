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


# ============================================================================
# F51 — Catalogue listing & detail (GET /me/offres, GET /me/offres/{id}).
# ============================================================================

from app.core.currencies import PEG_FCFA_EUR as FCFA_PER_EUR  # noqa: E402

# Mapping fallback de fonds_source.type → OffreType. La plupart des seeds
# utilisent des libellés libres ; on normalise.
_FONDS_TYPE_TO_OFFRE_TYPE: dict[str, str] = {
    "subvention": "subvention",
    "grant": "subvention",
    "credit": "credit",
    "loan": "credit",
    "pret": "credit",
    "garantie": "garantie",
    "guarantee": "garantie",
}


def _resolve_offre_type(offre_type: str | None, fonds_type: str | None) -> str:
    """Override offre.offre_type, sinon mapping fonds_source.type, sinon 'autre'."""
    if offre_type:
        return offre_type
    if fonds_type:
        normalized = fonds_type.strip().lower()
        return _FONDS_TYPE_TO_OFFRE_TYPE.get(normalized, "autre")
    return "autre"


def _money_to_eur_int(amount: Decimal | None, currency: str | None) -> int | None:
    """Convertit un montant en int EUR pour le filtrage SQL (parité 655.957)."""
    if amount is None or currency is None:
        return None
    if currency == "EUR":
        return int(amount)
    if currency == "XOF":
        return int(amount / FCFA_PER_EUR)
    return None


def _build_money(amount: Decimal | None, currency: str | None) -> dict | None:
    if amount is None or currency is None:
        return None
    return {"amount": str(amount), "currency": currency}


def _row_to_list_item(row: dict) -> dict:
    """Sérialise un row catalogue → OffreListItem dict."""
    geo = None
    if row.get("geo_lat") is not None and row.get("geo_lng") is not None:
        geo = {"lat": float(row["geo_lat"]), "lng": float(row["geo_lng"])}
    inter = {
        "id": str(row["intermediaire_id"]) if row.get("intermediaire_id") else str(row["fonds_id"]),
        "nom": row.get("intermediaire_name") or row.get("fonds_name") or "—",
        "geolocation": geo,
        "url": None,
    }
    secteurs = row.get("secteurs") or []
    if not secteurs and row.get("fonds_thematique"):
        secteurs = [str(row["fonds_thematique"]).strip().lower()]
    return {
        "offre_id": str(row["offre_id"]),
        "nom": row.get("offre_name") or row.get("fonds_name") or "Offre",
        "intermediaire": inter,
        "type": _resolve_offre_type(row.get("offre_type"), row.get("fonds_type")),
        "montant_min": _build_money(row.get("plancher_amount"), row.get("plancher_currency")),
        "montant_max": _build_money(row.get("plafond_amount"), row.get("plafond_currency")),
        "duree_min_mois": row.get("duree_min_mois"),
        "duree_max_mois": row.get("duree_max_mois"),
        "secteurs": list(secteurs) if secteurs else [],
        "accepted_languages": row.get("accepted_languages") or ["fr"],
    }


def list_offres_for_account(
    db: Session,
    *,
    account_id: UUID,  # noqa: ARG001 — utilisé pour set_config en amont (RLS)
    filters: dict[str, Any],
    limit: int = 20,
) -> list[dict]:
    """Catalogue d'offres publiées, filtrable. Aucun scoring.

    Le compte courant est posé en amont via ``app.current_account_id`` (RLS),
    mais ``offre`` n'a pas de ``account_id`` (catalogue partagé) — la
    visibilité est gouvernée par ``status='published'`` (P7 + F08).
    """
    where = ["o.status = 'published'", "f.status = 'published'"]
    params: dict[str, Any] = {"lim": int(limit)}

    if filters.get("type"):
        # Filtre type : applique l'override offre.offre_type OU le mapping fonds.type.
        # Pour rester simple en SQL, on filtre sur offre_type quand non-NULL et sur
        # fonds_source.type sinon, en faisant le mapping côté Python après lecture.
        params["type_in"] = filters["type"]
        where.append(
            "(o.offre_type = :type_in OR (o.offre_type IS NULL AND lower(f.type) = :type_in))"
        )
    if filters.get("intermediaire_id"):
        params["iid"] = str(filters["intermediaire_id"])
        where.append("i.id = CAST(:iid AS UUID)")
    if filters.get("secteur"):
        params["sect"] = filters["secteur"]
        where.append("(:sect = ANY(f.secteurs) OR lower(f.thematique) = :sect)")
    if filters.get("q"):
        params["q"] = f"%{filters['q'].lower()}%"
        where.append("(lower(o.name) LIKE :q OR lower(f.name) LIKE :q)")
    if filters.get("duree_min_mois") is not None:
        params["dmn"] = int(filters["duree_min_mois"])
        where.append("(o.duree_max_mois IS NULL OR o.duree_max_mois >= :dmn)")
    if filters.get("duree_max_mois") is not None:
        params["dmx"] = int(filters["duree_max_mois"])
        where.append("(o.duree_min_mois IS NULL OR o.duree_min_mois <= :dmx)")
    # Filtres montant : effectués post-lecture en Python pour gérer la conversion devise.

    sql = f"""
        SELECT
            o.id            AS offre_id,
            o.name          AS offre_name,
            o.offre_type    AS offre_type,
            o.duree_min_mois AS duree_min_mois,
            o.duree_max_mois AS duree_max_mois,
            o.accepted_languages AS accepted_languages,
            f.id            AS fonds_id,
            f.name          AS fonds_name,
            f.type          AS fonds_type,
            f.thematique    AS fonds_thematique,
            f.secteurs      AS secteurs,
            f.plafond_amount   AS plafond_amount,
            f.plafond_currency AS plafond_currency,
            f.plancher_amount  AS plancher_amount,
            f.plancher_currency AS plancher_currency,
            i.id            AS intermediaire_id,
            i.name          AS intermediaire_name,
            i.geo_lat       AS geo_lat,
            i.geo_lng       AS geo_lng
        FROM offre o
        JOIN fonds_source f ON f.id = o.fonds_id
        LEFT JOIN intermediaire i ON i.id = o.intermediaire_id AND i.status = 'published'
        WHERE {' AND '.join(where)}
        ORDER BY o.created_at DESC
        LIMIT :lim
    """
    rows = db.execute(text(sql), params).mappings().all()
    items: list[dict] = []
    mn_eur = filters.get("montant_min_eur")
    mx_eur = filters.get("montant_max_eur")
    for r in rows:
        item = _row_to_list_item(dict(r))
        # Filtrage montant en EUR équivalent (parité fixe).
        plancher_eur = _money_to_eur_int(r["plancher_amount"], r["plancher_currency"])
        plafond_eur = _money_to_eur_int(r["plafond_amount"], r["plafond_currency"])
        if mn_eur is not None and plafond_eur is not None and plafond_eur < mn_eur:
            continue
        if mx_eur is not None and plancher_eur is not None and plancher_eur > mx_eur:
            continue
        items.append(item)
    return items


def get_offre_detail(
    db: Session,
    *,
    account_id: UUID,  # noqa: ARG001
    offre_id: UUID,
) -> dict | None:
    """Détail d'une offre publiée. Renvoie None si invisible / non publiée."""
    row = db.execute(
        text(
            """
            SELECT
                o.id            AS offre_id,
                o.name          AS offre_name,
                o.offre_type    AS offre_type,
                o.duree_min_mois AS duree_min_mois,
                o.duree_max_mois AS duree_max_mois,
                o.accepted_languages AS accepted_languages,
                o.criteres_offre_specifiques AS criteres_offre,
                o.documents_specifiques      AS documents_offre,
                f.id            AS fonds_id,
                f.name          AS fonds_name,
                f.type          AS fonds_type,
                f.thematique    AS fonds_thematique,
                f.secteurs      AS secteurs,
                f.plafond_amount   AS plafond_amount,
                f.plafond_currency AS plafond_currency,
                f.plancher_amount  AS plancher_amount,
                f.plancher_currency AS plancher_currency,
                f.documents_requis_json AS fonds_documents,
                i.id            AS intermediaire_id,
                i.name          AS intermediaire_name,
                i.geo_lat       AS geo_lat,
                i.geo_lng       AS geo_lng,
                i.documents_requis_json AS intermediaire_documents
            FROM offre o
            JOIN fonds_source f ON f.id = o.fonds_id AND f.status = 'published'
            LEFT JOIN intermediaire i ON i.id = o.intermediaire_id AND i.status = 'published'
            WHERE o.id = CAST(:oid AS UUID) AND o.status = 'published'
            """
        ),
        {"oid": str(offre_id)},
    ).mappings().first()
    if row is None:
        return None
    base = _row_to_list_item(dict(row))

    # Documents requis = union fonds_source.documents_requis_json + intermediaire.documents_requis_json
    # + offre.documents_specifiques. Format permissif (le seed est libre — on gère best-effort).
    docs: list[dict] = []
    seen: set[str] = set()
    for raw in (
        row.get("fonds_documents") or [],
        row.get("intermediaire_documents") or [],
        row.get("documents_offre") or [],
    ):
        if not isinstance(raw, list):
            continue
        for it in raw:
            if isinstance(it, dict):
                key = str(it.get("key") or it.get("name") or it.get("label") or "").strip()
                label = str(it.get("label") or it.get("name") or key)
                fmt = str(it.get("format") or "pdf")
            elif isinstance(it, str):
                key = it.strip().lower().replace(" ", "_")
                label = it
                fmt = "pdf"
            else:
                continue
            if not key or key in seen:
                continue
            seen.add(key)
            docs.append({"key": key, "label": label, "format": fmt})

    base.update(
        {
            "description": row.get("fonds_thematique") or "",
            "documents_requis": docs,
            "conditions": [],
            "lien_externe": None,
            "source_id": None,
        }
    )
    return base
