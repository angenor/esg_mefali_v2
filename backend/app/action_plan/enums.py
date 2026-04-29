"""F31 — Enums du module Plan d'Action.

Ces enums Python miroir les types Postgres (cf. migration 0021) et sont
utilisés par les schemas Pydantic ainsi que par le générateur déterministe.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Category(StrEnum):
    ESG = "esg"
    CARBONE = "carbone"
    CREDIT = "credit"
    CANDIDATURE = "candidature"


class Priority(StrEnum):
    HAUTE = "haute"
    MOYENNE = "moyenne"
    BASSE = "basse"


class StepStatus(StrEnum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    POSTPONED = "postponed"


class Horizon(IntEnum):
    SIX = 6
    TWELVE = 12
    TWENTYFOUR = 24


VALID_HORIZONS: frozenset[int] = frozenset({h.value for h in Horizon})
"""Valeurs autorisées pour le query param ``horizon``."""
