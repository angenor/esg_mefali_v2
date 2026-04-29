"""Type Money — montant + devise (F05 — US4).

Pydantic v2, immutable (`frozen=True`), strict (`extra='forbid'`).
Sérialise `amount` en chaîne décimale stable (préserve la précision côté JSON).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.currencies import Currency


class Money(BaseModel):
    """Montant typé : `(amount: Decimal >= 0, currency: Currency)`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: Decimal = Field(..., ge=0)
    currency: Currency

    @field_serializer("amount")
    def _serialize_amount(self, v: Decimal) -> str:
        # `format(v, 'f')` évite la notation scientifique et préserve l'échelle.
        return format(v, "f")
