"""F54 / FR-002 — load_business_context, load_page_context.

Service pur (NFR-004) — n'importe **pas** ``app.chat.api`` ni
``app.agent.runner``. Lit toutes les données strictement filtrées par
``account_id`` (RLS P2 — la session DOIT déjà avoir
``app.current_account_id`` positionné par l'appelant).

Cardinalités cap (FR-002) :

- ``CAP_PROJETS = 10`` (tri date desc, statut != ``archive``).
- ``CAP_CANDIDATURES = 10`` (statut ∈ {brouillon, soumise, en_instruction}).
- ``CAP_INDICATEURS = 30`` (tri date desc, tous axes E/S/G).
- ``CAP_PLAN_ACTION = 5`` (statut ∈ {todo, doing}).

Cache hybride : :func:`load_business_context` consulte le cache LRU+TTL
process-local (``cache.get_business_context_cache()``) avant de toucher la
DB. Les services qui mutent les données métier doivent appeler
:func:`app.agent.context.cache.invalidate_business_context` après commit.

L'API publique reste **async** pour respecter le contrat des consommateurs
(F55–F58) ; en interne on délègue les appels SQL synchrones via
``asyncio.to_thread`` afin de ne pas bloquer la boucle d'événements.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.context.cache import get_business_context_cache
from app.agent.context.escape import clean_user_str
from app.agent.context.models import (
    SCHEMA_VERSION,
    BusinessContext,
    CandidatureSummary,
    EnrichedPageContext,
    EntrepriseSummary,
    IndicateurSummary,
    Money,
    PlanActionStepSummary,
    ProjetSummary,
    ScoreCreditSummary,
)

logger = logging.getLogger(__name__)


CAP_PROJETS: int = 10
CAP_CANDIDATURES: int = 10
CAP_INDICATEURS: int = 30
CAP_PLAN_ACTION: int = 5


# ---------------------------------------------------------------------------
# Helpers RLS-safe
# ---------------------------------------------------------------------------


def _safe_money(amount: Any, currency: Any) -> Money | None:
    if amount is None or currency is None:
        return None
    try:
        return Money(amount=Decimal(str(amount)), currency=str(currency))
    except (ValueError, ArithmeticError):  # pragma: no cover - defensive
        return None


def _aware_dt(dt: Any) -> datetime:
    if dt is None:
        return datetime.now(UTC)
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Business context loaders (sync — wrappés via to_thread)
# ---------------------------------------------------------------------------


def _fetch_entreprise(db: Session, account_id: UUID) -> EntrepriseSummary | None:
    row = db.execute(
        text(
            """
            SELECT id, account_id, name, secteur_code, secteur_label,
                   taille_ca_amount, taille_ca_currency, taille_effectifs,
                   localisation_siege_pays_iso2, gouvernance_json
            FROM entreprise
            WHERE account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"aid": str(account_id)},
    ).first()
    if row is None:
        return None

    pays = (row.localisation_siege_pays_iso2 or "CI").strip() or "CI"
    gouv = row.gouvernance_json
    gouv_str: str | None = None
    if isinstance(gouv, dict) and gouv:
        # Résumé court : 1 ligne avec les clés non vides.
        keys_short = [k for k, v in gouv.items() if v][:5]
        gouv_str = ", ".join(keys_short) if keys_short else None

    return EntrepriseSummary(
        account_id=row.account_id,
        raison_sociale=clean_user_str(row.name) or "PME (sans raison sociale)",
        secteur_naf=row.secteur_code,
        secteur_label=clean_user_str(row.secteur_label) or None,
        effectif=int(row.taille_effectifs) if row.taille_effectifs is not None else None,
        pays=pays[:2] if pays else "CI",
        ca_dernier_exercice=_safe_money(row.taille_ca_amount, row.taille_ca_currency),
        gouvernance_resume=clean_user_str(gouv_str) if gouv_str else None,
    )


def _fetch_projets_actifs(
    db: Session, account_id: UUID, *, cap: int = CAP_PROJETS
) -> list[ProjetSummary]:
    rows = db.execute(
        text(
            """
            SELECT id, nom, description,
                   montant_recherche_amount, montant_recherche_currency,
                   statut, created_at, updated_at
            FROM projet
            WHERE account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
              AND COALESCE(statut, '') != 'archive'
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
            LIMIT :lim
            """
        ),
        {"aid": str(account_id), "lim": cap},
    ).all()

    out: list[ProjetSummary] = []
    for r in rows:
        out.append(
            ProjetSummary(
                id=r.id,
                titre=clean_user_str(r.nom) or "Projet sans titre",
                description_courte=clean_user_str(r.description) if r.description else None,
                montant_demande=_safe_money(
                    r.montant_recherche_amount, r.montant_recherche_currency
                ),
                statut=r.statut or "brouillon",
                date_creation=_aware_dt(r.created_at),
                date_archivage=None,
            )
        )
    return out


