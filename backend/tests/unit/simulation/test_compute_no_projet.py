"""F51 — Tests du mode pedagogique simulate_preview (sans projet_id ni offre_id).

Verifie que :
1. SimulationRequest accepte projet_id=None et offre_id=None (regression du bug 422 F51).
2. simulate_preview retourne un SimulationResults valide avec defaults.
3. Le calcul reflete les inputs utilisateur (montant, duree, part_subvention, taux).
4. Le shape de reponse est conforme au contrat F51 (mensualites, cout_total, ...).
"""

from __future__ import annotations

from decimal import Decimal

from app.core.currencies import Currency
from app.schemas.money import Money
from app.simulation.schemas import (
    SimulationHypotheses,
    SimulationRequest,
    SimulationResults,
)
from app.simulation.service import simulate_preview


def test_simulation_request_accepts_null_projet_and_offre():
    """Bug 422 F51 : projet_id et offre_id doivent etre Optional."""
    req = SimulationRequest()
    assert req.projet_id is None
    assert req.offre_id is None
    assert req.hypotheses is None


def test_simulation_request_accepts_null_with_hypotheses():
    req = SimulationRequest(
        hypotheses=SimulationHypotheses(
            montant=Money(amount=Decimal("100000"), currency=Currency.EUR),
            duree_mois=60,
            type_investissement="renouvelable_solaire",
            part_subvention_pct=Decimal("0"),
        ),
    )
    assert req.projet_id is None
    assert req.offre_id is None
    assert req.hypotheses is not None
    assert req.hypotheses.montant is not None
    assert req.hypotheses.montant.amount == Decimal("100000")


def test_simulate_preview_with_defaults_returns_valid_results():
    """Sans hypotheses : defaults pedagogiques (100k EUR, 60 mois, 4%, 0% subv)."""
    out = simulate_preview()
    assert isinstance(out, SimulationResults)
    assert len(out.mensualites) == 60
    assert out.mensualites[0].mois == 1
    assert out.mensualites[-1].mois == 60
    assert out.cout_total.currency == Currency.EUR
    assert out.cout_total.amount > Decimal("0")
    assert out.economie_estimee.currency == Currency.EUR
    assert out.economie_estimee.amount > Decimal("0")
    assert Decimal(out.co2_evite_t) > Decimal("0")
    decomp = out.decomposition_pct
    total_pct = decomp.principal + decomp.interets + decomp.subvention
    assert abs(total_pct - 100.0) < 1.0  # tolerance arrondi
    assert len(out.formula_refs) >= 1
    assert out.computed_at is not None


def test_simulate_preview_respects_montant_and_duree():
    h = SimulationHypotheses(
        montant=Money(amount=Decimal("200000"), currency=Currency.EUR),
        duree_mois=120,
        taux_interet_pct=Decimal("3"),
        part_subvention_pct=Decimal("0"),
    )
    out = simulate_preview(hypotheses=h)
    assert len(out.mensualites) == 120
    # interets simples : 200000 * 3% * 10 ans = 60000
    assert out.cout_total.amount == Decimal("60000.00")
    assert out.cout_total.currency == Currency.EUR


def test_simulate_preview_subvention_reduces_emprunt():
    """Avec 50% de subvention, le montant emprunte est moitie -> interets moitie."""
    h_no_subv = SimulationHypotheses(
        montant=Money(amount=Decimal("100000"), currency=Currency.EUR),
        duree_mois=60,
        taux_interet_pct=Decimal("4"),
        part_subvention_pct=Decimal("0"),
    )
    h_with_subv = SimulationHypotheses(
        montant=Money(amount=Decimal("100000"), currency=Currency.EUR),
        duree_mois=60,
        taux_interet_pct=Decimal("4"),
        part_subvention_pct=Decimal("50"),
    )
    out_no = simulate_preview(hypotheses=h_no_subv)
    out_yes = simulate_preview(hypotheses=h_with_subv)
    assert out_yes.cout_total.amount < out_no.cout_total.amount
    # Avec subvention 50% : decomposition_pct.subvention > 0
    assert out_yes.decomposition_pct.subvention > 0


def test_simulate_preview_co2_factor_varies_by_type():
    """Le facteur CO2 doit varier selon type_investissement (eolien > solaire > autre)."""
    common = {
        "montant": Money(amount=Decimal("100000"), currency=Currency.EUR),
        "duree_mois": 60,
        "taux_interet_pct": Decimal("4"),
        "part_subvention_pct": Decimal("0"),
    }
    out_eolien = simulate_preview(
        hypotheses=SimulationHypotheses(type_investissement="renouvelable_eolien", **common)
    )
    out_autre = simulate_preview(
        hypotheses=SimulationHypotheses(type_investissement="autre", **common)
    )
    assert Decimal(out_eolien.co2_evite_t) > Decimal(out_autre.co2_evite_t)


def test_simulate_preview_xof_currency():
    """Mode XOF : la reponse garde la devise et calcule un CO2 evite via conversion EUR."""
    h = SimulationHypotheses(
        montant=Money(amount=Decimal("65595700"), currency=Currency.XOF),  # ~100k EUR
        duree_mois=60,
        taux_interet_pct=Decimal("4"),
        part_subvention_pct=Decimal("0"),
        type_investissement="renouvelable_solaire",
    )
    out = simulate_preview(hypotheses=h)
    assert out.cout_total.currency == Currency.XOF
    assert out.economie_estimee.currency == Currency.XOF
    # Equivalent EUR ~100k -> facteur solaire 1/2000 -> ~50t CO2
    co2 = Decimal(out.co2_evite_t)
    assert Decimal("40") <= co2 <= Decimal("60")


def test_simulate_preview_response_shape_matches_contract():
    """Le shape de reponse F51 doit avoir les champs attendus par le frontend."""
    out = simulate_preview()
    payload = out.model_dump(mode="json")
    # Champs racine du contrat simulateur_api_extensions.md § 1
    assert "mensualites" in payload
    assert "cout_total" in payload
    assert "economie_estimee" in payload
    assert "co2_evite_t" in payload
    assert "decomposition_pct" in payload
    assert "formula_refs" in payload
    # Money serialise en {amount: str, currency: str}
    assert payload["cout_total"]["amount"] is not None
    assert payload["cout_total"]["currency"] in {"EUR", "XOF", "USD", "GHS", "NGN", "MAD", "GBP"}
    # decomposition_pct : { principal, interets, subvention }
    assert "principal" in payload["decomposition_pct"]
    assert "interets" in payload["decomposition_pct"]
    assert "subvention" in payload["decomposition_pct"]
    # mensualites : list of {mois, amount, currency}
    if payload["mensualites"]:
        m0 = payload["mensualites"][0]
        assert "mois" in m0
        assert "amount" in m0
        assert "currency" in m0
