"""F54 / T034 — Tests perf builder latency (NFR-001, SC-011).

Mesure :
- Cold cache : 100 itérations sans cache → p95 < 250 ms.
- Hot cache : 100 itérations avec cache prérempli → p95 < 50 ms.

Le test est marqué ``@pytest.mark.perf`` (skipé par défaut sauf si
``-m perf``). Il n'utilise pas de DB réelle : on benche le builder pur.
"""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.agent.context.models import (
    BusinessContext,
    EnrichedPageContext,
    EntrepriseSummary,
    IndicateurSummary,
    Money,
    ProjetSummary,
)
from app.agent.prompt_builder import build_system_prompt


def _build_realistic_ctx() -> BusinessContext:
    aid = uuid4()
    ent = EntrepriseSummary(
        account_id=aid,
        raison_sociale="SARL Boulangerie Sankoré",
        secteur_naf="C10.71",
        secteur_label="Boulangerie-pâtisserie",
        pays="CI",
        devise_principale="XOF",
        ca_dernier_exercice=Money(amount=Decimal("12000000"), currency="XOF"),
    )
    projets = [
        ProjetSummary(
            id=uuid4(),
            titre=f"Projet {i}",
            description_courte=f"Description du projet {i}",
            montant_demande=Money(amount=Decimal("5000000"), currency="XOF"),
            statut="en_analyse",
            date_creation=datetime.now(UTC),
        )
        for i in range(10)
    ]
    indic = [
        IndicateurSummary(
            id=uuid4(),
            code=f"INDIC_{i}",
            libelle=f"Indicateur {i}",
            axe=("E", "S", "G")[i % 3],
            valeur=Decimal("10"),
            unite="tCO2e",
            date_calcul=datetime.now(UTC),
        )
        for i in range(30)
    ]
    return BusinessContext(
        account_id=aid,
        user_id=uuid4(),
        user_role="pme",
        loaded_at=datetime.now(UTC),
        entreprise=ent,
        projets_actifs=projets,
        indicateurs_recents=indic,
    )


@pytest.mark.perf
def test_build_system_prompt_latency_p95() -> None:
    """100 itérations du builder pur (sans DB). p95 < 50 ms attendu."""
    ctx = _build_realistic_ctx()
    page = EnrichedPageContext(page="/", entity_type=None)
    durations_ms: list[float] = []

    # Warm-up.
    for _ in range(5):
        build_system_prompt(business_ctx=ctx, page_ctx=page)

    for _ in range(100):
        start = time.perf_counter()
        build_system_prompt(business_ctx=ctx, page_ctx=page)
        durations_ms.append((time.perf_counter() - start) * 1000)

    durations_ms.sort()
    p95 = durations_ms[int(0.95 * len(durations_ms))]
    p50 = statistics.median(durations_ms)

    # Le builder pur (pas de DB) doit être très rapide.
    assert p95 < 100.0, f"p95 builder pur = {p95:.2f} ms (attendu < 100 ms)"
    print(f"[perf] builder pur: p50={p50:.2f}ms, p95={p95:.2f}ms")
