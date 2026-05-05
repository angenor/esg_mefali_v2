"""F52 US4 — Service de l'extension : ping + sidepanel-context + status.

- ``record_ping(user, payload)`` : UPSERT sur ``(user_id)``.
- ``get_status(user)`` : ``detected`` selon last_ping_at <= 24h.
- ``build_sidepanel_context(user, host, path)`` : projette les candidatures
  actives + 3 offres recommandées si la combinaison host/path matche un
  ``url_pattern`` actif (catalogue F33).

Cloisonnement strict (P2) : tous les SQL passent par ``account_id`` et le RLS.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.extension.schemas_f52 import (
    ExtensionStatusOut,
    SidepanelCandidatureItem,
    SidepanelContextOut,
    SidepanelOfferItem,
)
from app.extension.url_matcher import match_url
from app.models.account_user import AccountUser
from app.models.extension_ping import ExtensionPing

logger = logging.getLogger(__name__)


PING_FRESHNESS = timedelta(hours=24)
APP_BASE_URL = "https://app.esg-mefali.example"


def record_ping(
    db: Session,
    *,
    user: AccountUser,
    extension_version: str,
    user_agent_summary: str,
) -> None:
    """UPSERT idempotent par user_id (table ``extension_ping``)."""
    if user.account_id is None:
        raise ValueError("user.account_id requis")
    now = datetime.now(UTC)
    row = (
        db.query(ExtensionPing)
        .filter(ExtensionPing.user_id == user.id)
        .one_or_none()
    )
    if row is None:
        row = ExtensionPing(
            id=uuid.uuid4(),
            account_id=user.account_id,
            user_id=user.id,
            extension_version=extension_version,
            user_agent_summary=user_agent_summary,
            last_ping_at=now,
            created_at=now,
        )
        db.add(row)
    else:
        row.extension_version = extension_version
        row.user_agent_summary = user_agent_summary
        row.last_ping_at = now
    db.flush()


def get_status(db: Session, *, user: AccountUser) -> ExtensionStatusOut:
    """Retourne le statut courant de l'extension pour le user."""
    row = (
        db.query(ExtensionPing)
        .filter(ExtensionPing.user_id == user.id)
        .one_or_none()
    )
    if row is None:
        return ExtensionStatusOut(detected=False)
    last = row.last_ping_at
    last_aware = last if last.tzinfo else last.replace(tzinfo=UTC)
    detected = (datetime.now(UTC) - last_aware) <= PING_FRESHNESS
    return ExtensionStatusOut(
        detected=detected,
        extension_version=row.extension_version,
        last_ping_at=last_aware,
    )


# ---------------------------------------------------------------------------
# Sidepanel context
# ---------------------------------------------------------------------------


def _matched_offer_ids(db: Session, host: str, path: str) -> list[uuid.UUID]:
    """Retourne les offres dont l'``url_pattern`` actif matche ``host+path``."""
    full_url = f"https://{host}{path}" if not host.startswith("http") else host + path
    try:
        rows = db.execute(
            text(
                """
                SELECT up.pattern, up.pattern_type, up.offre_id
                FROM url_pattern up
                LEFT JOIN offre o ON o.id = up.offre_id
                WHERE up.is_active = TRUE
                  AND (up.offre_id IS NULL OR o.status = 'published')
                """
            )
        ).all()
    except Exception as exc:  # pragma: no cover — schéma url_pattern
        logger.debug("sidepanel: url_pattern read failed: %s", exc)
        return []
    matched: list[uuid.UUID] = []
    for r in rows:
        if r.offre_id is None:
            continue
        if match_url(full_url, r.pattern, r.pattern_type):
            matched.append(r.offre_id)
    return matched


