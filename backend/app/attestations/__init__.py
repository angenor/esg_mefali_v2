"""F30 — Attestation Verifiable.

Module backend self-contained livrant :
- Signature Ed25519 et canonicalisation JSON deterministe (``crypto.py``).
- Generation du PDF (``pdf_builder.py``).
- Service metier (``service.py``) et router FastAPI (``router.py``).
- Modele SQLAlchemy ``Attestation`` (dans ``app.models.attestation``).

Voir ``specs/030-attestation-verifiable/``.
"""

from __future__ import annotations
