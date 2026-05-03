"""F42 — Schémas Pydantic pour /me/preferences."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

OnboardingState = Literal["pending", "completed", "skipped", "dismissed"]


class UserPreferencesOut(BaseModel):
    model_config = {"extra": "forbid"}

    onboarding_state: OnboardingState
    onboarding_state_updated_at: datetime


class UserPreferencesPatch(BaseModel):
    model_config = {"extra": "forbid"}

    onboarding_state: OnboardingState | None = None
