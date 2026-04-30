"""F30 - Router FastAPI : /me/attestations + /admin/attestations + /verify/*.

Pour le MVP, le router accepte des stubs ``scores_resolved`` et
``referentiels_versions`` via le body, ce qui permet :
- aux PME (en attendant l'integration F23/F29 enrichie post-MVP) de fournir
  explicitement les valeurs a inclure ;
- aux tests d'orchestrer sans monter toute la stack scoring.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.attestations import crypto
from app.attestations.schemas import (
    AttestationOut,
    PubkeyOut,
    PublicVerification,
    RevokeRequest,
)
from app.attestations.service import (
    AttestationService,
    GenerateInput,
    KeyMissingError,
    ScoresUnavailableError,
    compute_status,
)
from app.auth.dependencies import get_current_admin, get_current_pme
from app.config import get_settings
from app.core.rate_limit import check_rate
from app.db import get_db
from app.models.account_user import AccountUser
from app.models.attestation import Attestation
from app.storage.local import LocalStorage

router = APIRouter()


class GenerateBody(BaseModel):
    """Body F30 MVP : scores deja resolus fournis explicitement.

    Post-MVP, ``scores_resolved`` et ``referentiels_versions`` seront
    auto-derives par le service via F23/F29.
    """

    model_config = ConfigDict(extra="forbid")

    scores_to_include: list[str] = Field(min_length=1, max_length=20)
    valid_for_months: int = 6
    scores_resolved: dict[str, Any] = Field(default_factory=dict)
    referentiels_versions: dict[str, str] = Field(default_factory=dict)
    entreprise_name: str = Field(min_length=1, max_length=200)


def _storage_root(settings) -> str:  # noqa: ANN001 — loose settings type
    return getattr(settings, "ATTESTATION_STORAGE_DIR", None) or "var/attestations"


def _service(db: Session) -> AttestationService:
    settings = get_settings()
    storage = LocalStorage(_storage_root(settings))
    return AttestationService(db=db, storage=storage, app_url=settings.APP_URL)


def _to_out(att: Attestation, app_url: str) -> AttestationOut:
    base = app_url.rstrip("/")
    return AttestationOut(
        id=att.id,
        public_id=att.public_id,
        status=compute_status(valid_until=att.valid_until, revoked_at=att.revoked_at),
        generated_at=att.generated_at,
        valid_until=att.valid_until,
        revoked_at=att.revoked_at,
        scores_inclus=att.scores_inclus_json,
        referentiels_versions=att.referentiels_versions_json,
        signature_ed25519=att.signature_ed25519,
        pubkey_fingerprint=att.pubkey_fingerprint,
        hash_document=att.hash_document,
        download_url=f"{base}/me/attestations/{att.id}/download",
        verify_url=f"{base}/verify/{att.public_id}",
    )


def _to_public(att: Attestation, app_url: str) -> PublicVerification:
    base = app_url.rstrip("/")
    name = att.scores_inclus_json.get("__entreprise_name__", "PME")
    return PublicVerification(
        public_id=att.public_id,
        status=compute_status(valid_until=att.valid_until, revoked_at=att.revoked_at),
        entreprise_name=name,
        generated_at=att.generated_at,
        valid_until=att.valid_until,
        revoked_at=att.revoked_at,
        scores={
            k: v for k, v in att.scores_inclus_json.items() if not k.startswith("__")
        },
        referentiels_versions=att.referentiels_versions_json,
        hash_document=att.hash_document,
        signature_ed25519=att.signature_ed25519,
        pubkey_fingerprint=att.pubkey_fingerprint,
        download_url=f"{base}/verify/{att.public_id}/download",
    )


# ---------- PME endpoints
@router.post(
    "/me/attestations",
    response_model=AttestationOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_attestation(
    body: GenerateBody,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> AttestationOut:
    settings = get_settings()
    service = _service(db)
    try:
        scores_resolved = dict(body.scores_resolved)
        scores_resolved["__entreprise_name__"] = body.entreprise_name
        included = list(body.scores_to_include) + ["__entreprise_name__"]
        att = service.generate(
            GenerateInput(
                account_id=user.account_id,  # type: ignore[arg-type]
                entreprise_id=user.account_id,  # type: ignore[arg-type]
                entreprise_name=body.entreprise_name,
                generated_by=user.id,
                scores_to_include=included,
                valid_for_months=body.valid_for_months,
                scores_resolved=scores_resolved,
                referentiels_versions=body.referentiels_versions,
            )
        )
    except ScoresUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "scores_unavailable", "message": str(exc)},
        ) from exc
    except KeyMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "key_not_configured", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_input", "message": str(exc)},
        ) from exc
    # Build response BEFORE commit: SQLAlchemy expires attrs on commit and
    # reload would run in a fresh tx without `app.current_account_id`
    # GUC, so RLS would filter the row out (ObjectDeletedError).
    out = _to_out(att, settings.APP_URL)
    db.commit()
    return out


@router.get("/me/attestations", response_model=list[AttestationOut])
def list_me_attestations(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> list[AttestationOut]:
    settings = get_settings()
    service = _service(db)
    rows = service.list_for_account(
        account_id=user.account_id,  # type: ignore[arg-type]
        limit=min(max(limit, 1), 100),
        offset=max(offset, 0),
    )
    return [_to_out(r, settings.APP_URL) for r in rows]


@router.get("/me/attestations/{attestation_id}/download")
def download_me_attestation(
    attestation_id: uuid.UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Response:
    service = _service(db)
    row = service._get_pme_or_404(  # noqa: SLF001 — internal helper used here
        account_id=user.account_id,  # type: ignore[arg-type]
        attestation_id=attestation_id,
    )
    pdf_bytes = service.read_pdf_bytes(row)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="attestation-{row.public_id}.pdf"'
            )
        },
    )


@router.post(
    "/me/attestations/{attestation_id}/revoke", response_model=AttestationOut
)
def revoke_me_attestation(
    attestation_id: uuid.UUID,
    body: RevokeRequest,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> AttestationOut:
    settings = get_settings()
    service = _service(db)
    att = service.revoke_by_pme(
        account_id=user.account_id,  # type: ignore[arg-type]
        attestation_id=attestation_id,
        actor_id=user.id,
        reason=body.reason,
    )
    # Build response BEFORE commit: SQLAlchemy expires attrs on commit and
    # reload would run in a fresh tx without `app.current_account_id`
    # GUC, so RLS would filter the row out (ObjectDeletedError).
    out = _to_out(att, settings.APP_URL)
    db.commit()
    return out


@router.post(
    "/admin/attestations/{attestation_id}/revoke", response_model=AttestationOut
)
def revoke_admin_attestation(
    attestation_id: uuid.UUID,
    body: RevokeRequest,
    admin: AccountUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AttestationOut:
    settings = get_settings()
    service = _service(db)
    att = service.revoke_by_admin(
        attestation_id=attestation_id, actor_id=admin.id, reason=body.reason
    )
    # Build response BEFORE commit: SQLAlchemy expires attrs on commit and
    # reload would run in a fresh tx without `app.current_account_id`
    # GUC, so RLS would filter the row out (ObjectDeletedError).
    out = _to_out(att, settings.APP_URL)
    db.commit()
    return out


# ---------- Public endpoints
@router.get("/verify/_pubkey", response_model=PubkeyOut)
def get_pubkey() -> PubkeyOut:
    try:
        keypair = crypto.load_keypair()
    except crypto.KeyNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "key_not_configured", "message": str(exc)},
        ) from exc
    return PubkeyOut(
        pubkey_hex=keypair.public_hex, pubkey_fingerprint=keypair.fingerprint
    )


def _rate_limit_verify(request: Request) -> None:
    check_rate(request, scope="verify_public", rate="60/minute")


@router.get("/verify/{public_id}/json", response_model=PublicVerification)
def verify_public_json(
    public_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_rate_limit_verify),
) -> PublicVerification:
    settings = get_settings()
    service = _service(db)
    AttestationService.set_public_session(db)
    row = service.get_public(public_id=public_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Attestation introuvable."},
        )
    return _to_public(row, settings.APP_URL)


_HTML_TEMPLATE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow">
<title>Verification attestation ESG Mefali</title>
<style>
  body{{font-family:sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222}}
  .status{{padding:.5rem 1rem;border-radius:.4rem;display:inline-block}}
  .status.active{{background:#e6f6ec;color:#1d6b32}}
  .status.expired{{background:#fff4e6;color:#8a4b00}}
  .status.revoked{{background:#fde8e8;color:#9b1c1c}}
  table{{border-collapse:collapse;margin-top:1rem;width:100%}}
  td,th{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left;font-size:.9rem}}
</style></head><body>
<h1>Attestation {public_id}</h1>
<p>PME : <strong>{entreprise_name}</strong></p>
<p>Statut : <span class="status {status}">{status}</span></p>
<p>Emise le {generated_at} - Valide jusqu'au {valid_until}{revoked_block}</p>
<h2>Scores</h2>{scores_table}
<h2>Versions des referentiels</h2>{ref_table}
<p style="font-size:.8rem;color:#666">Hash document : <code>{hash_document}</code></p>
<p style="font-size:.8rem;color:#666">Signature Ed25519 : <code>{signature_ed25519}</code></p>
<p>Empreinte cle publique : <code>{pubkey_fingerprint}</code></p>
<p><a href="{download_url}">Telecharger l'attestation originale (PDF)</a></p>
</body></html>"""


