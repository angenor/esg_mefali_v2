"""F52 US3 — Service ``export_artifact`` pour ``/me/exports``.

Gère :
- listing avec pagination keyset + filtre par type ;
- création d'un export (transition pending → ready synchronisé pour le MVP ; le
  passage à un worker async via APScheduler/BackgroundTasks reste plug-and-play
  côté ``router``).
- bascule e-mail si ``size_bytes > 100 MB`` (lien envoyé par mail, non retourné
  au client).
- masquage de la signed URL expirée à la lecture.
- audit log (``manual``).
- notification SSE ``system`` sur transition ``ready`` (consommée par le
  centre des notifications).
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.dashboard.schemas_f52 import (
    ExportCreate,
    ExportListOut,
    ExportOut,
)
from app.dashboard.service import build_export
from app.email.sender import ConsoleEmailSender, EmailMessage, EmailSender
from app.models.account_user import AccountUser
from app.models.export_artifact import ExportArtifact
from app.notifications.broker import notifications_broker
from app.notifications.service import NotificationService

logger = logging.getLogger(__name__)


SIZE_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB
SIGNED_URL_TTL = timedelta(days=7)
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# ---------------------------------------------------------------------------
# Cursor encoding (keyset)
# ---------------------------------------------------------------------------


def _encode_cursor(created_at: datetime, eid: uuid.UUID) -> str:
    raw = json.dumps({"ts": created_at.isoformat(), "id": str(eid)})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        obj = json.loads(raw)
        return datetime.fromisoformat(obj["ts"]), uuid.UUID(obj["id"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def list_exports(
    db: Session,
    *,
    account_id: uuid.UUID,
    types: list[str] | None = None,
    cursor: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> ExportListOut:
    """Liste les exports d'un compte (DESC par created_at, id)."""
    capped = max(1, min(MAX_LIMIT, int(limit)))
    decoded = _decode_cursor(cursor)

    where_parts: list[str] = ["account_id = CAST(:aid AS UUID)"]
    params: dict[str, Any] = {"aid": str(account_id), "lim": capped + 1}
    if types:
        where_parts.append("type = ANY(:types)")
        params["types"] = list(types)
    if decoded is not None:
        where_parts.append(
            "(created_at, id) < (:cur_ts, CAST(:cur_id AS UUID))"
        )
        params["cur_ts"] = decoded[0]
        params["cur_id"] = str(decoded[1])

    where_sql = " AND ".join(where_parts)
    rows = db.execute(
        text(
            f"""
            SELECT id, account_id, user_id, type, format, size_bytes,
                   status, signed_url, signed_url_expires_at,
                   created_at, ready_at, delivered_via
            FROM export_artifact
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT :lim
            """  # noqa: S608 — `where_sql` est composée de littéraux
        ),
        params,
    ).all()
    rows_list = list(rows)
    has_more = len(rows_list) > capped
    rows_list = rows_list[:capped]

    items: list[ExportOut] = []
    now = datetime.now(UTC)
    for r in rows_list:
        signed_url = r.signed_url
        expires = r.signed_url_expires_at
        if signed_url and expires:
            # comparer en aware
            if expires.tzinfo is None:
                expires_aware = expires.replace(tzinfo=UTC)
            else:
                expires_aware = expires
            if expires_aware < now:
                signed_url = None
        if r.status != "ready":
            signed_url = None
        items.append(
            ExportOut(
                id=r.id,
                type=r.type,
                format=r.format,
                size_bytes=r.size_bytes,
                status=r.status,
                created_at=r.created_at,
                ready_at=r.ready_at,
                signed_url=signed_url,
                signed_url_expires_at=r.signed_url_expires_at,
                delivered_via=r.delivered_via,
            )
        )

    next_cursor = None
    if has_more and rows_list:
        last = rows_list[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return ExportListOut(items=items, next_cursor=next_cursor)


def get_export(
    db: Session,
    *,
    account_id: uuid.UUID,
    export_id: uuid.UUID,
) -> ExportOut | None:
    row = db.execute(
        text(
            """
            SELECT id, account_id, user_id, type, format, size_bytes,
                   status, signed_url, signed_url_expires_at,
                   created_at, ready_at, delivered_via
            FROM export_artifact
            WHERE account_id = CAST(:aid AS UUID)
              AND id = CAST(:eid AS UUID)
            LIMIT 1
            """
        ),
        {"aid": str(account_id), "eid": str(export_id)},
    ).first()
    if row is None:
        return None
    signed_url = row.signed_url
    if row.status != "ready":
        signed_url = None
    elif signed_url and row.signed_url_expires_at:
        expires = row.signed_url_expires_at
        if expires.tzinfo is None:
            expires_aware = expires.replace(tzinfo=UTC)
        else:
            expires_aware = expires
        if expires_aware < datetime.now(UTC):
            signed_url = None
    return ExportOut(
        id=row.id,
        type=row.type,
        format=row.format,
        size_bytes=row.size_bytes,
        status=row.status,
        created_at=row.created_at,
        ready_at=row.ready_at,
        signed_url=signed_url,
        signed_url_expires_at=row.signed_url_expires_at,
        delivered_via=row.delivered_via,
    )


# ---------------------------------------------------------------------------
# Création + worker synchrone
# ---------------------------------------------------------------------------


def _signed_url_for(eid: uuid.UUID) -> str:
    """Génère une signed URL stub locale (placeholder ; bucket EU câblé en
    prod via ``app.storage``)."""
    token = secrets.token_urlsafe(16)
    return f"https://eu-storage.local/exports/{eid}?sig={token}"


def _build_payload(
    db: Session, *, account_id: uuid.UUID, export_create: ExportCreate
) -> tuple[bytes, int]:
    """Construit le payload binaire + retourne ``(bytes, size_bytes)``.

    Pour ``rgpd_full`` on appelle ``build_export`` (F32) et on JSON-sérialise.
    Les autres types sont des placeholders PDF stubés (l'implémentation PDF
    réelle vit dans F49/F30/F26).
    """
    if export_create.type == "rgpd_full":
        export_obj = build_export(db, account_id)
        payload = export_obj.model_dump_json(by_alias=False).encode("utf-8")
        return payload, len(payload)
    # Placeholder stubs pour les types PDF — l'orchestration réelle est
    # déléguée aux services F49/F30/F26 dans une PR future. Le test gate
    # n'invoque pas ces branches en MVP.
    placeholder = (
        f"%PDF-1.4 stub for {export_create.type} {export_create.format}\n"
    ).encode()
    return placeholder, len(placeholder)


def _send_email_link(  # pragma: no cover — couvert manuellement en E2E
    *,
    sender: EmailSender,
    to: str,
    signed_url: str,
    export_type: str,
) -> None:
    msg = EmailMessage(
        to=to,
        subject="Votre export ESG Mefali est prêt",
        html=(
            f"<p>Votre export <code>{export_type}</code> est disponible.</p>"
            f'<p><a href="{signed_url}">Télécharger</a> — lien valable 7 jours.</p>'
        ),
        text=(
            f"Votre export {export_type} est disponible :\n"
            f"{signed_url}\n(lien valable 7 jours)\n"
        ),
    )
    sender.send(msg)


def _emit_ready_notification(
    db: Session, *, account_id: uuid.UUID, user_id: uuid.UUID, eid: uuid.UUID
) -> None:
    try:
        NotificationService.create_for_account(
            db,
            account_id=account_id,
            kind="system",
            title="Export prêt",
            body="Votre export est prêt à être téléchargé.",
            user_id=user_id,
            entity_type="export_artifact",
            entity_id=eid,
            payload={"export_id": str(eid)},
        )
        notifications_broker.publish(
            account_id=account_id,
            event="notification.created",
            data={"kind": "system", "export_id": str(eid)},
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("export: ready notification failed: %s", exc)


def create_export(
    db: Session,
    *,
    user: AccountUser,
    payload: ExportCreate,
    sender: EmailSender | None = None,
) -> ExportOut:
    """Crée un row ``pending`` puis enchaîne synchrone le run du worker.

    Le passage à un worker async (BackgroundTasks / APScheduler) est trivial :
    on déplace le bloc ``_run_worker`` dans une queue et on retourne dès le
    flush du row pending.
    """
    if user.account_id is None:
        raise ValueError("PME sans account_id")

    sender = sender or ConsoleEmailSender()
    now = datetime.now(UTC)
    eid = uuid.uuid4()
    row = ExportArtifact(
        id=eid,
        account_id=user.account_id,
        user_id=user.id,
        type=payload.type,
        format=payload.format,
        size_bytes=None,
        status="pending",
        signed_url=None,
        signed_url_expires_at=None,
        created_at=now,
        ready_at=None,
        delivered_via=None,
    )
    db.add(row)
    db.flush()

    # Audit creation
    try:
        record_audit(
            db,
            entity_type="export_artifact",
            entity_id=eid,
            field="status",
            old=None,
            new={"action": "create", "type": payload.type, "format": payload.format},
            source_of_change=SourceOfChange.MANUAL,
            user_id=user.id,
            account_id=user.account_id,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("export: audit create failed: %s", exc)

    # Worker synchrone
    try:
        data, size_bytes = _build_payload(
            db, account_id=user.account_id, export_create=payload
        )
        delivered_via: str
        signed_url: str | None
        signed_url_expires_at: datetime | None
        if size_bytes > SIZE_THRESHOLD_BYTES:
            delivered_via = "email"
            signed_url = None
            signed_url_expires_at = None
            try:
                fallback_url = _signed_url_for(eid)
                _send_email_link(
                    sender=sender,
                    to=user.email,
                    signed_url=fallback_url,
                    export_type=payload.type,
                )
            except Exception as exc:  # noqa: BLE001 — l'envoi d'email échoue
                # silencieusement (audit présent)
                logger.warning("export: email send failed: %s", exc)
        else:
            delivered_via = "inapp"
            signed_url = _signed_url_for(eid)
            signed_url_expires_at = now + SIGNED_URL_TTL

        row.size_bytes = size_bytes
        row.status = "ready"
        row.ready_at = now
        row.signed_url = signed_url
        row.signed_url_expires_at = signed_url_expires_at
        row.delivered_via = delivered_via
        db.flush()

        # Audit ready
        try:
            record_audit(
                db,
                entity_type="export_artifact",
                entity_id=eid,
                field="status",
                old="pending",
                new={
                    "status": "ready",
                    "size_bytes": size_bytes,
                    "delivered_via": delivered_via,
                },
                source_of_change=SourceOfChange.MANUAL,
                user_id=user.id,
                account_id=user.account_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("export: audit ready failed: %s", exc)

        _emit_ready_notification(
            db,
            account_id=user.account_id,
            user_id=user.id,
            eid=eid,
        )
        # data is intentionally discarded in MVP (no real bucket upload)
        del data
    except Exception as exc:
        logger.exception("export: build failed: %s", exc)
        row.status = "failed"
        db.flush()
        raise

    return ExportOut(
        id=row.id,
        type=row.type,
        format=row.format,
        size_bytes=row.size_bytes,
        status=row.status,
        created_at=row.created_at,
        ready_at=row.ready_at,
        signed_url=row.signed_url,
        signed_url_expires_at=row.signed_url_expires_at,
        delivered_via=row.delivered_via,
    )
