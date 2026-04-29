"""F02 — Schémas Pydantic v2 pour l'API d'auth (cf. contracts/auth.openapi.yaml).

T022 — référence plan.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import PasswordPolicyError, validate_password_policy


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_policy(cls, v: str) -> str:
        try:
            validate_password_policy(v)
        except PasswordPolicyError as exc:
            raise ValueError(str(exc)) from exc
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_policy(cls, v: str) -> str:
        try:
            validate_password_policy(v)
        except PasswordPolicyError as exc:
            raise ValueError(str(exc)) from exc
        return v


class MeOut(BaseModel):
    user_id: UUID
    account_id: UUID | None
    role: Literal["pme", "admin"]
    email: EmailStr
    created_at: datetime
    last_login_at: datetime | None = None


class NeutralAck(BaseModel):
    status: Literal["accepted"] = "accepted"


class ErrorBody(BaseModel):
    code: str
    message: str


class Error(BaseModel):
    error: ErrorBody


class ValidationErrorBody(BaseModel):
    code: Literal["validation_error"] = "validation_error"
    message: str
    fields: dict[str, list[str]]


class ValidationError(BaseModel):
    error: ValidationErrorBody
