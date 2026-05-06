"""F27 - Service de simulation financiere.

Lecture seule depuis projet, offre, fonds_source, intermediaire.
Pas de mutation, pas de record_audit (FR-008).

Coherence : reutilise le pattern F25 (matching/service.py) pour les SQL `text()`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.currencies import Currency
from app.schemas.money import Money
from app.simulation.calculator import (
    compute_pct_of,
    convert_to_xof,
    extract_pct,
    interets_simples,
)
from app.simulation.schemas import (
    ComparatorResult,
    DecompositionPct,
    FormulaRef,
    Instrument,
    MensualiteEntry,
    SimulationHypotheses,
    SimulationResult,
    SimulationResults,
)


class ProjetNotFound(Exception):
    """Projet inconnu, hors-tenant, ou supprime."""


class OffreNotFound(Exception):
    """Offre inconnue ou non publiee."""


# Defauts par instrument (taux annuel %, source : moyennes catalog).
_DEFAULT_TAUX: dict[str, Decimal] = {
    "subvention": Decimal("0"),
    "equity": Decimal("0"),
    "pret": Decimal("4"),
    "blending": Decimal("3"),
}


def _normalize_instrument(instruments: Any) -> Instrument:
    if not isinstance(instruments, list) or not instruments:
        return "unknown"
    first = str(instruments[0]).lower().strip()
    if "subvention" in first or "grant" in first:
        return "subvention"
    if "equity" in first or "fonds propres" in first:
        return "equity"
    if "blending" in first or "mixte" in first:
        return "blending"
    if "pret" in first or "prêt" in first or "loan" in first or "concession" in first:
        return "pret"
    return "unknown"


def _money_from_jsonb(payload: Any) -> Money | None:
    if not isinstance(payload, dict):
        return None
    amt = payload.get("amount")
    cur = payload.get("currency")
    if amt is None or cur is None:
        return None
    try:
        return Money(amount=Decimal(str(amt)), currency=cur)
    except Exception:
        return None


def _to_uuid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _load_projet(
    db: Session, *, account_id: UUID, projet_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, account_id, montant_recherche_amount,
                   montant_recherche_currency, duree_mois
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


def _load_offre_full(
    db: Session, *, offre_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
                o.id            AS offre_id,
                o.frais_specifiques AS offre_frais,
                o.source_ids    AS offre_source_ids,
                f.id            AS fonds_id,
                f.instruments   AS fonds_instruments,
                f.plafond_money AS fonds_plafond,
                f.plancher_money AS fonds_plancher,
                f.frais_json    AS fonds_frais,
                f.source_ids    AS fonds_source_ids,
                i.id            AS intermediaire_id,
                i.frais_json    AS intermediaire_frais,
                i.source_ids    AS intermediaire_source_ids
            FROM offre o
            JOIN fonds_source f ON f.id = o.fonds_id AND f.status = 'published'
            LEFT JOIN intermediaire i
              ON i.id = o.intermediaire_id AND i.status = 'published'
            WHERE o.id = CAST(:oid AS UUID)
              AND o.status = 'published'
            """
        ),
        {"oid": str(offre_id)},
    ).mappings().first()
    if row is None:
        return None
    return dict(row)


def _merge_source_ids(*lists: Any) -> list[UUID]:
    seen: dict[str, None] = {}
    for lst in lists:
        if not isinstance(lst, list):
            continue
        for sid in lst:
            key = str(sid)
            if key not in seen:
                seen[key] = None
    out: list[UUID] = []
    for key in seen:
        try:
            out.append(UUID(key))
        except (ValueError, AttributeError):
            continue
    return out


def _eligible_amount(
    *,
    projet: dict[str, Any],
    offre: dict[str, Any],
    unknown_fields: list[str],
) -> Money:
    p_amt = projet.get("montant_recherche_amount")
    p_cur = projet.get("montant_recherche_currency")
    if p_amt is None or p_cur is None:
        unknown_fields.append("montant_projet")
        plafond = _money_from_jsonb(offre.get("fonds_plafond"))
        if plafond is not None:
            return plafond
        return Money(amount=Decimal("0"), currency=Currency.EUR)

    projet_money = Money(amount=Decimal(str(p_amt)), currency=p_cur)
    plafond = _money_from_jsonb(offre.get("fonds_plafond"))
    if plafond is None:
        return projet_money

    if plafond.currency != projet_money.currency:
        if {plafond.currency, projet_money.currency} <= {Currency.XOF, Currency.EUR}:
            projet_xof = convert_to_xof(projet_money)
            plafond_xof = convert_to_xof(plafond)
            if projet_xof and plafond_xof:
                if projet_xof.amount <= plafond_xof.amount:
                    return projet_money
                return plafond
        unknown_fields.append("fx_rate")
        return projet_money

    if projet_money.amount <= plafond.amount:
        return projet_money
    return plafond


