"""F54 / T035, T052 — Tests d'isolation cross-tenant (NFR-003, SC-003, US8).

Vérifie :
1. La clé du cache LRU+TTL est strictement par account_id (pas de fuite
   A → B même en cache hot).
2. Construire un prompt pour A puis pour B : aucun field de B n'apparaît
   dans le prompt de A et inversement.

Test sans DB (mocks loader) — l'isolation est testée au niveau du builder
+ cache.
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


def _ctx_for(*, name: str, projet_titre: str, account_id=None) -> BusinessContext:
    aid = account_id or uuid4()
    ent = EntrepriseSummary(
        account_id=aid,
        raison_sociale=name,
        pays="CI",
        devise_principale="XOF",
        ca_dernier_exercice=Money(amount=Decimal("12000000"), currency="XOF"),
    )
    proj = ProjetSummary(
        id=uuid4(),
        titre=projet_titre,
        statut="en_analyse",
        date_creation=datetime.now(UTC),
    )
    return BusinessContext(
        account_id=aid,
        user_id=uuid4(),
        user_role="pme",
        loaded_at=datetime.now(UTC),
        entreprise=ent,
        projets_actifs=[proj],
    )


@pytest.mark.integration
class TestCacheCrossTenantIsolation:
    """NFR-003 : la clé inclut account_id, jamais de collision."""

    def test_two_accounts_separate_cache_entries(self) -> None:
        cache = get_business_context_cache()

        ctx_a = _ctx_for(name="Alpha", projet_titre="ProjAlpha")
        ctx_b = _ctx_for(name="Beta", projet_titre="ProjBeta")

        cache.set(ctx_a.account_id, SCHEMA_VERSION, ctx_a)
        cache.set(ctx_b.account_id, SCHEMA_VERSION, ctx_b)

        # Lecture A → ctx_a.
        cached_a = cache.get(ctx_a.account_id, SCHEMA_VERSION)
        assert cached_a is not None
        assert cached_a.entreprise.raison_sociale == "Alpha"
        assert cached_a.projets_actifs[0].titre == "ProjAlpha"

        # Lecture B → ctx_b.
        cached_b = cache.get(ctx_b.account_id, SCHEMA_VERSION)
        assert cached_b is not None
        assert cached_b.entreprise.raison_sociale == "Beta"
        assert cached_b.projets_actifs[0].titre == "ProjBeta"

        # Aucune fuite.
        assert cached_a.entreprise.account_id != cached_b.entreprise.account_id


@pytest.mark.integration
class TestPromptCrossTenantIsolation:
    """SC-003 : le prompt construit pour A ne contient AUCUN field de B."""

    def test_prompt_a_does_not_contain_b_data(self) -> None:
        ctx_a = _ctx_for(name="Compagnie Alpha", projet_titre="Solaire Alpha")
        ctx_b = _ctx_for(name="Compagnie Beta", projet_titre="Eolien Beta")

        page = EnrichedPageContext(page="/", entity_type=None)

        prompt_a, _ = build_system_prompt(business_ctx=ctx_a, page_ctx=page)
        prompt_b, _ = build_system_prompt(business_ctx=ctx_b, page_ctx=page)

        # Prompt A : que des données A.
        assert "Compagnie Alpha" in prompt_a
        assert "Solaire Alpha" in prompt_a
        assert "Compagnie Beta" not in prompt_a
        assert "Eolien Beta" not in prompt_a

        # Prompt B : que des données B.
        assert "Compagnie Beta" in prompt_b
        assert "Eolien Beta" in prompt_b
        assert "Compagnie Alpha" not in prompt_b
        assert "Solaire Alpha" not in prompt_b


@pytest.mark.integration
class TestPromptHashChangesPerTenant:
    """Le hash SHA-256 du prompt doit différer entre 2 tenants distincts."""

    def test_different_account_different_hash(self) -> None:
        from app.agent.context.hashing import compute_prompt_hash

        ctx_a = _ctx_for(name="Alpha", projet_titre="P_A")
        ctx_b = _ctx_for(name="Beta", projet_titre="P_B")
        page = EnrichedPageContext(page="/", entity_type=None)

        prompt_a, _ = build_system_prompt(business_ctx=ctx_a, page_ctx=page)
        prompt_b, _ = build_system_prompt(business_ctx=ctx_b, page_ctx=page)

        h_a = compute_prompt_hash(prompt_a)
        h_b = compute_prompt_hash(prompt_b)
        assert h_a != h_b
