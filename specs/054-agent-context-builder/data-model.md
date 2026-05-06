# Phase 1 — Data Model

**Feature**: F54 Agent Context Builder
**Date**: 2026-05-06

Toutes les entités sont des dataclasses Pydantic v2 immutables (`model_config = ConfigDict(frozen=True, extra='forbid')`).

## Money (réutilisé)

Module commun `app.core.money.Money` (existant, P5).

```text
Money:
  amount: Decimal               # toujours positive ou zéro
  currency: str                 # ISO 4217 (XOF, EUR, USD, MAD, …)
```

## EntrepriseSummary

Sous-modèle inclus dans `BusinessContext`.

```text
EntrepriseSummary:
  account_id: UUID
  raison_sociale: str           # tronqué à MAX_FIELD_LEN=500 + escape (FR-013)
  forme_juridique: str | None   # SARL, SA, EI, GIE…
  secteur_naf: str | None       # ex. "C10.71"
  secteur_label: str | None     # libellé humain
  taille: Literal["TPE", "PE", "ME", "GE"] | None
  effectif: int | None
  pays: str                     # ISO 3166-1 alpha-2 (CI, SN, BF, …)
  devise_principale: str        # ISO 4217 — par défaut XOF
  ca_dernier_exercice: Money | None
  gouvernance_resume: str | None     # tronqué et escape
```

## ProjetSummary

```text
ProjetSummary:
  id: UUID
  titre: str
  description_courte: str | None     # tronqué et escape
  montant_demande: Money | None
  statut: Literal["draft", "en_analyse", "en_candidature", "finance", "archive"]
  date_creation: datetime
  date_archivage: datetime | None
```

## CandidatureSummary

```text
CandidatureSummary:
  id: UUID
  projet_id: UUID
  offre_id: UUID
  intermediaire_label: str | None
  statut: Literal["en_redaction", "soumise", "en_revue", "acceptee", "refusee", "cloturee"]
  score: int | None              # 0–100
  date_soumission: datetime | None
```

## IndicateurSummary

```text
IndicateurSummary:
  id: UUID
  code: str                     # ex. "GHG_SCOPE1_2"
  libelle: str
  axe: Literal["E", "S", "G"]
  valeur: Decimal
  unite: str                    # "tCO2e", "%", "FCFA", …
  source_id: UUID | None        # P1 — null seulement pour valeur déclarative non sourcée (à éviter)
  date_calcul: datetime
  referentiel_code: str | None  # ex. "GRI:305-1"
```

## ScoreCreditSummary

```text
ScoreCreditSummary:
  scoring_id: UUID
  gauge: int                   # 0–100
  sub_scores: dict[str, int]   # ex. {"financiere": 65, "esg": 62, "gouvernance": 70}
  date_calcul: datetime
  lacunes_principales: list[str]   # ex. ["gestion_dechets", "suivi_eau"] — max 5
```

## PlanActionStepSummary

```text
PlanActionStepSummary:
  id: UUID
  titre: str
  statut: Literal["en_cours", "a_faire", "termine", "bloque"]
  echeance: date | None
```

## BusinessContext

Entité agrégée principale (FR-003).

```text
BusinessContext:
  account_id: UUID
  user_id: UUID
  user_role: Literal["pme", "admin"]
  loaded_at: datetime
  schema_version: int           # bump si modèle change → invalide cache existant
  entreprise: EntrepriseSummary | None
  projets_actifs: list[ProjetSummary]            # cap 10 par FR-002
  candidatures_en_cours: list[CandidatureSummary] # cap 10 par FR-002
  indicateurs_recents: list[IndicateurSummary]   # cap 30 par FR-002, tri date desc
  score_credit: ScoreCreditSummary | None
  plan_action_steps: list[PlanActionStepSummary] # max 5 (en_cours en priorité)

Validation rules:
  - Tous les UUID + dates : type fort.
  - amount Money: Decimal positive ou zéro.
  - Si entreprise est None: cas "PME nouvelle, pas de profil renseigné".
  - schema_version: incrémentée à chaque migration de modèle (versionning cache).

Lifecycle:
  - Construit par load_business_context(account_id, user_id, db).
  - Caché par (account_id, schema_version).
  - Invalidé par EventBus push OR TTL 60s.
```

## EnrichedPageContext

Entité agrégée pour le contexte de page courante.