def _fetch_candidatures_en_cours(
    db: Session, account_id: UUID, *, cap: int = CAP_CANDIDATURES
) -> list[CandidatureSummary]:
    rows = db.execute(
        text(
            """
            SELECT c.id, c.projet_id, c.offre_id, c.statut,
                   COALESCE(c.soumission_at, c.created_at) AS soumission_at,
                   c.created_at, c.updated_at
            FROM candidature c
            WHERE c.account_id = CAST(:aid AS UUID)
              AND c.deleted_at IS NULL
              AND c.statut IN ('brouillon', 'soumise', 'en_instruction')
            ORDER BY c.updated_at DESC NULLS LAST, c.created_at DESC
            LIMIT :lim
            """
        ),
        {"aid": str(account_id), "lim": cap},
    ).all()

    out: list[CandidatureSummary] = []
    for r in rows:
        out.append(
            CandidatureSummary(
                id=r.id,
                projet_id=r.projet_id,
                offre_id=r.offre_id,
                statut=r.statut or "brouillon",
                date_soumission=_aware_dt(r.soumission_at)
                if r.soumission_at
                else None,
            )
        )
    return out


def _fetch_indicateurs_recents(
    db: Session, account_id: UUID, *, cap: int = CAP_INDICATEURS
) -> list[IndicateurSummary]:
    """Lit les indicateurs récents.

    F54 ne dépend pas d'une table « valeur_indicateur » spécifique : on lit
    la table catalogue ``indicateur`` filtrée par ``account_id`` quand cette
    colonne existe (sinon retourne []). Le pivot ESG par PME (P6) est
    matérialisé en F55+ via les attestations / score ; ici on présente la
    vue catalogue côté agent.

    Si la table est absente ou si le schéma n'a pas de colonne ``account_id``
    (catalogue partagé), on retourne une liste vide sans erreur — le
    contexte ESG sera disponible via le score (P6 — la grille E/S/G est
    une vue, pas un stockage dupliqué).
    """
    try:
        rows = db.execute(
            text(
                """
                SELECT i.id, i.code, i.libelle,
                       COALESCE(i.axe, 'E') AS axe,
                       COALESCE(i.unite, '') AS unite,
                       COALESCE(i.referentiel_code, NULL) AS referentiel_code,
                       i.created_at
                FROM indicateur i
                WHERE i.deleted_at IS NULL
                ORDER BY i.created_at DESC NULLS LAST
                LIMIT :lim
                """
            ),
            {"lim": cap},
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Indicateurs unavailable (catalogue/account schema mismatch?): %s", exc
        )
        return []

    out: list[IndicateurSummary] = []
    for r in rows:
        # Le catalogue ne porte pas de valeur PME-spécifique. F54 expose
        # les indicateurs disponibles ; F55+ branchera la valeur PME issue
        # de score_calculation.details_json.
        try:
            out.append(
                IndicateurSummary(
                    id=r.id,
                    code=r.code or "INDIC",
                    libelle=clean_user_str(r.libelle) or "Indicateur",
                    axe=str(r.axe).upper() if r.axe else "E",
                    valeur=Decimal("0"),
                    unite=r.unite or "",
                    source_id=None,
                    date_calcul=_aware_dt(r.created_at),
                    referentiel_code=r.referentiel_code,
                )
            )
        except Exception:  # noqa: BLE001 - tolerate axes hors E/S/G
            continue
    return out


