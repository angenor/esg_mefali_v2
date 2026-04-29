"""F10 — PII masking utility (T016).

Masks email, phone, IBAN and CIN tokens in free-text strings. Used on
public attestation projections (T054) and other surfaces that may leak
PII into otherwise public payloads.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phone — 8+ digits, optionally separated by spaces / dots / dashes / parens.
_PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,}\d{2,4}"
)
# IBAN — country code (2 letters) + 2 digits + up to 30 alnum.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
# Moroccan CIN — letter + 4-7 digits (heuristic).
_CIN_RE = re.compile(r"\b[A-Z]{1,2}\d{4,7}\b")

MASK = "[REDACTED]"


def mask_pii(text: str | None) -> str | None:
    """Return ``text`` with email/phone/IBAN/CIN tokens replaced by ``[REDACTED]``.

    ``None`` is passed through unchanged.
    """
    if text is None:
        return None
    out = _EMAIL_RE.sub(MASK, text)
    out = _IBAN_RE.sub(MASK, out)
    out = _CIN_RE.sub(MASK, out)
    out = _PHONE_RE.sub(MASK, out)
    return out
