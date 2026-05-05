"""F34/F51 — Service applicatif ``/me/candidatures``."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.candidatures.schemas import VALID_CANDIDATURE_STATUTS

logger = logging.getLogger(__name__)


class CandidatureNotFoundError(LookupError):
    """Candidature introuvable ou n'appartenant pas à la PME."""


class InvalidCandidatureStatutError(ValueError):
    """Statut hors liste blanche."""


class VersionConflictError(Exception):
    """Optimistic lock mismatch."""

    def __init__(self, current_version: int, current_draft: dict[str, Any]) -> None:
        super().__init__("version_conflict")
        self.current_version = current_version
        self.current_draft = current_draft


class AlreadySubmittedError(Exception):
    """Candidature déjà soumise — mutations gelées (P4)."""


class IncompleteDossierError(Exception):
    """Soumission impossible : progression < 100 %."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__("incomplete_dossier")
        self.missing = missing


class ConfirmationRequiredError(Exception):
    """Double-confirmation incomplète."""


_LIST_LIMIT_HARD = 200


def _progression_from_snapshot(snapshot_json: dict | None) -> int:
    if not isinstance(snapshot_json, dict):
        return 0
    val = snapshot_json.get("progression_pct")
    if isinstance(val, bool):
        return 0
    if not isinstance(val, int):
        return 0
    if val < 0:
        return 0
    if val > 100:
        return 100
    return val


def _calc_progression(draft: dict[str, Any], step_courant: int) -> int:
    """Règle data-model.md §3 : palier 20/40/60/80/100 selon avancement."""
    if not isinstance(draft, dict):
        return 0
    pct = 0
    step1 = draft.get("step1") or {}
    if isinstance(step1, dict) and step1.get("offre_id") and step1.get("projet_id"):
        pct = 20
    step2 = draft.get("step2") or {}
    if isinstance(step2, dict) and step2.get("entreprise"):
        pct = max(pct, 40)
    step3 = draft.get("step3") or {}
    if isinstance(step3, dict):
        completed = step3.get("checklist_completed")
        if isinstance(completed, list) and len(completed) > 0:
            pct = max(pct, 60)
    step4 = draft.get("step4") or {}
    if isinstance(step4, dict):
        rep = step4.get("reponses_libres")
        if isinstance(rep, list) and len(rep) > 0:
            pct = max(pct, 80)
    step5 = draft.get("step5") or {}
    if isinstance(step5, dict) and step5.get("user_acknowledged_intangible") is True:
        pct = 100
    if step_courant >= 5 and pct >= 80 and (
        isinstance(step5, dict) and step5.get("user_acknowledged_intangible") is True
    ):
        pct = 100
    return min(100, max(0, pct))


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Fusion profonde (top-level keys + 1 niveau pour step1..step5)."""
    out = dict(base) if isinstance(base, dict) else {}
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out