```text
EnrichedPageContext:
  page: str                    # URL ou route ex. "/projet/<id>"
  entity_type: Literal["Projet", "Candidature", "Indicateur", "Scoring", None]
  entity_id: UUID | None
  data: dict[str, Any]         # contenu spécifique au type, validé par sous-modèle
  related: list[dict[str, Any]] # sous-entités (documents, candidatures, sources…)

Variantes data selon entity_type:
  - "Projet": {projet: ProjetSummary, description_complete: str, documents: list, candidatures_du_projet: list[CandidatureSummary]}
  - "Candidature": {candidature: CandidatureSummary, offre: dict, intermediaire: dict, criteres: list[dict]}
  - "Indicateur": {indicateur: IndicateurSummary, sources: list[dict], referentiel: dict}
  - "Scoring": {scoring: ScoreCreditSummary, lacunes_detail: list[dict]}
  - None: data = {}, related = []

Validation rules:
  - entity_id obligatoire si entity_type != None.
  - account_id implicite (filtre RLS appliqué côté DB) — non re-stocké ici.
```

## PromptParts

Structure intermédiaire pour la troncature.

```text
PromptParts:
  identity: str                 # bloc d'identité ESG Mefali (FR-001) — JAMAIS tronqué
  invariants: str               # bloc 10 invariants — JAMAIS tronqué
  skills: list[SkillRender]     # skills actifs (F19) avec procedure
  tools: list[ToolRender]       # tools disponibles avec use_when, dont_use_when, schema résumé
  business_ctx: BusinessContextRender  # texte rendu du contexte porteur
  page_ctx: PageContextRender   # texte rendu du contexte de page
  decision_tree: str            # arbre de décision tools (généré depuis tools)
  metadata: str                 # date, devise PME, langue, PROMPT_VERSION
  recent_messages: list[ChatMsgRender]  # 15 derniers messages au format LangChain
  sheet_result_note: str | None # FR-017 — note "ne re-pose pas la question"
  admin_banner: str | None      # FR-018 — bandeau admin si user_role == "admin"

Sub-models:
  SkillRender: {code: str, version: str, procedure_short: str}
  ToolRender: {name: str, use_when: str, dont_use_when: str | None, schema_summary: str}
  BusinessContextRender: {text: str, indicateurs_par_axe: dict[str, list[str]]}
  PageContextRender: {text: str}
  ChatMsgRender: {role: str, content: str, timestamp: datetime}
```

## TruncationReport

Observabilité de la troncature.

```text
TruncationReport:
  budget: int                  # LLM_AGENT_PROMPT_BUDGET_TOKENS (4000 par défaut)
  tokens_before: int
  tokens_after: int
  warning_emitted: bool        # True si tokens_before > budget
  parts_truncated: list[Literal[
    "indicateurs_old",
    "projets_archived",
    "candidatures_closed",
    "tools_dont_use_when",
    "sources_verbatim",
    "skills_secondary",
    "messages_oldest"
  ]]
  steps_applied: list[str]      # ex. ["step1_indicateurs", "step2_projets_archived"]
```

## AgentRun (extension F53)

Migration ALTER ajoute deux colonnes.

```text
agent_run (existant F53) — colonnes ajoutées:
  + system_prompt_hash: VARCHAR(64) NULL    -- SHA-256 hex du prompt construit
  + prompt_version: VARCHAR(16) NULL        -- ex. "2026.05"

Index:
  -- aucun nouvel index nécessaire (lookup uniquement par run_id, déjà PK).

Migration: backend/alembic/versions/0XYY_alter_agent_run_prompt_hash.py
Type: ALTER TABLE ADD COLUMN (idempotent, rollback safe).
```

## Validation rules transverses

- Tous les `str` champs PME passent par `escape_template_chars` + `truncate_field(MAX_FIELD_LEN=500)` AVANT entrée dans dataclass (helper `clean_user_str`).
- Toute valeur monétaire est `Money | None` typé avec `Decimal` (jamais float, P5).
- Tous les UUID stockés en `UUID` (pas string).
- Le schema_version global est incrémenté manuellement à chaque modification structurelle des dataclasses → invalide cache.

## State transitions

Aucune entité de F54 ne porte d'état métier. Seuls `Projet.statut`, `Candidature.statut`, `PlanActionStep.statut` ont des transitions, mais elles sont gérées par F11/F12/F31 — F54 lit l'état courant.

## Diagramme de relations (logique)

```
BusinessContext (per account_id)
├── EntrepriseSummary          (1:1)
├── ProjetSummary[]            (cap 10)
│     └── CandidatureSummary[]  (chargées séparément, FK indirecte)
├── CandidatureSummary[]       (cap 10)
├── IndicateurSummary[]        (cap 30)
│     └── source_id            (référence Source — NON chargée par F54, juste l'id)
├── ScoreCreditSummary         (1:1, le plus récent)
└── PlanActionStepSummary[]    (max 5 en_cours)

EnrichedPageContext (per request)
├── data: dict[str, Any]       (variant selon entity_type)
└── related: list[dict]        (sous-entités contextuelles)

PromptParts (per turn, output of build_system_prompt)
└── consommé par count_tokens + truncate_prompt → string finale.
```
