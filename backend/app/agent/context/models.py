"""F54 / FR-003 — Modèles Pydantic immutables du contexte agent.

Toutes les entités sont :
- ``frozen=True`` (immutables, P8 — la DB est la source de vérité, pas
  l'objet en mémoire).
- ``extra='forbid'`` (rejet strict des champs inattendus, P9).

Toute valeur monétaire est typée :class:`Money`
(``{amount: Decimal, currency: ISO 4217}``) — jamais ``float`` (P5).

Les UUID, dates, statuts utilisent des types forts. Le ``schema_version``
permet d'invalider le cache au boot après un déploiement avec changement
structurel des dataclasses.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.agent.context.money_format import Money

#: Bumper à chaque changement structurel des dataclasses → invalide caches.
SCHEMA_VERSION: int = 1

_FROZEN_STRICT = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class EntrepriseSummary(BaseModel):
    """Résumé du profil entreprise (P8 — lecture seule au moment du tour)."""

    model_config = _FROZEN_STRICT

    account_id: UUID
    raison_sociale: str  # déjà cleaned (FR-013)
    forme_juridique: str | None = None
    secteur_naf: str | None = None
    secteur_label: str | None = None
    taille: Literal["TPE", "PE", "ME", "GE"] | None = None
    effectif: int | None = None
    pays: str = "CI"  # ISO 3166-1 alpha-2 — défaut Côte d'Ivoire.
    devise_principale: str = "XOF"  # ISO 4217.
    ca_dernier_exercice: Money | None = None
    gouvernance_resume: str | None = None  # cleaned + tronqué.


class ProjetSummary(BaseModel):
    model_config = _FROZEN_STRICT

    id: UUID
    titre: str  # cleaned.
    description_courte: str | None = None  # cleaned + tronqué.
    montant_demande: Money | None = None
    statut: str  # ex. "brouillon", "en_analyse", "finance", "archive"
    date_creation: datetime
    date_archivage: datetime | None = None


class CandidatureSummary(BaseModel):
    model_config = _FROZEN_STRICT

    id: UUID
    projet_id: UUID
    offre_id: UUID
    intermediaire_label: str | None = None  # cleaned.
    statut: str  # ex. "brouillon", "soumise", "en_instruction", "acceptee"
    score: int | None = Field(default=None, ge=0, le=100)
    date_soumission: datetime | None = None


class IndicateurSummary(BaseModel):
    """Pivot ESG (P6) — reste sous forme :class:`Indicateur` : la vue par axe
    E/S/G est générée à la volée par le builder, jamais stockée."""

    model_config = _FROZEN_STRICT

    id: UUID
    code: str  # ex. "GHG_SCOPE1_2"
    libelle: str  # cleaned.
    axe: Literal["E", "S", "G"]
    valeur: Decimal
    unite: str  # "tCO2e", "%", "FCFA"…
    source_id: UUID | None = None  # P1 — null seulement pour valeur déclarative.
    date_calcul: datetime
    referentiel_code: str | None = None


class ScoreCreditSummary(BaseModel):
    model_config = _FROZEN_STRICT

    scoring_id: UUID
    gauge: int = Field(ge=0, le=100)
    sub_scores: dict[str, int] = Field(default_factory=dict)
    date_calcul: datetime
    lacunes_principales: list[str] = Field(default_factory=list)


class PlanActionStepSummary(BaseModel):
    model_config = _FROZEN_STRICT

    id: UUID
    titre: str  # cleaned.
    statut: str  # ex. "todo", "doing", "done", "blocked"
    echeance: date | None = None


# ---------------------------------------------------------------------------
# Aggregated entities
# ---------------------------------------------------------------------------


class BusinessContext(BaseModel):
    """Contexte porteur d'une PME au moment du tour (FR-003).

    Cardinalités cap (FR-002) appliquées par le loader :

    - ``projets_actifs`` : 10 max.
    - ``candidatures_en_cours`` : 10 max.
    - ``indicateurs_recents`` : 30 max (tri date desc, tous axes).
    - ``plan_action_steps`` : 5 max (en_cours en priorité).
    """

    model_config = _FROZEN_STRICT

    account_id: UUID
    user_id: UUID
    user_role: Literal["pme", "admin"]
    loaded_at: datetime
    schema_version: int = SCHEMA_VERSION

    entreprise: EntrepriseSummary | None = None
    projets_actifs: list[ProjetSummary] = Field(default_factory=list)
    candidatures_en_cours: list[CandidatureSummary] = Field(default_factory=list)
    indicateurs_recents: list[IndicateurSummary] = Field(default_factory=list)
    score_credit: ScoreCreditSummary | None = None
    plan_action_steps: list[PlanActionStepSummary] = Field(default_factory=list)


class EnrichedPageContext(BaseModel):
    """Contexte de la page courante consultée par l'utilisateur (FR-002)."""

    model_config = _FROZEN_STRICT

    page: str  # URL ou route ex. ``/projet/<id>``
    entity_type: Literal["Projet", "Candidature", "Indicateur", "Scoring"] | None = None
    entity_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    related: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Render (intermediate, mutable for builder convenience)
