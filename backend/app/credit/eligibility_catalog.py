"""F48 - Catalogue declaratif des dispositifs d'eligibilite credit vert.

Catalogue versionne, pure-data, evalue a la volee par
``credit/service.evaluate_eligibility``. Aucune table SQL : la verite reside
dans ce module Python ; un changement de regles -> bump version + nouvelle
entree (l'ancienne reste consultable via l'audit applicatif post-MVP).

Chaque dispositif expose un ``source_id`` pointant vers une ``Source`` au
statut ``verified`` (P1 Sourcage).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final


@dataclass(frozen=True)
class EligibilityRule:
    code: str
    label: str
    description: str
    min_combine_score: int | None
    min_subscore_engagement_esg: int | None
    min_subscore_solidite_financiere: int | None
    excluded_sectors: tuple[str, ...]  # codes secteurs exclus
    required_min_size: str | None  # "tpe" | "pme" | "eti"
    source_id: uuid.UUID
    version: int
    valid_from: datetime
    valid_to: datetime | None
    matching_offer_query: str


# UUIDs deterministes pour les sources (a remplacer par les UUID reels une
# fois le seed `seed_credit_eligibility_sources.py` execute en production).
_SRC_BOAD = uuid.UUID("48000000-0000-0000-0000-000000000001")
_SRC_SUNREF = uuid.UUID("48000000-0000-0000-0000-000000000002")
_SRC_ECOBANK = uuid.UUID("48000000-0000-0000-0000-000000000003")

_VALID_FROM_INITIAL = datetime(2026, 1, 1, tzinfo=UTC)


CATALOG: Final[tuple[EligibilityRule, ...]] = (
    EligibilityRule(
        code="boad_vert",
        label="BOAD-vert",
        description=(
            "Ligne de credit verte de la Banque Ouest-Africaine de Developpement "
            "pour les PME engagees dans une demarche environnementale."
        ),
        min_combine_score=60,
        min_subscore_engagement_esg=50,
        min_subscore_solidite_financiere=None,
        excluded_sectors=(),
        required_min_size="pme",
        source_id=_SRC_BOAD,
        version=1,
        valid_from=_VALID_FROM_INITIAL,
        valid_to=None,
        matching_offer_query="instrument=ligne_credit&dispositif=boad_vert",
    ),
    EligibilityRule(
        code="sunref",
        label="SUNREF",
        description=(
            "Programme SUNREF (AFD) finançant les investissements verts "
            "des PME ouest-africaines."
        ),
        min_combine_score=55,
        min_subscore_engagement_esg=60,
        min_subscore_solidite_financiere=None,
        excluded_sectors=("armement", "tabac"),
        required_min_size="pme",
        source_id=_SRC_SUNREF,
        version=1,
        valid_from=_VALID_FROM_INITIAL,
        valid_to=None,
        matching_offer_query="instrument=ligne_credit&dispositif=sunref",
    ),
    EligibilityRule(
        code="ecobank_green_lending",
        label="Ecobank Green Lending",
        description=(
            "Programme de prets verts Ecobank pour PME, axe sur l'efficacite "
            "energetique et les energies renouvelables."
        ),
        min_combine_score=70,
        min_subscore_engagement_esg=None,
        min_subscore_solidite_financiere=75,
        excluded_sectors=(),
        required_min_size="pme",
        source_id=_SRC_ECOBANK,
        version=1,
        valid_from=_VALID_FROM_INITIAL,
        valid_to=None,
        matching_offer_query="instrument=pret&dispositif=ecobank_green_lending",
    ),
)


def active_catalog(now: datetime | None = None) -> tuple[EligibilityRule, ...]:
    """Retourne les regles dont la fenetre de validite couvre ``now``."""
    ref = now or datetime.now(UTC)
    return tuple(
        r
        for r in CATALOG
        if r.valid_from <= ref and (r.valid_to is None or ref < r.valid_to)
    )