def simulate(
    db: Session,
    *,
    account_id: UUID,
    projet_id: UUID,
    offre_id: UUID,
    hypotheses: SimulationHypotheses | None = None,
) -> SimulationResult:
    """Calcule un SimulationResult pour un couple (projet, offre)."""
    projet = _load_projet(db, account_id=account_id, projet_id=projet_id)
    if projet is None:
        raise ProjetNotFound(f"Projet {projet_id} introuvable.")
    offre = _load_offre_full(db, offre_id=offre_id)
    if offre is None:
        raise OffreNotFound(f"Offre {offre_id} introuvable ou non publiee.")
    return _build_result(projet=projet, offre=offre, hypotheses=hypotheses)


def _build_result(
    *,
    projet: dict[str, Any],
    offre: dict[str, Any],
    hypotheses: SimulationHypotheses | None,
) -> SimulationResult:
    unknown_fields: list[str] = []
    notes: list[str] = []
    hypotheses = hypotheses or SimulationHypotheses()

    instrument = _normalize_instrument(offre.get("fonds_instruments"))
    montant_eligible = _eligible_amount(
        projet=projet, offre=offre, unknown_fields=unknown_fields
    )

    offre_frais = offre.get("offre_frais") or {}
    fonds_frais = offre.get("fonds_frais") or {}
    inter_frais = offre.get("intermediaire_frais") or {}

    marge_pct = (
        extract_pct(inter_frais, "marge_pct", "marge_intermediaire_pct")
        or extract_pct(offre_frais, "marge_intermediaire_pct", "marge_pct")
    )
    if marge_pct is None and offre.get("intermediaire_id") is not None:
        unknown_fields.append("marge_intermediaire")
    marge_money = compute_pct_of(montant_eligible, marge_pct)

    frais_pct = extract_pct(
        offre_frais, "frais_dossier_pct", "frais_dossier"
    ) or extract_pct(fonds_frais, "frais_dossier_pct", "frais_dossier")
    frais_money = compute_pct_of(montant_eligible, frais_pct)
    if frais_money is None:
        frais_fixed = _money_from_jsonb(offre_frais.get("frais_dossier_montant"))
        if frais_fixed is None:
            frais_fixed = _money_from_jsonb(fonds_frais.get("frais_dossier_montant"))
        if frais_fixed is not None:
            frais_money = frais_fixed
        else:
            unknown_fields.append("frais_dossier")

    garantie_pct = (
        hypotheses.garantie_pct
        or extract_pct(offre_frais, "garantie_pct")
        or extract_pct(fonds_frais, "garantie_pct")
    )
    garantie_money = compute_pct_of(montant_eligible, garantie_pct)

    taux_pct = (
        hypotheses.taux_interet_pct
        or extract_pct(offre_frais, "taux_interet_pct", "taux_pct")
        or extract_pct(fonds_frais, "taux_interet_pct", "taux_pct")
    )
    if instrument in ("subvention", "equity"):
        taux_pct = Decimal("0")
    elif taux_pct is None:
        unknown_fields.append("taux_interet_pct")
        notes.append(
            "Donnee non disponible : taux d'interet absent du catalog. "
            "Defaut concessionnel applique."
        )
        taux_pct = _DEFAULT_TAUX.get(instrument, Decimal("0"))

    duree_mois = hypotheses.duree_mois or projet.get("duree_mois")

    if instrument in ("subvention", "equity"):
        interets_money: Money | None = Money(
            amount=Decimal("0.00"), currency=montant_eligible.currency
        )
    elif duree_mois is None:
        unknown_fields.append("duree_mois")
        interets_money = None
    else:
        interets_money = interets_simples(
            montant_eligible, taux_pct, int(duree_mois)
        )

    cout_amount = Decimal("0")
    for component in (marge_money, frais_money, interets_money):
        if component is not None:
            cout_amount += component.amount
    cout_total = Money(
        amount=cout_amount.quantize(Decimal("0.01")),
        currency=montant_eligible.currency,
    )
    if instrument == "subvention":
        cout_total = Money(amount=Decimal("0.00"), currency=montant_eligible.currency)

    if montant_eligible.amount > 0:
        cout_pct = (cout_total.amount / montant_eligible.amount * Decimal(100)).quantize(
            Decimal("0.01")
        )
    else:
        cout_pct = Decimal("0.00")

    equivalent_xof = convert_to_xof(montant_eligible)
    change_risk = montant_eligible.currency not in (Currency.XOF, Currency.EUR)
    if change_risk:
        unknown_fields.append("fx_rate")

    source_ids = _merge_source_ids(
        offre.get("fonds_source_ids"),
        offre.get("intermediaire_source_ids"),
        offre.get("offre_source_ids"),
    )
    unsourced = len(source_ids) == 0

    return SimulationResult(
        projet_id=_to_uuid(projet["id"]),
        offre_id=_to_uuid(offre["offre_id"]),
        instrument=instrument,
        montant_eligible=montant_eligible,
        frais_dossier=frais_money,
        marge_intermediaire=marge_money,
        garantie_exigee=garantie_money,
        interets_cumules=interets_money,
        cout_total=cout_total,
        cout_total_pct=cout_pct,
        duree_mois=int(duree_mois) if duree_mois is not None else None,
        taux_interet_pct=taux_pct,
        devise_emprunt=montant_eligible.currency,
        equivalent_xof=equivalent_xof,
        change_risk=change_risk,
        dilution_warning=instrument == "equity",
        unsourced=unsourced,
        unknown_fields=unknown_fields,
        source_ids=source_ids,
        notes=notes,
    )


