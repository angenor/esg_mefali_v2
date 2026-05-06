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
from app.models.account_deletion_request import (  # noqa: E402,F401
    AccountDeletionRequest,
)
from app.models.account_user import AccountUser  # noqa: E402,F401
from app.models.action_plan import ActionPlan  # noqa: E402,F401
from app.models.action_step import ActionStep  # noqa: E402,F401
from app.models.agent_tool_status import AgentToolStatus  # noqa: E402,F401
from app.models.attestation import Attestation  # noqa: E402,F401
from app.models.carbon_footprint import CarbonFootprint  # noqa: E402,F401
from app.models.credit_data import CreditData  # noqa: E402,F401
from app.models.credit_score import CreditScore  # noqa: E402,F401
from app.models.export_artifact import ExportArtifact  # noqa: E402,F401
from app.models.extension_ping import ExtensionPing  # noqa: E402,F401
from app.models.field_mapping_intermediaire import (  # noqa: E402,F401
    FieldMappingIntermediaire,
)
from app.models.indicateur import Indicateur  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.notification_preference import (  # noqa: E402,F401
    NotificationPreference,
)
from app.models.password_reset_token import PasswordResetToken  # noqa: E402,F401
from app.models.refresh_token import RefreshToken  # noqa: E402,F401
from app.models.skill import Skill, SkillSource  # noqa: E402,F401
from app.models.source import Source  # noqa: E402,F401
from app.models.unsourced_claim_log import UnsourcedClaimLog  # noqa: E402,F401
from app.models.unsourced_flag import UnsourcedFlag  # noqa: E402,F401
from app.models.url_pattern import UrlPattern  # noqa: E402,F401
from app.models.user_preferences import UserPreferences  # noqa: E402,F401

__all__ = [
    "Account",
    "AccountDeletionRequest",
    "AccountUser",
    "ActionPlan",
    "ActionStep",
    "AgentToolStatus",
    "Attestation",
    "Base",
    "CarbonFootprint",
    "CreditData",
    "CreditScore",
    "ExportArtifact",
    "ExtensionPing",
    "FieldMappingIntermediaire",
    "Notification",
    "NotificationPreference",
    "PasswordResetToken",
    "RefreshToken",
    "Skill",
    "SkillSource",
    "Source",
    "UnsourcedClaimLog",
    "UnsourcedFlag",
    "UrlPattern",
    "UserPreferences",
]
