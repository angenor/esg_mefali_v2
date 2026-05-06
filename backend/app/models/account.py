"""Modèle Account (mappe la table F01 ``account``).

F58 — extension : 3 sous-quotas tokens / jour, paramétrables par administrateur
selon plan d'abonnement (CHECK ``daily_conversation_quota +
daily_ocr_analysis_quota <= daily_token_quota`` côté DB).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # F58 — Sous-quotas tokens (FR-012/FR-013)
    daily_token_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="50000"
    )
    daily_conversation_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30000"
    )
    daily_ocr_analysis_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="20000"
    )
