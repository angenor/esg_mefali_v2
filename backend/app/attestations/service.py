"""F30 - AttestationService : generate / revoke / list / get_public.

Le service est volontairement self-contained pour le MVP : il ne consulte pas
F23/F29 directement, le router lui passe ``scores_resolved``. Cela garde le
service deterministe et testable sans monter toute la stack scoring.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.attestations import crypto
from app.attestations.pdf_builder import render_attestation_pdf
from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.models.attestation import Attestation
from app.storage.local import LocalStorage

ALLOWED_VALID_MONTHS = {3, 6, 12}
SCHEMA_VERSION = "v1"


def _purge_verify_cache(public_id: uuid.UUID) -> None:
    """F49 T010 — Hook d'invalidation CDN sur révocation.

    No-op par défaut : aucune `CDN_PURGE_URL` n'est configurée dans le MVP.
    En production, ce hook fera un POST vers le CDN. Le TTL ≤ 60 s côté
    routeRules Nuxt garantit déjà SC-009.
    """
    import logging
    import os

    purge_url = os.environ.get("CDN_PURGE_URL")
    if not purge_url:
        logging.getLogger(__name__).debug(
            "attestations.cdn_purge skipped (no CDN_PURGE_URL) public_id=%s",
            public_id,
        )
        return
    # Hypothèse minimaliste : POST {urls: [...]}.
    try:  # pragma: no cover - dépend d'env externe
        import urllib.request

        req = urllib.request.Request(
            purge_url,
            data=(
                f'{{"urls":["/verify/{public_id}","/verify/{public_id}/json"]}}'
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)  # noqa: S310 - URL configurée
    except Exception:
        logging.getLogger(__name__).warning(
            "attestations.cdn_purge_failed public_id=%s", public_id
        )


class AttestationError(Exception):
    """Base for attestation domain errors."""


class ScoresUnavailableError(AttestationError):
    """Raised when scores requested are not present in the resolved set."""


class KeyMissingError(AttestationError):
    """Raised when the Ed25519 private key env var is not configured."""


@dataclass
class GenerateInput:
    """Input passed to :meth:`AttestationService.generate`."""

    account_id: uuid.UUID
    entreprise_id: uuid.UUID
    entreprise_name: str
    generated_by: uuid.UUID
    scores_to_include: list[str]
    valid_for_months: int
    scores_resolved: dict[str, Any]
    referentiels_versions: dict[str, str]


def _now_utc() -> datetime:
    return datetime.now(UTC)


def compute_status(
    *, valid_until: datetime, revoked_at: datetime | None, now: datetime | None = None
) -> Literal["active", "expired", "revoked"]:
    """Pure helper: derive the attestation status at read time."""
    if revoked_at is not None:
        return "revoked"
    cur = now or _now_utc()
    if valid_until < cur:
        return "expired"
    return "active"


class AttestationService:
    """Service couche metier pour les attestations."""

    def __init__(self, *, db: Session, storage: LocalStorage, app_url: str) -> None:
        self.db = db
        self.storage = storage
        self.app_url = app_url.rstrip("/")

    # ---------- core helpers
    def _verify_url(self, public_id: uuid.UUID) -> str:
        return f"{self.app_url}/verify/{public_id}"

    def _download_url(self, attestation_id: uuid.UUID) -> str:
        return f"{self.app_url}/me/attestations/{attestation_id}/download"

    @staticmethod
    def _file_path(public_id: uuid.UUID, generated_at: datetime) -> str:
        yyyy = f"{generated_at.year:04d}"
        mm = f"{generated_at.month:02d}"
        return f"{yyyy}/{mm}/{public_id}.pdf"

    # ---------- generate
    def generate(self, payload: GenerateInput) -> Attestation:
        """Generate a signed attestation, persist it, and return the row."""
        if payload.valid_for_months not in ALLOWED_VALID_MONTHS:
            raise ValueError("valid_for_months must be in {3, 6, 12}")

        missing = [
            s for s in payload.scores_to_include if s not in payload.scores_resolved
        ]
        if missing:
            raise ScoresUnavailableError(
                f"Scores demandes non disponibles : {', '.join(missing)}"
            )

        try:
            keypair = crypto.load_keypair()
        except crypto.KeyNotConfiguredError as exc:
            raise KeyMissingError(str(exc)) from exc

        public_id = uuid.uuid4()
        attestation_id = uuid.uuid4()
        generated_at = _now_utc()
        valid_until = generated_at + timedelta(days=30 * payload.valid_for_months)

        document: dict[str, Any] = {
            "entreprise_name": payload.entreprise_name,
            "generated_at": generated_at.isoformat(),
            "public_id": str(public_id),
            "referentiels_versions": payload.referentiels_versions,
            "schema_version": SCHEMA_VERSION,
            "scores": {
                k: payload.scores_resolved[k] for k in payload.scores_to_include
            },
            "valid_until": valid_until.isoformat(),
        }
        canonical = crypto.canonicalize_document(document)
        hash_doc = crypto.compute_document_hash(canonical)
        signature_hex = crypto.sign_document(canonical, keypair)

        rel_path = self._file_path(public_id, generated_at)
        pdf_bytes = render_attestation_pdf(
            entreprise_name=payload.entreprise_name,
            public_id=str(public_id),
            generated_at_iso=document["generated_at"],
            valid_until_iso=document["valid_until"],
            scores=document["scores"],
            referentiels_versions=payload.referentiels_versions,
            verify_url=self._verify_url(public_id),
            signature_hex=signature_hex,
            pubkey_fingerprint=keypair.fingerprint,
        )
        self.storage.save(rel_path, pdf_bytes)

        row = Attestation(
            id=attestation_id,
            account_id=payload.account_id,
            entreprise_id=payload.entreprise_id,
            public_id=public_id,
            scores_inclus_json=document["scores"],
            referentiels_versions_json=payload.referentiels_versions,
            file_path=rel_path,
            signature_ed25519=signature_hex,
            pubkey_fingerprint=keypair.fingerprint,
            hash_document=hash_doc,
            generated_at=generated_at,
            generated_by=payload.generated_by,
            valid_until=valid_until,
            version=1,
        )
        self.db.add(row)
        self.db.flush()

        record_audit(
            self.db,
            entity_type="attestation",
            entity_id=row.id,
            field="generated",
            old=None,
            new={
                "public_id": str(public_id),
                "valid_until": valid_until.isoformat(),
                "scores_to_include": payload.scores_to_include,
            },
            source_of_change=SourceOfChange.MANUAL,
            account_id=payload.account_id,
            user_id=payload.generated_by,
        )
        return row

    # ---------- list
    def list_for_account(
        self, *, account_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[Attestation]:
        return list(
            self.db.query(Attestation)
            .filter(Attestation.account_id == account_id)
            .order_by(Attestation.generated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # ---------- revoke
    def _get_pme_or_404(
        self, *, account_id: uuid.UUID, attestation_id: uuid.UUID
    ) -> Attestation:
        row = (
            self.db.query(Attestation)
            .filter(
                Attestation.id == attestation_id,
                Attestation.account_id == account_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": "Attestation introuvable."},
            )
        return row

    def _revoke_common(
        self,
        *,
        row: Attestation,
        actor_id: uuid.UUID,
        reason: str,
        source: SourceOfChange,
    ) -> Attestation:
        if row.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "already_revoked",
                    "message": "Attestation deja revoquee.",
                },
            )
        old = {"revoked_at": None, "revoked_by": None, "revoked_reason": None}
        row.revoked_at = _now_utc()
        row.revoked_by = actor_id
        row.revoked_reason = reason
        new = {
            "revoked_at": row.revoked_at.isoformat(),
            "revoked_by": str(actor_id),
            "revoked_reason": reason,
        }
        self.db.flush()
        record_audit(
            self.db,
            entity_type="attestation",
            entity_id=row.id,
            field="revoked",
            old=old,
            new=new,
            source_of_change=source,
            account_id=row.account_id,
            user_id=actor_id,
        )
        # F49 T010 — invalidation explicite du cache CDN sur /verify/{public_id}.
        # En dev/test : no-op silencieux. En prod : appel HTTP au CDN (à brancher
        # via variable d'env CDN_PURGE_URL ; pas configuré dans MVP).
        try:
            _purge_verify_cache(row.public_id)
        except Exception:  # noqa: BLE001
            # Best-effort : la révocation ne doit jamais échouer pour ça.
            pass
        return row

    def revoke_by_pme(
        self,
        *,
        account_id: uuid.UUID,
        attestation_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> Attestation:
        row = self._get_pme_or_404(
            account_id=account_id, attestation_id=attestation_id
        )
        return self._revoke_common(
            row=row, actor_id=actor_id, reason=reason, source=SourceOfChange.MANUAL
        )

    def revoke_by_admin(
        self, *, attestation_id: uuid.UUID, actor_id: uuid.UUID, reason: str
    ) -> Attestation:
        row = (
            self.db.query(Attestation)
            .filter(Attestation.id == attestation_id)
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": "Attestation introuvable."},
            )
        return self._revoke_common(
            row=row, actor_id=actor_id, reason=reason, source=SourceOfChange.ADMIN
        )

    # ---------- public verification
    def get_public(self, *, public_id: uuid.UUID) -> Attestation | None:
        return (
            self.db.query(Attestation)
            .filter(Attestation.public_id == public_id)
            .first()
        )

    @staticmethod
    def set_public_session(db: Session) -> None:
        """Mark the current session as 'admin-context' for read-only public access."""
        db.execute(text("SET LOCAL app.is_admin = 'true'"))

    def read_pdf_bytes(self, row: Attestation) -> bytes:
        return self.storage.read(row.file_path)
