"""F32 — Tests unitaires des schémas Pydantic du dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.dashboard.schemas import (
    ActionStepEntry,
    AttestationBlock,
    AttestationItem,
    CandidatureBlock,
    CandidatureItem,
    CarbonEntry,
    CreditScoreEntry,
    DashboardSummaryOut,
    DataExportOut,
    RapportBlock,
    RapportItem,
    ScoreEntry,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_score_entry_minimal() -> None:
    e = ScoreEntry(
        referentiel_code="ESG_MEFALI",
        referentiel_version=1,
        score_global=Decimal("75.0"),
        coverage_ratio=Decimal("0.85"),
        computed_at=_now(),
    )
    assert e.referentiel_code == "ESG_MEFALI"


def test_score_entry_nullable_fields() -> None:
    e = ScoreEntry(
        referentiel_code="X",
        referentiel_version=2,
        score_global=None,
        coverage_ratio=None,
        computed_at=_now(),
    )
    assert e.score_global is None and e.coverage_ratio is None


def test_carbon_entry() -> None:
    c = CarbonEntry(year=2025, total_tco2e=Decimal("12.5"), computed_at=_now())
    assert c.year == 2025


def test_credit_score_entry() -> None:
    s = CreditScoreEntry(
        solvabilite=70,
        impact_vert=80,
        combine=75,
        methodologie_version=1,
        coherence_warning=False,
        computed_at=_now(),
    )
    assert s.combine == 75


def test_candidature_block_empty() -> None:
    block = CandidatureBlock(counters_by_statut={}, total=0, recent=[])
    assert block.total == 0
    assert block.recent == []


def test_candidature_block_with_items() -> None:
    item = CandidatureItem(
        id=uuid.uuid4(),
        projet_id=uuid.uuid4(),
        offre_id=uuid.uuid4(),
        statut="brouillon",
        soumission_at=None,
        created_at=_now(),
    )
    block = CandidatureBlock(
        counters_by_statut={"brouillon": 1}, total=1, recent=[item]
    )
    assert block.total == 1
    assert block.recent[0].statut == "brouillon"


def test_rapport_block() -> None:
    item = RapportItem(
        id=uuid.uuid4(),
        entity_type="entreprise",
        entity_id=uuid.uuid4(),
        referentiels=["ESG_MEFALI"],
        language="fr",
        generated_at=_now(),
    )
    block = RapportBlock(total=1, recent=[item])
    assert block.recent[0].language == "fr"


def test_attestation_block() -> None:
    item = AttestationItem(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        generated_at=_now(),
        valid_until=_now(),
        revoked_at=None,
    )
    block = AttestationBlock(active=1, revoked=0, recent=[item])
    assert block.active == 1


def test_action_step_entry() -> None:
    s = ActionStepEntry(
        id=uuid.uuid4(),
        title="Realiser bilan carbone Scope 1",
        category="carbone",
        priority="haute",
        status="todo",
        horizon_at=date(2026, 12, 31),
    )
    assert s.priority == "haute"


def test_dashboard_summary_full() -> None:
    aid = uuid.uuid4()
    out = DashboardSummaryOut(
        account_id=aid,
        scores=[],
        carbon=[],
        credit_score=None,
        candidatures=CandidatureBlock(counters_by_statut={}, total=0, recent=[]),
        rapports=RapportBlock(total=0, recent=[]),
        attestations=AttestationBlock(active=0, revoked=0, recent=[]),
        next_actions=[],
        generated_at=_now(),
    )
    assert out.account_id == aid


def test_data_export_full() -> None:
    out = DataExportOut(
        account={"id": "x", "type": "pme"},
        entreprise=None,
        projets=[],
        candidatures=[],
        scores=[],
        carbon=[],
        credit_score=None,
        rapports=[],
        attestations=[],
        consents=[],
        action_plan=[],
        exported_at=_now(),
    )
    assert out.account["id"] == "x"
    assert out.entreprise is None
