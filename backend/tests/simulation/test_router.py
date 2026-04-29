"""F27 - Tests des schemas de requetes router (validation Pydantic + smoke import)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.simulation.schemas import (
    ComparatorRequest,
    SimulationHypotheses,
    SimulationRequest,
)


def test_simulation_request_valid():
    req = SimulationRequest(projet_id=uuid4(), offre_id=uuid4())
    assert req.hypotheses is None


def test_simulation_request_with_hypotheses():
    req = SimulationRequest(
        projet_id=uuid4(),
        offre_id=uuid4(),
        hypotheses=SimulationHypotheses(taux_interet_pct=Decimal("3.5")),
    )
    assert req.hypotheses is not None
    assert req.hypotheses.taux_interet_pct == Decimal("3.5")


def test_simulation_request_extra_forbidden():
    with pytest.raises(ValidationError):
        SimulationRequest(
            projet_id=uuid4(),
            offre_id=uuid4(),
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_comparator_request_min_2():
    with pytest.raises(ValidationError):
        ComparatorRequest(projet_id=uuid4(), offre_ids=[uuid4()])


def test_comparator_request_max_5():
    with pytest.raises(ValidationError):
        ComparatorRequest(projet_id=uuid4(), offre_ids=[uuid4() for _ in range(6)])


def test_comparator_request_valid_3_offres():
    req = ComparatorRequest(
        projet_id=uuid4(),
        offre_ids=[uuid4(), uuid4(), uuid4()],
    )
    assert len(req.offre_ids) == 3


def test_hypotheses_taux_negatif_rejected():
    with pytest.raises(ValidationError):
        SimulationHypotheses(taux_interet_pct=Decimal("-1"))


def test_hypotheses_duree_zero_rejected():
    with pytest.raises(ValidationError):
        SimulationHypotheses(duree_mois=0)


def test_hypotheses_immutable():
    h = SimulationHypotheses(taux_interet_pct=Decimal("4"))
    with pytest.raises(ValidationError):
        h.taux_interet_pct = Decimal("5")  # type: ignore[misc]


def test_router_module_imports():
    """Smoke test : router module se charge sans erreur."""
    from app.simulation.router import router

    assert router is not None
    routes = {route.path for route in router.routes}  # type: ignore[attr-defined]
    assert "/me/simulations" in routes
    assert "/me/simulations/comparator" in routes