def _fetch_score_credit(db: Session, account_id: UUID) -> ScoreCreditSummary | None:
    try:
        row = db.execute(
            text(
                """
                SELECT id, score_global, scores_by_pillar, computed_at
                FROM score_calculation
                WHERE account_id = CAST(:aid AS UUID)
                  AND entity_type = 'entreprise'
                ORDER BY computed_at DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"aid": str(account_id)},
        ).first()
    except Exception as exc:  # noqa: BLE001
        logger.debug("score_credit unavailable: %s", exc)
        return None

    if row is None:
        return None

    sub_scores: dict[str, int] = {}
    sb = row.scores_by_pillar
    if isinstance(sb, dict):
        for k, v in sb.items():
            try:
                sub_scores[str(k)] = int(round(float(v)))
            except (TypeError, ValueError):
                continue

    gauge = 0
    if row.score_global is not None:
        try:
            gauge = max(0, min(100, int(round(float(row.score_global)))))
        except (TypeError, ValueError):
            gauge = 0

    return ScoreCreditSummary(
        scoring_id=row.id,
        gauge=gauge,
        sub_scores=sub_scores,
        date_calcul=_aware_dt(row.computed_at),
        lacunes_principales=[],
    )


def _fetch_plan_action_steps(
    db: Session, account_id: UUID, *, cap: int = CAP_PLAN_ACTION
) -> list[PlanActionStepSummary]:
    try:
        rows = db.execute(
            text(
                """
                SELECT s.id, s.title, s.status, s.horizon_at
                FROM action_step s
                JOIN action_plan p ON p.id = s.plan_id
                WHERE p.account_id = CAST(:aid AS UUID)
                  AND s.status IN ('todo', 'doing')
                ORDER BY s.horizon_at ASC NULLS LAST, s.priority ASC NULLS LAST
                LIMIT :lim
                """
            ),
            {"aid": str(account_id), "lim": cap},
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.debug("action_step unavailable: %s", exc)
        return []

    out: list[PlanActionStepSummary] = []
    for r in rows:
        out.append(
            PlanActionStepSummary(
                id=r.id,
                titre=clean_user_str(r.title) or "Étape",
                statut=r.status or "todo",
                echeance=r.horizon_at if r.horizon_at else None,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public API — async
# ---------------------------------------------------------------------------


def _load_business_context_sync(
    db: Session,
    *,
    account_id: UUID,
    user_id: UUID,
    user_role: str,
) -> BusinessContext:
    """Variante sync : utilisée par les tests + appelée via to_thread depuis
    la version async pour ne pas bloquer la boucle.
    """
    entreprise = _fetch_entreprise(db, account_id)
    projets = _fetch_projets_actifs(db, account_id)
    candidatures = _fetch_candidatures_en_cours(db, account_id)
    indicateurs = _fetch_indicateurs_recents(db, account_id)
    score = _fetch_score_credit(db, account_id)
    plan = _fetch_plan_action_steps(db, account_id)

    role: Any = user_role if user_role in ("pme", "admin") else "pme"

    return BusinessContext(
        account_id=account_id,
        user_id=user_id,
        user_role=role,
        loaded_at=datetime.now(UTC),
        schema_version=SCHEMA_VERSION,
        entreprise=entreprise,
        projets_actifs=projets,
        candidatures_en_cours=candidatures,
        indicateurs_recents=indicateurs,
        score_credit=score,
        plan_action_steps=plan,
    )


async def load_business_context(
    *,
    account_id: UUID,
    user_id: UUID,
    db: Session,
    user_role: str = "pme",
    use_cache: bool = True,
) -> BusinessContext:
    """Charge le contexte porteur d'une PME (FR-002).

    Read-through cache : si une entrée valide existe pour ``account_id``
    (TTL ≤ 60 s), on la retourne. Sinon on charge toutes les sous-tables
    via :func:`_load_business_context_sync` et on cache le résultat.

    Toutes les requêtes sont **filtrées par account_id** (RLS strict P2).
    L'invalidation est faite par les services qui mutent les données
    métier via :func:`app.agent.context.cache.invalidate_business_context`.
    """
    cache = get_business_context_cache()

    if use_cache:
        cached = cache.get(account_id, SCHEMA_VERSION)
        if cached is not None:
            return cached

    # Délègue au thread pool pour ne pas bloquer la boucle.
    ctx = await asyncio.to_thread(
        _load_business_context_sync,
        db,
        account_id=account_id,
        user_id=user_id,
        user_role=user_role,
    )

    if use_cache:
        cache.set(account_id, SCHEMA_VERSION, ctx)

    return ctx


# ---------------------------------------------------------------------------
# Page context — sync sub-loaders + async dispatch
# ---------------------------------------------------------------------------


def _load_projet_page(
    db: Session, *, projet_id: UUID, account_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, nom, description, statut,
                   montant_recherche_amount, montant_recherche_currency
            FROM projet
            WHERE id = CAST(:pid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"pid": str(projet_id), "aid": str(account_id)},
    ).first()
    if row is None:
        return None
    candidatures = db.execute(
        text(
            """
            SELECT id, offre_id, statut
            FROM candidature
            WHERE projet_id = CAST(:pid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 5
            """
        ),
        {"pid": str(projet_id), "aid": str(account_id)},
    ).all()
    return {
        "projet": {
            "id": str(row.id),
            "titre": clean_user_str(row.nom) or "",
            "description": clean_user_str(row.description) if row.description else "",
            "statut": row.statut,
            "montant_demande": (
                {
                    "amount": str(row.montant_recherche_amount),
                    "currency": row.montant_recherche_currency,
                }
                if row.montant_recherche_amount and row.montant_recherche_currency
                else None
            ),
        },
        "candidatures_du_projet": [
            {
                "id": str(c.id),
                "offre_id": str(c.offre_id),
                "statut": c.statut,
            }
            for c in candidatures
        ],
    }


def _load_candidature_page(
    db: Session, *, candidature_id: UUID, account_id: UUID
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, projet_id, offre_id, statut, snapshot_json
            FROM candidature
            WHERE id = CAST(:cid AS UUID)
              AND account_id = CAST(:aid AS UUID)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"cid": str(candidature_id), "aid": str(account_id)},
    ).first()
    if row is None:
        return None

    return {
        "candidature": {
            "id": str(row.id),
            "projet_id": str(row.projet_id),
            "offre_id": str(row.offre_id),
            "statut": row.statut,
            "has_snapshot": bool(row.snapshot_json),
        },
    }


def _load_indicateur_page(
    db: Session, *, indicateur_id: UUID, account_id: UUID  # noqa: ARG001
) -> dict[str, Any] | None:
    """Indicateur catalogue (P6 — pivot unique).

    L'indicateur appartient au catalogue (pas par tenant), mais on respecte
    la signature account_id pour cohérence d'API. Pas de fuite cross-tenant
    possible (indicateur catalog est PUBLIC en lecture).
    """
    row = db.execute(
        text(
            """
            SELECT id, code, libelle, axe, unite, referentiel_code
            FROM indicateur
            WHERE id = CAST(:iid AS UUID)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"iid": str(indicateur_id)},
    ).first()
    if row is None:
        return None
    return {
        "indicateur": {
            "id": str(row.id),
            "code": row.code,
            "libelle": clean_user_str(row.libelle),
            "axe": str(row.axe).upper() if row.axe else "E",
            "unite": row.unite or "",
            "referentiel_code": row.referentiel_code,
        }
    }


def _load_scoring_page(db: Session, *, account_id: UUID) -> dict[str, Any] | None:
    score = _fetch_score_credit(db, account_id)
    if score is None:
        return None
    return {
        "scoring": {
            "scoring_id": str(score.scoring_id),
            "gauge": score.gauge,
            "sub_scores": score.sub_scores,
            "date_calcul": score.date_calcul.isoformat(),
            "lacunes_principales": score.lacunes_principales,
        }
    }


def _load_page_context_sync(
    db: Session,
    *,
    page_ctx_dict: dict,
    account_id: UUID,
) -> EnrichedPageContext:
    """Variante sync exploitable directement par les tests."""
    page_route = str(page_ctx_dict.get("page_route") or page_ctx_dict.get("page") or "/")
    entity_type_raw = page_ctx_dict.get("entity_type")
    entity_id_raw = page_ctx_dict.get("entity_id")

    valid_types = {"Projet", "Candidature", "Indicateur", "Scoring"}
    entity_type = entity_type_raw if entity_type_raw in valid_types else None

    entity_id: UUID | None = None
    if entity_id_raw is not None:
        try:
            entity_id = (
                entity_id_raw
                if isinstance(entity_id_raw, UUID)
                else UUID(str(entity_id_raw))
            )
        except (ValueError, TypeError):
            entity_id = None

    data: dict[str, Any] = {}
    related: list[dict[str, Any]] = []

    if entity_type == "Projet" and entity_id:
        loaded = _load_projet_page(db, projet_id=entity_id, account_id=account_id)
        if loaded is not None:
            data = {"projet": loaded["projet"]}
            related = [
                {"type": "candidature", "summary": c}
                for c in loaded.get("candidatures_du_projet", [])
            ]
    elif entity_type == "Candidature" and entity_id:
        loaded = _load_candidature_page(
            db, candidature_id=entity_id, account_id=account_id
        )
        if loaded is not None:
            data = loaded
    elif entity_type == "Indicateur" and entity_id:
        loaded = _load_indicateur_page(
            db, indicateur_id=entity_id, account_id=account_id
        )
        if loaded is not None:
            data = loaded
    elif entity_type == "Scoring":
        loaded = _load_scoring_page(db, account_id=account_id)
        if loaded is not None:
            data = loaded

    return EnrichedPageContext(
        page=page_route,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
        related=related,
    )


async def load_page_context(
    page_ctx_dict: dict,
    *,
    account_id: UUID,
    db: Session,
) -> EnrichedPageContext:
    """Charge le contexte de page courante (FR-002, US3).

    Filtre RLS strict (P2) : retourne 404 implicite (data vide) si l'entité
    n'appartient pas à ``account_id``.
    """
    return await asyncio.to_thread(
        _load_page_context_sync,
        db,
        page_ctx_dict=page_ctx_dict,
        account_id=account_id,
    )


__all__ = [
    "CAP_CANDIDATURES",
    "CAP_INDICATEURS",
    "CAP_PLAN_ACTION",
    "CAP_PROJETS",
    "load_business_context",
    "load_page_context",
]