def compare(
    db: Session,
    *,
    account_id: UUID,
    projet_id: UUID,
    offre_ids: list[UUID],
    hypotheses: SimulationHypotheses | None = None,
) -> ComparatorResult:
    """Compare 2..5 offres pour un meme projet, tries par cout_total asc."""
    if len(offre_ids) < 2 or len(offre_ids) > 5:
        raise ValueError("offre_ids must have 2..5 elements")
    if len(set(offre_ids)) != len(offre_ids):
        raise ValueError("offre_ids must be unique")
    rows: list[SimulationResult] = []
    for oid in offre_ids:
        rows.append(
            simulate(
                db,
                account_id=account_id,
                projet_id=projet_id,
                offre_id=oid,
                hypotheses=hypotheses,
            )
        )
    rows.sort(key=lambda r: r.cout_total.amount)
    return ComparatorResult(projet_id=projet_id, rows=rows)


# ---------- F51 — Mode pedagogique (preview) ----------

# Defaults pedagogiques pour le mode preview (sans projet/offre).
_PREVIEW_DEFAULT_MONTANT: Money = Money(amount=Decimal("100000"), currency=Currency.EUR)
_PREVIEW_DEFAULT_DUREE_MOIS: int = 60
_PREVIEW_DEFAULT_TAUX_PCT: Decimal = Decimal("4")
_PREVIEW_DEFAULT_PART_SUBV_PCT: Decimal = Decimal("0")

# Facteurs CO2 pedagogiques par type d'investissement (tonnes CO2 evitees / EUR).
# Source : ordre de grandeur ADEME (2024) — chiffres indicatifs MVP.
_PREVIEW_CO2_FACTOR_PER_EUR: dict[str, Decimal] = {
    "renouvelable_solaire": Decimal("1") / Decimal("2000"),
    "renouvelable_eolien": Decimal("1") / Decimal("1500"),
    "efficacite_energetique": Decimal("1") / Decimal("3000"),
    "agriculture_durable": Decimal("1") / Decimal("5000"),
    "mobilite_electrique": Decimal("1") / Decimal("4000"),
    "autre": Decimal("1") / Decimal("6000"),
}

# Part d'economies sur la duree (% du montant initial) pour le mode pedagogique.
_PREVIEW_ECONOMIE_PCT: Decimal = Decimal("30")


