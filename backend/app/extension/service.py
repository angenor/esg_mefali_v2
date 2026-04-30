"""F33 - Service backend extension Chrome."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.extension.schemas import (
    FieldMappingListOut,
    FieldMappingOut,
    ProfileSummaryOut,
    ProjetSummaryOut,
    SuggestFieldIn,
    SuggestFieldOut,
    UrlPatternListOut,
    UrlPatternOut,
)
from app.extension.url_matcher import VALID_NATURES, VALID_TYPES, compile_pattern

logger = logging.getLogger(__name__)


def list_active_url_patterns(db: Session) -> UrlPatternListOut:
    """Retourne tous les url_pattern actifs liés (si offre liée) à une offre publiée."""
    sql = text(
        """
        SELECT up.id, up.pattern, up.pattern_type, up.nature,
               up.fonds_id, up.intermediaire_id, up.offre_id,
               up.preferred_language,
               COALESCE(o.name, '') AS offre_label,
               o.status AS offre_status
        FROM url_pattern up
        LEFT JOIN offre o ON o.id = up.offre_id
        WHERE up.is_active = TRUE
          AND (up.offre_id IS NULL OR o.status = 'published')
        ORDER BY up.created_at ASC
        """
    )
    rows = db.execute(sql).all()
    items = [
        UrlPatternOut(
            id=r.id,
            pattern=r.pattern,
            pattern_type=r.pattern_type,
            nature=r.nature,
            fonds_id=r.fonds_id,
            intermediaire_id=r.intermediaire_id,
            offre_id=r.offre_id,
            offre_label=r.offre_label or None,
            preferred_language=r.preferred_language,
        )
        for r in rows
    ]
    return UrlPatternListOut(items=items, updated_at=datetime.now(UTC))


def build_profile_summary(
    db: Session, *, account_id: uuid.UUID, projet_id: uuid.UUID | None = None
) -> ProfileSummaryOut:
    """Construit la vue compactee profil + projet courant.

    Best-effort : si entreprise/projet manquent, retourne un summary minimal.
    """
    raison_sociale: str | None = None
    secteur: str | None = None
    pays: str | None = None
    taille: int | None = None

    try:
        ent = db.execute(
            text(
                """
                SELECT name, secteur_label, secteur_code,
                       localisation_siege_pays_iso2, taille_effectifs
                FROM entreprise
                WHERE account_id = CAST(:aid AS UUID) AND deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"aid": str(account_id)},
        ).first()
        if ent is not None:
            raison_sociale = ent.name
            secteur = ent.secteur_label or ent.secteur_code
            pays = ent.localisation_siege_pays_iso2
            taille = ent.taille_effectifs
    except Exception as exc:  # pragma: no cover - resilience
        logger.debug("profile_summary: entreprise read failed: %s", exc)

    projet_out: ProjetSummaryOut | None = None
    try:
        params: dict[str, Any] = {"aid": str(account_id)}
        if projet_id:
            sql_proj = text(
                """
                SELECT id, nom, description, montant_recherche_amount,
                       montant_recherche_currency, localisation_pays_iso2
                FROM projet
                WHERE id = CAST(:pid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                LIMIT 1
                """
            )
            params["pid"] = str(projet_id)
            row = db.execute(sql_proj, params).first()
        else:
            row = db.execute(
                text(
                    """
                    SELECT id, nom, description, montant_recherche_amount,
                           montant_recherche_currency, localisation_pays_iso2
                    FROM projet
                    WHERE account_id = CAST(:aid AS UUID)
                      AND deleted_at IS NULL
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ),
                params,
            ).first()
        if row is not None:
            descr = row.description
            short = (descr[:280] + "...") if descr and len(descr) > 280 else descr
            projet_out = ProjetSummaryOut(
                id=row.id,
                titre=row.nom,
                description_courte=short,
                montant_amount=str(row.montant_recherche_amount)
                if row.montant_recherche_amount is not None
                else None,
                montant_currency=row.montant_recherche_currency,
                pays=row.localisation_pays_iso2,
            )
    except Exception as exc:  # pragma: no cover - resilience
        logger.debug("profile_summary: projet read failed: %s", exc)

    return ProfileSummaryOut(
        account_id=account_id,
        raison_sociale=raison_sociale,
        secteur=secteur,
        pays=pays,
        taille_effectifs=taille,
        projet=projet_out,
        generated_at=datetime.now(UTC),
    )


def list_field_mappings(
    db: Session, *, intermediaire_id: uuid.UUID | None = None
) -> FieldMappingListOut:
    """Retourne les mappings publics par intermediaire."""
    if intermediaire_id is not None:
        rows = db.execute(
            text(
                """
                SELECT intermediaire_id, mapping_json
                FROM field_mapping_intermediaire
                WHERE intermediaire_id = CAST(:iid AS UUID)
                """
            ),
            {"iid": str(intermediaire_id)},
        ).all()
    else:
        rows = db.execute(
            text(
                """
                SELECT intermediaire_id, mapping_json
                FROM field_mapping_intermediaire
                ORDER BY created_at ASC
                """
            )
        ).all()
    items = [
        FieldMappingOut(
            intermediaire_id=r.intermediaire_id, mapping_json=r.mapping_json or {}
        )
        for r in rows
    ]
    return FieldMappingListOut(items=items)


def _build_fallback(field_label: str, max_length: int) -> str:
    base = f"[Suggestion non disponible pour {field_label}]"
    return base[: max(1, max_length)]


def _build_prompt(payload: SuggestFieldIn, intermediaire_name: str | None) -> str:
    bits = [
        f"Champ: {payload.field_label}",
        f"Limite caracteres: {payload.field_max_length}",
        f"Langue: {payload.language}",
    ]
    if intermediaire_name:
        bits.append(f"Adapter le ton au format de {intermediaire_name}.")
    bits.append("Reponds en texte brut sans guillemets.")
    return " | ".join(bits)


def _intermediaire_name(db: Session, intermediaire_id: uuid.UUID | None) -> str | None:
    if intermediaire_id is None:
        return None
    try:
        row = db.execute(
            text("SELECT name FROM intermediaire WHERE id = CAST(:iid AS UUID)"),
            {"iid": str(intermediaire_id)},
        ).first()
        return row.name if row else None
    except Exception:
        return None


def suggest_field(
    db: Session,
    *,
    payload: SuggestFieldIn,
) -> SuggestFieldOut:
    """Genere une suggestion texte. Tente le LLM, fallback texte court sinon."""
    intermediaire_name = _intermediaire_name(db, payload.intermediaire_id)
    prompt = _build_prompt(payload, intermediaire_name)
    text_out: str
    source: str = "fallback"
    try:
        from app.llm_client import generate_text  # type: ignore[attr-defined]

        text_out = generate_text(prompt, max_tokens=200)
        if text_out and text_out.strip():
            source = "llm"
        else:
            text_out = _build_fallback(payload.field_label, payload.field_max_length)
    except Exception as exc:  # noqa: BLE001 - fallback is allowed
        logger.info("suggest_field: LLM unavailable, fallback: %s", exc)
        text_out = _build_fallback(payload.field_label, payload.field_max_length)

    if len(text_out) > payload.field_max_length:
        text_out = text_out[: payload.field_max_length]
    return SuggestFieldOut(
        text=text_out,
        length=len(text_out),
        source=source,  # type: ignore[arg-type]
        generated_at=datetime.now(UTC),
    )


def validate_pattern(pattern: str, pattern_type: str, nature: str) -> None:
    """Valide les arguments admin. Leve ValueError si invalide."""
    if pattern_type not in VALID_TYPES:
        raise ValueError(f"pattern_type invalide: {pattern_type}")
    if nature not in VALID_NATURES:
        raise ValueError(f"nature invalide: {nature}")
    compile_pattern(pattern, pattern_type)