def _render_kv_table(d: dict[str, Any]) -> str:
    if not d:
        return "<p>(aucun)</p>"
    rows = "".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in sorted(d.items())
    )
    return f"<table>{rows}</table>"


@router.get("/verify/{public_id}", response_class=HTMLResponse)
def verify_public_html(
    public_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_rate_limit_verify),
) -> HTMLResponse:
    settings = get_settings()
    service = _service(db)
    AttestationService.set_public_session(db)
    row = service.get_public(public_id=public_id)
    if row is None:
        return HTMLResponse(
            "<h1>Attestation introuvable</h1>",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    public = _to_public(row, settings.APP_URL)
    revoked_block = (
        f" - Revoquee le {public.revoked_at}" if public.revoked_at else ""
    )
    body = _HTML_TEMPLATE.format(
        public_id=public.public_id,
        entreprise_name=public.entreprise_name,
        status=public.status,
        generated_at=public.generated_at.isoformat(),
        valid_until=public.valid_until.isoformat(),
        revoked_block=revoked_block,
        scores_table=_render_kv_table(public.scores),
        ref_table=_render_kv_table(public.referentiels_versions),
        hash_document=public.hash_document,
        signature_ed25519=public.signature_ed25519[:32] + "...",
        pubkey_fingerprint=public.pubkey_fingerprint,
        download_url=public.download_url,
    )
    return HTMLResponse(body)


@router.get("/verify/{public_id}/download")
def verify_public_download(
    public_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_rate_limit_verify),
) -> Response:
    service = _service(db)
    AttestationService.set_public_session(db)
    row = service.get_public(public_id=public_id)
    if row is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": {"code": "not_found", "message": "Inconnu."}},
        )
    pdf_bytes = service.read_pdf_bytes(row)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="attestation-{public_id}.pdf"'
            )
        },
    )