def simulate_preview(
    *,
    hypotheses: SimulationHypotheses | None = None,
) -> SimulationResults:
    """Calcule un SimulationResults purement base sur les hypotheses.

    Mode pedagogique F51 : sans projet ni offre, on calcule un amortissement
    lineaire sur la base des inputs utilisateur (montant, duree, type,
    part_subvention). Aucun acces DB.
    """
    h = hypotheses or SimulationHypotheses()
    montant: Money = h.montant or _PREVIEW_DEFAULT_MONTANT
    duree_mois: int = h.duree_mois or _PREVIEW_DEFAULT_DUREE_MOIS
    taux_pct: Decimal = h.taux_interet_pct or _PREVIEW_DEFAULT_TAUX_PCT
    part_subv_pct: Decimal = h.part_subvention_pct or _PREVIEW_DEFAULT_PART_SUBV_PCT
    type_inv: str = h.type_investissement or "autre"

    currency = montant.currency
    cents = Decimal("0.01")

    montant_subvention_amt = (montant.amount * part_subv_pct / Decimal(100)).quantize(cents)
    montant_emprunte_amt = (montant.amount - montant_subvention_amt).quantize(cents)
    montant_emprunte = Money(amount=montant_emprunte_amt, currency=currency)

    interets_total = interets_simples(montant_emprunte, taux_pct, duree_mois)

    # Mensualite lineaire : (principal + interets) / duree.
    total_a_rembourser = montant_emprunte_amt + interets_total.amount
    mensualite_amt = (total_a_rembourser / Decimal(duree_mois)).quantize(cents)
    mensualites: list[MensualiteEntry] = [
        MensualiteEntry(
            mois=m,
            amount=format(mensualite_amt, "f"),
            currency=currency,
        )
        for m in range(1, duree_mois + 1)
    ]

    cout_total = Money(amount=interets_total.amount, currency=currency)

    economie_amt = (montant.amount * _PREVIEW_ECONOMIE_PCT / Decimal(100)).quantize(cents)
    economie_estimee = Money(amount=economie_amt, currency=currency)

    co2_factor = _PREVIEW_CO2_FACTOR_PER_EUR.get(
        type_inv, _PREVIEW_CO2_FACTOR_PER_EUR["autre"]
    )
    montant_xof_or_eur: Decimal
    if currency == Currency.EUR:
        montant_xof_or_eur = montant.amount
    elif currency == Currency.XOF:
        # Convertit en EUR pour appliquer le facteur (CO2 calibre en EUR).
        montant_xof_or_eur = (montant.amount / Decimal("655.957")).quantize(cents)
    else:
        montant_xof_or_eur = montant.amount  # autres devises : approximation 1:1
    co2_evite_t = (montant_xof_or_eur * co2_factor).quantize(Decimal("0.01"))

    total_finance = montant_emprunte_amt + interets_total.amount + montant_subvention_amt
    if total_finance > 0:
        principal_pct = float(
            (montant_emprunte_amt / total_finance * Decimal(100)).quantize(cents)
        )
        interets_pct = float(
            (interets_total.amount / total_finance * Decimal(100)).quantize(cents)
        )
        subvention_pct = float(
            (montant_subvention_amt / total_finance * Decimal(100)).quantize(cents)
        )
    else:
        principal_pct = interets_pct = subvention_pct = 0.0

    return SimulationResults(
        mensualites=mensualites,
        cout_total=cout_total,
        economie_estimee=economie_estimee,
        co2_evite_t=format(co2_evite_t, "f"),
        decomposition_pct=DecompositionPct(
            principal=principal_pct,
            interets=interets_pct,
            subvention=subvention_pct,
        ),
        formula_refs=[FormulaRef(formula_id="preview.linear", version="1.0")],
        computed_at=datetime.now(UTC).isoformat(),
    )


# ---------- F51 — Save & history ----------


import json as _json  # noqa: E402

_HISTORY_CAP = 50


class QuotaExceededError(Exception):
    """Cap 50 simulations actives par account."""


class SimulationNotFound(Exception):
    """Simulation sauvegardée introuvable."""


