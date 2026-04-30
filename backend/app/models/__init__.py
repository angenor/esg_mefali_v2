"""F02 — Modèles SQLAlchemy ORM (déclaratifs).

Ces modèles sont volontairement minimaux : ils mappent uniquement les colonnes
nécessaires à la logique d'auth. Le reste des tables F01 reste manipulé en SQL
brut via Alembic.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy partagée."""


from app.models.account import Account  # noqa: E402,F401
from app.models.account_user import AccountUser  # noqa: E402,F401
from app.models.action_plan import ActionPlan  # noqa: E402,F401
from app.models.action_step import ActionStep  # noqa: E402,F401
from app.models.attestation import Attestation  # noqa: E402,F401
from app.models.carbon_footprint import CarbonFootprint  # noqa: E402,F401
from app.models.credit_data import CreditData  # noqa: E402,F401
from app.models.credit_score import CreditScore  # noqa: E402,F401
from app.models.field_mapping_intermediaire import (  # noqa: E402,F401
    FieldMappingIntermediaire,
)
from app.models.notification import Notification  # noqa: E402,F401
from app.models.password_reset_token import PasswordResetToken  # noqa: E402,F401
from app.models.refresh_token import RefreshToken  # noqa: E402,F401
from app.models.skill import Skill, SkillSource  # noqa: E402,F401
from app.models.source import Source  # noqa: E402,F401
from app.models.unsourced_claim_log import UnsourcedClaimLog  # noqa: E402,F401
from app.models.url_pattern import UrlPattern  # noqa: E402,F401

__all__ = [
    "Account",
    "AccountUser",
    "ActionPlan",
    "ActionStep",
    "Attestation",
    "Base",
    "CarbonFootprint",
    "CreditData",
    "CreditScore",
    "FieldMappingIntermediaire",
    "Notification",
    "PasswordResetToken",
    "RefreshToken",
    "Skill",
    "SkillSource",
    "Source",
    "UnsourcedClaimLog",
    "UrlPattern",
]