def list_for_account(
    db: Session,
    *,
    account_id: uuid.UUID,
    limit: int = _LIST_LIMIT_HARD,
) -> list[dict]:
    """Liste des candidatures non supprimées de la PME, triées updated_at DESC."""
    capped = max(1, min(_LIST_LIMIT_HARD, int(limit)))
    rows = (
        db.execute(
            text(
                """
                SELECT id, projet_id, offre_id, statut, snapshot_json,
                       created_at, updated_at
                FROM candidature
                WHERE account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT :lim
                """
            ),
            {"aid": str(account_id), "lim": capped},
        )
        .mappings()
        .all()
    )
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "projet_id": r["projet_id"],
                "offre_id": r["offre_id"],
                "statut": r["statut"],
                "progression_pct": _progression_from_snapshot(r["snapshot_json"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return out


def update_status(
    db: Session,
    *,
    candidature_id: uuid.UUID,
    account_id: uuid.UUID,
    user_id: uuid.UUID | None,
    new_statut: str,
) -> dict:
    """Met à jour ``statut`` ; audit ; retourne dict {id, statut, version, updated_at}."""
    if new_statut not in VALID_CANDIDATURE_STATUTS:
        raise InvalidCandidatureStatutError(new_statut)

    row = (
        db.execute(
            text(
                """
                SELECT id, statut, version
                FROM candidature
                WHERE id = CAST(:cid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                """
            ),
            {"cid": str(candidature_id), "aid": str(account_id)},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise CandidatureNotFoundError(str(candidature_id))

    old_statut = row["statut"]
    if old_statut == new_statut:
        cur = (
            db.execute(
                text(
                    "SELECT updated_at, version FROM candidature "
                    "WHERE id = CAST(:cid AS UUID)"
                ),
                {"cid": str(candidature_id)},
            )
            .mappings()
            .first()
        )
        return {
            "id": candidature_id,
            "statut": new_statut,
            "version": cur["version"] if cur else row["version"],
            "updated_at": cur["updated_at"] if cur else datetime.now(tz=UTC),
        }

    now = datetime.now(tz=UTC).replace(tzinfo=None)
    db.execute(
        text(
            """
            UPDATE candidature
            SET statut = :s,
                version = version + 1,
                updated_at = :ts
            WHERE id = CAST(:cid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {
            "s": new_statut,
            "ts": now,
            "cid": str(candidature_id),
            "aid": str(account_id),
        },
    )
    try:
        record_audit(
            db,
            entity_type="candidature",
            entity_id=candidature_id,
            field="statut",
            old=old_statut,
            new=new_statut,
            source_of_change=SourceOfChange.MANUAL,
            user_id=str(user_id) if user_id else None,
            account_id=str(account_id),
        )
    except Exception as exc:  # noqa: BLE001 — audit best-effort
        logger.warning("candidature: audit failed: %s", exc)

    refreshed = (
        db.execute(
            text(
                "SELECT id, statut, version, updated_at "
                "FROM candidature WHERE id = CAST(:cid AS UUID)"
            ),
            {"cid": str(candidature_id)},
        )
        .mappings()
        .first()
    )
    assert refreshed is not None
    return dict(refreshed)


# ---------- F51 — Wizard ----------


def _fetch_candidature(
    db: Session, *, candidature_id: uuid.UUID, account_id: uuid.UUID
) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                """
                SELECT id, projet_id, offre_id, statut, version,
                       step_courant, progression_pct, draft_snapshot_json,
                       snapshot_json, submitted_at, created_at, updated_at
                FROM candidature
                WHERE id = CAST(:cid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                """
            ),
            {"cid": str(candidature_id), "aid": str(account_id)},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise CandidatureNotFoundError(str(candidature_id))
    return dict(row)


def get_detail(
    db: Session,
    *,
    account_id: uuid.UUID,
    candidature_id: uuid.UUID,
) -> dict[str, Any]:
    """Détail candidature + offre/projet/timeline/documents."""
    row = _fetch_candidature(db, candidature_id=candidature_id, account_id=account_id)

    offre = (
        db.execute(
            text(
                """
                SELECT o.id, o.nom, o.type, o.montant_min, o.montant_max,
                       o.documents_requis, i.nom AS intermediaire_nom
                FROM offre o
                LEFT JOIN intermediaire i ON i.id = o.intermediaire_id
                WHERE o.id = CAST(:oid AS UUID)
                """
            ),
            {"oid": str(row["offre_id"])},
        )
        .mappings()
        .first()
    )
    projet = (
        db.execute(
            text(
                "SELECT id, titre, description FROM projet "
                "WHERE id = CAST(:pid AS UUID)"
            ),
            {"pid": str(row["projet_id"])},
        )
        .mappings()
        .first()
    )

    timeline_rows = (
        db.execute(
            text(
                """
                SELECT timestamp AS ts, field, old_value, new_value,
                       source_of_change, user_id
                FROM audit_log
                WHERE entity_type = 'candidature'
                  AND entity_id = CAST(:cid AS UUID)
                ORDER BY timestamp ASC
                LIMIT 200
                """
            ),
            {"cid": str(candidature_id)},
        )
        .mappings()
        .all()
    )
    timeline: list[dict[str, Any]] = [
        {
            "ts": r["ts"],
            "event": (
                "step_changed" if r["field"] == "step_courant"
                else "submitted" if r["field"] == "submitted_at"
                else "status_changed" if r["field"] == "statut"
                else "updated"
            ),
            "by": "PME" if r["user_id"] else "system",
            "field": r["field"],
            "from": r["old_value"],
            "to": r["new_value"],
            "comment": None,
        }
        for r in timeline_rows
    ]

    docs_rows = (
        db.execute(
            text(
                """
                SELECT dlp.document_id, dlp.created_at AS uploaded_at,
                       d.filename
                FROM document_link_projet dlp
                JOIN document_entreprise d ON d.id = dlp.document_id
                WHERE dlp.account_id = CAST(:aid AS UUID)
                  AND dlp.projet_id = CAST(:pid AS UUID)
                  AND d.deleted_at IS NULL
                ORDER BY dlp.created_at DESC
                """
            ),
            {"aid": str(account_id), "pid": str(row["projet_id"])},
        )
        .mappings()
        .all()
    )
    draft = row["draft_snapshot_json"] or {}
    checklist_map: dict[str, str] = {}
    step3 = draft.get("step3") if isinstance(draft, dict) else None
    if isinstance(step3, dict):
        for link in step3.get("documents_links") or []:
            if isinstance(link, dict) and link.get("document_id") and link.get("checklist_key"):
                checklist_map[str(link["document_id"])] = str(link["checklist_key"])

    documents_lies = [
        {
            "document_id": r["document_id"],
            "checklist_key": checklist_map.get(str(r["document_id"])),
            "filename": r["filename"],
            "uploaded_at": r["uploaded_at"],
        }
        for r in docs_rows
    ]

    offre_dict: dict[str, Any] = {"id": row["offre_id"]}
    if offre is not None:
        offre_dict.update(
            {
                "id": offre["id"],
                "nom": offre.get("nom"),
                "intermediaire_nom": offre.get("intermediaire_nom"),
                "type": offre.get("type"),
                "montant_min": offre.get("montant_min"),
                "montant_max": offre.get("montant_max"),
                "documents_requis": offre.get("documents_requis") or [],
            }
        )
    projet_dict: dict[str, Any] = {"id": row["projet_id"]}
    if projet is not None:
        projet_dict.update(
            {
                "id": projet["id"],
                "titre": projet.get("titre"),
                "description": projet.get("description"),
            }
        )

    return {
        "id": row["id"],
        "offre": offre_dict,
        "projet": projet_dict,
        "statut": row["statut"] or "brouillon",
        "step_courant": int(row["step_courant"] or 1),
        "progression_pct": int(row["progression_pct"] or 0),
        "draft_snapshot_json": draft if isinstance(draft, dict) else {},
        "submitted_at": row["submitted_at"],
        "submitted_snapshot_json": row["snapshot_json"] if row["submitted_at"] else None,
        "timeline": timeline,
        "documents_lies": documents_lies,
        "version": int(row["version"]),
    }


def save_draft(
    db: Session,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID | None,
    candidature_id: uuid.UUID,
    patch: dict[str, Any],
    expected_version: int,
    new_step: int | None,
) -> dict[str, Any]:
    """PATCH brouillon : deep merge + recalcul progression + audit transition d'étape."""
    row = _fetch_candidature(db, candidature_id=candidature_id, account_id=account_id)

    if row["submitted_at"] is not None:
        raise AlreadySubmittedError("already_submitted")

    if int(row["version"]) != int(expected_version):
        cur_draft = row["draft_snapshot_json"] or {}
        raise VersionConflictError(
            current_version=int(row["version"]),
            current_draft=cur_draft if isinstance(cur_draft, dict) else {},
        )

    base = row["draft_snapshot_json"] or {}
    base = base if isinstance(base, dict) else {}
    merged = _deep_merge(base, patch) if patch else base

    old_step = int(row["step_courant"] or 1)
    target_step = int(new_step) if new_step is not None else old_step
    progression = _calc_progression(merged, target_step)

    now = datetime.now(tz=UTC).replace(tzinfo=None)
    import json as _json

    db.execute(
        text(
            """
            UPDATE candidature
            SET draft_snapshot_json = CAST(:draft AS JSONB),
                step_courant = :step,
                progression_pct = :pct,
                version = version + 1,
                updated_at = :ts
            WHERE id = CAST(:cid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {
            "draft": _json.dumps(merged, default=str),
            "step": target_step,
            "pct": progression,
            "ts": now,
            "cid": str(candidature_id),
            "aid": str(account_id),
        },
    )

    if target_step != old_step:
        try:
            record_audit(
                db,
                entity_type="candidature",
                entity_id=candidature_id,
                field="step_courant",
                old=old_step,
                new=target_step,
                source_of_change=SourceOfChange.MANUAL,
                user_id=str(user_id) if user_id else None,
                account_id=str(account_id),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("candidature: audit step failed: %s", exc)

    refreshed = (
        db.execute(
            text(
                "SELECT id, step_courant, progression_pct, draft_snapshot_json, "
                "version, updated_at FROM candidature WHERE id = CAST(:cid AS UUID)"
            ),
            {"cid": str(candidature_id)},
        )
        .mappings()
        .first()
    )
    assert refreshed is not None
    out = dict(refreshed)
    if not isinstance(out["draft_snapshot_json"], dict):
        out["draft_snapshot_json"] = {}
    return out


def _build_submitted_snapshot(
    db: Session, *, row: dict[str, Any], draft: dict[str, Any], account_id: uuid.UUID
) -> dict[str, Any]:
    """Construit le snapshot intangible (P4) — research §8."""
    now = datetime.now(tz=UTC).isoformat()
    entreprise = (
        db.execute(
            text(
                """
                SELECT id, raison_sociale, secteur, taille
                FROM entreprise
                WHERE account_id = CAST(:aid AS UUID)
                  AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"aid": str(account_id)},
        )
        .mappings()
        .first()
    )
    projet = (
        db.execute(
            text(
                "SELECT id, titre, description FROM projet "
                "WHERE id = CAST(:pid AS UUID)"
            ),
            {"pid": str(row["projet_id"])},
        )
        .mappings()
        .first()
    )
    offre = (
        db.execute(
            text(
                "SELECT id, nom, type, montant_min, montant_max, documents_requis "
                "FROM offre WHERE id = CAST(:oid AS UUID)"
            ),
            {"oid": str(row["offre_id"])},
        )
        .mappings()
        .first()
    )
    docs = (
        db.execute(
            text(
                """
                SELECT d.id AS document_id, d.fingerprint_sha256
                FROM document_link_projet dlp
                JOIN document_entreprise d ON d.id = dlp.document_id
                WHERE dlp.account_id = CAST(:aid AS UUID)
                  AND dlp.projet_id = CAST(:pid AS UUID)
                  AND d.deleted_at IS NULL
                """
            ),
            {"aid": str(account_id), "pid": str(row["projet_id"])},
        )
        .mappings()
        .all()
    )
    step3 = draft.get("step3") if isinstance(draft, dict) else None
    checklist_map: dict[str, str] = {}
    if isinstance(step3, dict):
        for link in step3.get("documents_links") or []:
            if isinstance(link, dict) and link.get("document_id") and link.get("checklist_key"):
                checklist_map[str(link["document_id"])] = str(link["checklist_key"])
    return {
        "schema_version": "1",
        "submitted_at": now,
        "entreprise": dict(entreprise) if entreprise else {},
        "projet": dict(projet) if projet else {"id": str(row["projet_id"])},
        "offre": dict(offre) if offre else {"id": str(row["offre_id"])},
        "skills_used": [],
        "indicateurs_valid_from_to": [],
        "draft_payload": draft if isinstance(draft, dict) else {},
        "documents": [
            {
                "document_id": str(d["document_id"]),
                "fingerprint_sha256": d.get("fingerprint_sha256"),
                "checklist_key": checklist_map.get(str(d["document_id"])),
            }
            for d in docs
        ],
    }


def submit_with_snapshot(
    db: Session,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID | None,
    candidature_id: uuid.UUID,
    expected_version: int,
    confirmed: bool,
    user_acknowledged_intangible: bool,
) -> dict[str, Any]:
    """POST /submit : fige le snapshot, statut→soumise, audit submitted_at."""
    if not confirmed or not user_acknowledged_intangible:
        raise ConfirmationRequiredError("confirmation_required")

    row = _fetch_candidature(db, candidature_id=candidature_id, account_id=account_id)

    if row["submitted_at"] is not None:
        raise AlreadySubmittedError("already_submitted")

    if int(row["version"]) != int(expected_version):
        cur_draft = row["draft_snapshot_json"] or {}
        raise VersionConflictError(
            current_version=int(row["version"]),
            current_draft=cur_draft if isinstance(cur_draft, dict) else {},
        )

    step_courant = int(row["step_courant"] or 1)
    progression = int(row["progression_pct"] or 0)
    draft = row["draft_snapshot_json"] or {}
    if step_courant < 5 or progression < 100:
        missing: list[str] = []
        if step_courant < 5:
            missing.append("wizard_not_completed")
        if progression < 100:
            missing.append("progression_below_100")
        raise IncompleteDossierError(missing)

    snapshot = _build_submitted_snapshot(
        db, row=row, draft=draft if isinstance(draft, dict) else {}, account_id=account_id
    )
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    import json as _json

    old_statut = row["statut"]
    db.execute(
        text(
            """
            UPDATE candidature
            SET submitted_at = :ts,
                snapshot_json = CAST(:snap AS JSONB),
                statut = 'soumise',
                version = version + 1,
                updated_at = :ts
            WHERE id = CAST(:cid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            """
        ),
        {
            "ts": now,
            "snap": _json.dumps(snapshot, default=str),
            "cid": str(candidature_id),
            "aid": str(account_id),
        },
    )

    try:
        record_audit(
            db,
            entity_type="candidature",
            entity_id=candidature_id,
            field="submitted_at",
            old=None,
            new=now.isoformat(),
            source_of_change=SourceOfChange.MANUAL,
            user_id=str(user_id) if user_id else None,
            account_id=str(account_id),
        )
        if old_statut != "soumise":
            record_audit(
                db,
                entity_type="candidature",
                entity_id=candidature_id,
                field="statut",
                old=old_statut,
                new="soumise",
                source_of_change=SourceOfChange.MANUAL,
                user_id=str(user_id) if user_id else None,
                account_id=str(account_id),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("candidature: audit submit failed: %s", exc)

    refreshed = (
        db.execute(
            text(
                "SELECT id, statut, submitted_at, version "
                "FROM candidature WHERE id = CAST(:cid AS UUID)"
            ),
            {"cid": str(candidature_id)},
        )
        .mappings()
        .first()
    )
    assert refreshed is not None
    return {
        "id": refreshed["id"],
        "statut": refreshed["statut"],
        "submitted_at": refreshed["submitted_at"],
        "snapshot_schema_version": "1",
        "version": int(refreshed["version"]),
    }