# ---------------------------------------------------------------------------


class SkillRender(BaseModel):
    model_config = _FROZEN_STRICT

    code: str
    version: str = "v1"
    procedure_short: str = ""


class ToolRender(BaseModel):
    model_config = _FROZEN_STRICT

    name: str
    use_when: str = ""
    dont_use_when: str | None = None
    schema_summary: str = ""


class ChatMsgRender(BaseModel):
    model_config = _FROZEN_STRICT

    role: Literal["user", "assistant", "tool", "system"]
    content: str
    timestamp: datetime | None = None


class BusinessContextRender(BaseModel):
    model_config = _FROZEN_STRICT

    text: str
    indicateurs_par_axe: dict[str, list[str]] = Field(default_factory=dict)


class PageContextRender(BaseModel):
    model_config = _FROZEN_STRICT

    text: str


class PromptParts(BaseModel):
    """Structure intermédiaire avant troncature (FR-006).

    Les blocs ``identity`` et ``invariants`` ne doivent **jamais** être
    tronqués. Les autres sont coupés selon la stratégie ordonnée.
    """

    model_config = _FROZEN_STRICT

    identity: str  # bloc identité ESG Mefali — IMMUTABLE.
    invariants: str  # bloc 10 invariants — IMMUTABLE.
    skills: list[SkillRender] = Field(default_factory=list)
    tools: list[ToolRender] = Field(default_factory=list)
    business_ctx: BusinessContextRender
    page_ctx: PageContextRender
    decision_tree: str = ""
    metadata: str = ""
    recent_messages: list[ChatMsgRender] = Field(default_factory=list)
    sheet_result_note: str | None = None
    admin_banner: str | None = None


_TRUNCATION_REASONS = Literal[
    "indicateurs_old",
    "projets_archived",
    "candidatures_closed",
    "tools_dont_use_when",
    "sources_verbatim",
    "skills_secondary",
    "messages_oldest",
]


class TruncationReport(BaseModel):
    """Observabilité de la troncature (FR-010)."""

    model_config = _FROZEN_STRICT

    budget: int
    tokens_before: int
    tokens_after: int
    warning_emitted: bool = False
    parts_truncated: list[_TRUNCATION_REASONS] = Field(default_factory=list)
    steps_applied: list[str] = Field(default_factory=list)


__all__ = [
    "SCHEMA_VERSION",
    "BusinessContext",
    "BusinessContextRender",
    "CandidatureSummary",
    "ChatMsgRender",
    "EnrichedPageContext",
    "EntrepriseSummary",
    "IndicateurSummary",
    "Money",
    "PageContextRender",
    "PlanActionStepSummary",
    "ProjetSummary",
    "PromptParts",
    "ScoreCreditSummary",
    "SkillRender",
    "ToolRender",
    "TruncationReport",
]
