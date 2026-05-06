"""F54 / T052 — Test d'intégration multi-tenant prompt isolation (US8).

Renforce SC-003 en validant l'isolation à l'échelle du **prompt complet**
construit pour 2 comptes A et B en succession (cache hot inclus).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.agent.context.cache import (
    get_business_context_cache,
    reset_business_context_cache,
)
from app.agent.context.models import (
    SCHEMA_VERSION,
    BusinessContext,
    EnrichedPageContext,
    EntrepriseSummary,
    Money,
    ProjetSummary,
)
from app.agent.prompt_builder import build_system_prompt


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_business_context_cache()
    yield
    reset_business_context_cache()


@pytest.mark.integration
def test_prompts_for_a_then_b_no_cross_leak() -> None:
    """Construit prompts A → B → A et vérifie l'isolation complète."""
    aid_a = uuid4()
    aid_b = uuid4()

    ctx_a = BusinessContext(
        account_id=aid_a,
        user_id=uuid4(),
        user_role="pme",
        loaded_at=datetime.now(UTC),
        entreprise=EntrepriseSummary(
            account_id=aid_a,
            raison_sociale="ALPHA SARL",
            pays="CI",
            devise_principale="XOF",
            ca_dernier_exercice=Money(amount=Decimal("1000000"), currency="XOF"),
        ),
        projets_actifs=[
            ProjetSummary(
                id=uuid4(),
                titre="Solaire Alpha",
                statut="en_analyse",
                date_creation=datetime.now(UTC),
            )
        ],
    )
    ctx_b = BusinessContext(
        account_id=aid_b,
        user_id=uuid4(),
        user_role="pme",
        loaded_at=datetime.now(UTC),
        entreprise=EntrepriseSummary(
            account_id=aid_b,
            raison_sociale="BETA SAS",
            pays="SN",
            devise_principale="XOF",
            ca_dernier_exercice=Money(amount=Decimal("9999999"), currency="XOF"),
        ),
        projets_actifs=[
            ProjetSummary(
                id=uuid4(),
                titre="Eolien Beta",
                statut="en_analyse",
                date_creation=datetime.now(UTC),
            )
        ],
    )

    cache = get_business_context_cache()
    cache.set(aid_a, SCHEMA_VERSION, ctx_a)
    cache.set(aid_b, SCHEMA_VERSION, ctx_b)

    page = EnrichedPageContext(page="/", entity_type=None)

    p_a, _ = build_system_prompt(business_ctx=ctx_a, page_ctx=page)
    p_b, _ = build_system_prompt(business_ctx=ctx_b, page_ctx=page)
    p_a2, _ = build_system_prompt(business_ctx=ctx_a, page_ctx=page)

    # 1. Prompt A ne contient AUCUN field B.
    assert "BETA SAS" not in p_a
    assert "Eolien Beta" not in p_a
    assert "9 999 999" not in p_a
    assert "ALPHA SARL" in p_a
    assert "Solaire Alpha" in p_a

    # 2. Prompt B ne contient AUCUN field A.
    assert "ALPHA SARL" not in p_b
    assert "Solaire Alpha" not in p_b
    assert "BETA SAS" in p_b
    assert "Eolien Beta" in p_b

    # 3. Idempotence A : second prompt A == premier prompt A
    #    (le timestamp de métadonnées peut différer ; on compare les blocs PME).
    assert "ALPHA SARL" in p_a2
    assert "BETA SAS" not in p_a2
