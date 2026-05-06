# Python Interfaces — F54

Signatures publiques exposées par F54 et consommables par F55–F58.

## `app.agent.context.loader`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.context.models import BusinessContext, EnrichedPageContext

async def load_business_context(
    account_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    *,
    use_cache: bool = True,
) -> BusinessContext:
    """
    Charge le contexte porteur d'une PME (entreprise + projets + candidatures
    + indicateurs récents + score crédit + plan d'action en cours).

    Cardinalités cap (FR-002) :
    - projets_actifs : 10 max
    - candidatures_en_cours : 10 max
    - indicateurs_recents : 30 max (tri date desc, tous axes)
    - plan_action_steps : 5 max

    Cache LRU+TTL hybride (FR-007). Invalide via EventBus push.
    Tous les RDBMS hits filtrent par account_id (RLS strict, P2).

    Performance: < 200 ms p95 cold, < 50 ms p95 hot.
    """
    ...


async def load_page_context(
    page_ctx_dict: dict,             # ContextJson reçu du frontend
    account_id: UUID,
    db: AsyncSession,
) -> EnrichedPageContext:
    """
    Enrichit le contexte de page selon entity_type.
    - "Projet": projet + documents + candidatures du projet
    - "Candidature": candidature + offre + intermédiaire + critères
    - "Indicateur": indicateur + sources + référentiel actif
    - "Scoring": scoring le plus récent + lacunes
    - None: contexte minimal (data={}).

    Filtre RLS par account_id (404 cross-tenant).
    """
    ...
```

## `app.agent.context.cache`

```python
from uuid import UUID
from app.agent.context.models import BusinessContext

class BusinessContextCache:
    """
    LRU+TTL cache process-local. Subscribes to EventBus events:
      - company_profile_updated, projet_*, candidature_*, indicateur_*,
        score_credit_calculated, plan_action_step_updated
    Invalide l'entrée account_id correspondante.
    """

    def __init__(self, *, maxsize: int = 512, ttl_seconds: int = 60) -> None: ...

    async def get(self, account_id: UUID, schema_version: int) -> BusinessContext | None: ...
    async def set(self, ctx: BusinessContext) -> None: ...
    async def invalidate(self, account_id: UUID) -> None: ...
    async def clear(self) -> None: ...
```

## `app.agent.context.tokens`

```python
def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """
    Compte les tokens via tiktoken si encoding disponible,
    sinon fallback heuristique len(text) / 4 (conservateur).
    """
    ...
```

## `app.agent.context.truncation`

```python
from app.agent.context.models import PromptParts, TruncationReport

def truncate_prompt(
    parts: PromptParts,
    *,
    budget: int = 4000,
    hard_limit: int = 6000,
    encoding: str = "cl100k_base",
) -> tuple[str, TruncationReport]:
    """
    Applique la stratégie de troncature ordonnée (US5):
    1. 5 indicateurs récents par axe E/S/G
    2. Retirer projets archivés / candidatures cloturées
    3. Couper dont_use_when des tools
    4. Couper sources verbatim
    5. Skills cap à 3
    6. Messages oldest cap à 8

    Renvoie (prompt_str, report).
    """
    ...
```

## `app.agent.context.escape`

```python
MAX_FIELD_LEN: int = 500

def escape_template_chars(s: str) -> str:
    """Replace { with {{ and } with }} to prevent f-string/Jinja injection."""
    ...

def truncate_field(s: str, max_len: int = MAX_FIELD_LEN) -> str:
    """Trunque + ajoute …"""
    ...

def clean_user_str(s: str | None, max_len: int = MAX_FIELD_LEN) -> str:
    """Pipeline: escape + truncate. None → ''. """
    ...
```

## `app.agent.prompts.invariants`

```python
PROMPT_VERSION: str = "2026.05"
INVARIANTS_TEMPLATE: str  # contenu figé, snapshot test SC-008
IDENTITY_BLOCK: str       # bloc d'identité ESG Mefali (figé)
```

## `app.agent.prompt_builder`

```python
from app.agent.context.models import (
    BusinessContext, EnrichedPageContext, PromptParts, TruncationReport,
)

def build_prompt_parts(
    *,
    business_ctx: BusinessContext,
    page_ctx: EnrichedPageContext,
    active_skills: list,            # list[Skill] de F19
    available_tools: list,          # list[ToolDef] de F14/F55
    recent_messages: list,          # list[ChatMessage] de F18
    sheet_result: dict | None,      # FR-017
    user_role: str,                 # "pme" | "admin"
    metadata: dict,                 # {date, devise_pme, langue}
) -> PromptParts:
    """Assemble les blocs sans tronquer."""
    ...

def build_system_prompt(
    *,
    business_ctx: BusinessContext,
    page_ctx: EnrichedPageContext,
    active_skills: list,
    available_tools: list,
    recent_messages: list,
    sheet_result: dict | None,
    user_role: str,
    metadata: dict,
    budget_tokens: int = 4000,
    encoding: str = "cl100k_base",
) -> tuple[str, TruncationReport]:
    """
    Pipeline complet:
      build_parts → count_tokens → truncate_if_needed → return (str, report).
    """
    ...
```

## Repository extension

```python
# app/agent/repository.py — ajout
async def persist_prompt_hash(
    db: AsyncSession,
    *,
    run_id: UUID,
    system_prompt_hash: str,        # SHA-256 hex (64 chars)
    prompt_version: str,            # ex. "2026.05"
    prompt_full: str | None = None, # stocké uniquement si status='error' (RGPD)
) -> None:
    ...
```

## Notes pour features dépendantes

- F55 (dispatch): consomme `BusinessContext` lecture seule pour résoudre les FK rapidement.
- F56 (sourcing): consomme `IndicateurSummary.source_id` pour valider P1.
- F57 (memory): F54 fournit les 15 derniers messages ; F57 ajoute le RAG au-delà.
- F58 (guardrails/eval): consomme `prompt_version` + `system_prompt_hash` pour reproduire les évaluations.