def _active_candidatures(
    db: Session, *, account_id: uuid.UUID, offer_ids: list[uuid.UUID]
) -> list[SidepanelCandidatureItem]:
    if not offer_ids:
        # Listage des candidatures actives (sans filtre offre) si aucun match.
        offer_filter = ""
        params: dict[str, Any] = {"aid": str(account_id)}
    else:
        offer_filter = "AND c.offre_id = ANY(:oids)"
        params = {"aid": str(account_id), "oids": [str(x) for x in offer_ids]}

    sql = text(
        f"""
        SELECT c.id, c.offre_id, c.statut,
               COALESCE(o.name, 'Candidature') AS offre_name,
               COALESCE(o.deadline_candidature, NOW() + INTERVAL '90 days')
                 AS deadline_at
        FROM candidature c
        LEFT JOIN offre o ON o.id = c.offre_id
        WHERE c.account_id = CAST(:aid AS UUID)
          AND c.deleted_at IS NULL
          AND COALESCE(c.statut, '') NOT IN ('soumise', 'archivee', 'rejetee')
          {offer_filter}
        ORDER BY c.updated_at DESC
        LIMIT 5
        """  # noqa: S608 — `offer_filter` est composé de littéraux
    )
    try:
        rows = db.execute(sql, params).all()
    except Exception as exc:  # pragma: no cover — schéma candidature variable
        logger.debug("sidepanel: candidature read failed: %s", exc)
        return []
    items: list[SidepanelCandidatureItem] = []
    for r in rows:
        items.append(
            SidepanelCandidatureItem(
                id=r.id,
                offer_label=r.offre_name,
                deadline_at=r.deadline_at,
                completion_pct=50,  # heuristique MVP — précis dans F26 plus tard
                resume_url=f"{APP_BASE_URL}/candidatures/{r.id}",
            )
        )
    return items


def _recommended_offers(
    db: Session, *, account_id: uuid.UUID, exclude_offer_ids: list[uuid.UUID]
) -> list[SidepanelOfferItem]:
    """Top-3 offres publiées non déjà candidatées."""
    excluded_in_clause = ""
    params: dict[str, Any] = {"aid": str(account_id)}
    if exclude_offer_ids:
        excluded_in_clause = "AND o.id NOT IN :oids"
        params["oids"] = tuple(str(x) for x in exclude_offer_ids)

    sql = text(
        f"""
        SELECT o.id, COALESCE(o.name, 'Offre') AS label
        FROM offre o
        WHERE o.status = 'published'
          AND o.id NOT IN (
            SELECT offre_id FROM candidature
            WHERE account_id = CAST(:aid AS UUID) AND deleted_at IS NULL
          )
          {excluded_in_clause}
        ORDER BY o.updated_at DESC NULLS LAST
        LIMIT 3
        """  # noqa: S608 — `excluded_in_clause` est composée de littéraux
    )
    try:
        rows = db.execute(sql, params).all()
    except Exception as exc:  # pragma: no cover — schéma offre variable
        logger.debug("sidepanel: offre read failed: %s", exc)
        return []
    items: list[SidepanelOfferItem] = []
    for r in rows:
        items.append(
            SidepanelOfferItem(
                id=r.id,
                label=r.label,
                match_score=0.5,  # heuristique MVP — recalculée par F25 ensuite
                matching_url=f"{APP_BASE_URL}/matching?offer={r.id}",
            )
        )
    return items


def build_sidepanel_context(
    db: Session, *, user: AccountUser, host: str, path: str
) -> SidepanelContextOut:
    """Construit le payload sidepanel pour ``user`` sur ``host+path``."""
    if user.account_id is None:
        return SidepanelContextOut(
            matched_offer_ids=[],
            active_candidatures=[],
            recommended_offers=[],
        )
    matched = _matched_offer_ids(db, host, path)
    candidatures = _active_candidatures(
        db, account_id=user.account_id, offer_ids=matched
    )
    recos = _recommended_offers(
        db,
        account_id=user.account_id,
        exclude_offer_ids=[c.id for c in candidatures] + matched,
    )
    return SidepanelContextOut(
        matched_offer_ids=matched,
        active_candidatures=candidatures,
        recommended_offers=recos,
    )