def save_simulation(
    db: Session,
    *,
    account_id: UUID,
    user_id: UUID | None,
    label: str,
    projet_id: UUID | None,
    offre_id: UUID | None,
    hypotheses: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    count_row = db.execute(
        text(
            "SELECT COUNT(*) AS n FROM simulation_savee "
            "WHERE account_id = CAST(:aid AS UUID) AND deleted_at IS NULL"
        ),
        {"aid": str(account_id)},
    ).mappings().first()
    if count_row and int(count_row["n"]) >= _HISTORY_CAP:
        raise QuotaExceededError("quota_exceeded")

    row = db.execute(
        text(
            """
            INSERT INTO simulation_savee
                (account_id, user_id, label, projet_id, offre_id,
                 hypotheses_json, results_json)
            VALUES
                (CAST(:aid AS UUID), CAST(:uid AS UUID), :lbl,
                 CAST(:pid AS UUID), CAST(:oid AS UUID),
                 CAST(:hyp AS JSONB), CAST(:res AS JSONB))
            RETURNING id, label, created_at
            """
        ),
        {
            "aid": str(account_id),
            "uid": str(user_id) if user_id else None,
            "lbl": label,
            "pid": str(projet_id) if projet_id else None,
            "oid": str(offre_id) if offre_id else None,
            "hyp": _json.dumps(hypotheses, default=str),
            "res": _json.dumps(results, default=str),
        },
    ).mappings().first()
    assert row is not None

    sim_id = row["id"]
    try:
        from app.audit.helper import record_audit
        from app.audit.schemas import SourceOfChange

        record_audit(
            db,
            entity_type="simulation_savee",
            entity_id=sim_id,
            field="id",
            old=None,
            new=str(sim_id),
            source_of_change=SourceOfChange.MANUAL,
            user_id=str(user_id) if user_id else None,
            account_id=str(account_id),
        )
    except Exception:
        pass
    return {
        "id": sim_id,
        "label": row["label"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
    }


def list_saved(
    db: Session, *, account_id: UUID, limit: int = 20
) -> list[dict[str, Any]]:
    capped = max(1, min(50, int(limit)))
    rows = db.execute(
        text(
            """
            SELECT id, label, projet_id, offre_id, hypotheses_json,
                   results_json, created_at
            FROM simulation_savee
            WHERE account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"aid": str(account_id), "lim": capped},
    ).mappings().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        results = r["results_json"] or {}
        summary = {
            "cout_total": results.get("cout_total") if isinstance(results, dict) else None,
            "co2_evite_t": results.get("co2_evite_t") if isinstance(results, dict) else None,
        }
        out.append(
            {
                "id": r["id"],
                "label": r["label"],
                "projet_id": r["projet_id"],
                "offre_id": r["offre_id"],
                "hypotheses": r["hypotheses_json"] or {},
                "results_summary": summary,
                "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            }
        )
    return out


def get_saved(
    db: Session, *, account_id: UUID, sim_id: UUID
) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, label, projet_id, offre_id, hypotheses_json,
                   results_json, created_at
            FROM simulation_savee
            WHERE id = CAST(:sid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            """
        ),
        {"sid": str(sim_id), "aid": str(account_id)},
    ).mappings().first()
    if row is None:
        raise SimulationNotFound(str(sim_id))
    return {
        "id": row["id"],
        "label": row["label"],
        "projet_id": row["projet_id"],
        "offre_id": row["offre_id"],
        "hypotheses": row["hypotheses_json"] or {},
        "results": row["results_json"] or {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
    }


def soft_delete_saved(
    db: Session, *, account_id: UUID, user_id: UUID | None, sim_id: UUID
) -> None:
    res = db.execute(
        text(
            """
            UPDATE simulation_savee
            SET deleted_at = now()
            WHERE id = CAST(:sid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            """
        ),
        {"sid": str(sim_id), "aid": str(account_id)},
    )
    if res.rowcount == 0:
        raise SimulationNotFound(str(sim_id))
    try:
        from app.audit.helper import record_audit
        from app.audit.schemas import SourceOfChange

        record_audit(
            db,
            entity_type="simulation_savee",
            entity_id=sim_id,
            field="deleted_at",
            old=None,
            new="now()",
            source_of_change=SourceOfChange.MANUAL,
            user_id=str(user_id) if user_id else None,
            account_id=str(account_id),
        )
    except Exception:
        pass
