# Phase 1 — Data Model: F58 Agent Guardrails

**Date**: 2026-05-06 | **Migration**: `0037_f58_guardrails.py`

## Résumé

F58 ajoute :
1. **1 nouvelle table** `agent_tool_status` (kill-switch admin global, sans RLS).
2. **3 colonnes ALTER `account`** (sous-quotas tokens).
3. **6 colonnes ALTER `agent_run`** (flags guardrails).
4. **1 colonne ALTER `agent_run_step`** (flow conversation/ocr_analysis).
5. **3 index** pour performance dashboard.

Aucune table métier business → P2 RLS non-applicable sur la table `agent_tool_status`
(globale, accès admin uniquement, retour 404 pour non-admin).

## Entités

### AgentToolStatus (nouvelle table)

| Colonne | Type SQL | Contraintes | Description |
|---|---|---|---|
| `tool_name` | VARCHAR(100) | PK | Nom canonique du tool agent (ex. `create_project`, `cite_source`) |
| `enabled` | BOOLEAN | NOT NULL DEFAULT TRUE | État d'activation |
| `disabled_at` | TIMESTAMP WITH TIME ZONE | NULL | Quand désactivé (NULL si actif) |
| `disabled_by` | UUID | NULL, FK → `account_user.id` | Quel admin a désactivé |
| `reason` | TEXT | NULL | Raison de désactivation (ex. « consume too many tokens ») |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL DEFAULT NOW() | |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL DEFAULT NOW() | Trigger ON UPDATE |

**Indexes**:
- PK `tool_name` (cluster).
- Pas d'index supplémentaire (table très petite, ~30 rows max).

**RLS**: désactivée (table globale). Accès gated au niveau endpoint admin via
`require_admin` decorator. Les non-admin reçoivent 404 (P2 convention).

**Audit**: les mutations (disable/enable) sont journalisées via le système F53/F55
existant dans `audit_log` avec `entity = 'agent_tool_status'`,
`source_of_change = 'admin'`.

**Lifecycle**:
- État initial : aucune ligne (= tous les tools enabled par défaut, vérification
  fallback dans le sélecteur).
- `POST /admin/agent/tools/{name}/disable` → INSERT ou UPDATE avec
  `enabled = false`.
- `POST /admin/agent/tools/{name}/enable` → UPDATE avec `enabled = true`,
  `disabled_at = NULL`.
- `GET /admin/agent/tools` → SELECT * + tools connus du registry, hydrate état.

### Account (extension)

3 nouvelles colonnes ajoutées par migration 0037 :

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| `daily_token_quota` | INTEGER | NOT NULL DEFAULT 50000 | Quota total agrégé /jour |
| `daily_conversation_quota` | INTEGER | NOT NULL DEFAULT 30000 | Sous-quota flow `conversation` |
| `daily_ocr_analysis_quota` | INTEGER | NOT NULL DEFAULT 20000 | Sous-quota flow `ocr_analysis` |

**Contraintes** :
- CHECK `daily_conversation_quota + daily_ocr_analysis_quota <= daily_token_quota`
  (cohérence sous-quotas vs total).
- Toutes paramétrables par admin selon plan d'abonnement.

**Migration** : ALTER TABLE `account` ADD COLUMN ... ; valeurs par défaut
appliquées immédiatement à toutes les lignes existantes.

**Audit** : modifications via admin → journalisées (F53 audit existant).

### AgentRun (extension)

6 nouvelles colonnes ajoutées par migration 0037 :

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| `injection_detected` | BOOLEAN | NOT NULL DEFAULT FALSE | True si US1 a détecté un pattern d'injection |
| `pii_masked_count` | INTEGER | NOT NULL DEFAULT 0 | Nombre d'occurrences PII masquées dans les traces (US2) |
| `language_corrected` | BOOLEAN | NOT NULL DEFAULT FALSE | True si retry FR appliqué (US3) |
| `loop_detected` | BOOLEAN | NOT NULL DEFAULT FALSE | True si boucle détectée et tour stoppé (US7) |
| `circuit_breaker_open` | BOOLEAN | NOT NULL DEFAULT FALSE | True si fallback retourné (US5) |
| `mode` | VARCHAR(20) | NOT NULL DEFAULT 'langgraph' | Mode actif : `langgraph` \| `raw` \| `minimal` (CHECK) |

**Contraintes** :
- CHECK `mode IN ('langgraph', 'raw', 'minimal')`.

**Indexes nouveaux** :
- `idx_agent_run_metrics` : `(account_id, started_at, injection_detected)` — pour dashboard sécurité.
- `idx_agent_run_mode` : `(mode, started_at)` — pour analyse mode minimal.

**Immutabilité** : ces flags sont écrits une seule fois lors de l'écriture du
run (pas de UPDATE post-hoc), conformément à P3.

### AgentRunStep (extension)

1 nouvelle colonne ajoutée par migration 0037 :

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| `flow` | VARCHAR(20) | NOT NULL DEFAULT 'conversation' | `conversation` \| `ocr_analysis` (CHECK) |

**Contrainte** : CHECK `flow IN ('conversation', 'ocr_analysis')`.

**Index nouveau** :
- `idx_agent_run_step_token_acct` : `(account_id, ts, flow)` — pour agrégation
  rapide compteurs tokens (R7 cache 60s).

**Backfill** : valeurs existantes (pré-F58) restent à `'conversation'` (default)
— forward-only (clarification Q4).

## Entités en mémoire (non persistées)

Ces structures sont retournées par les fonctions guardrails et utilisées dans le
graph LangGraph mais ne touchent pas la DB.

### InjectionFinding

```python
@dataclass(frozen=True)
class InjectionFinding:
    category: Literal['ignore_previous', 'role_hijack', 'system_leak', 'jailbreak']
    matched_pattern: str           # ex. "ignore previous"
    severity: Literal['low', 'medium', 'high']
    position: int                  # offset dans le message original
```

### BudgetResult

```python
@dataclass(frozen=True)
class BudgetResult:
    allowed: bool
    flow: Literal['conversation', 'ocr_analysis']
    requested_tokens: int
    remaining_conversation_tokens: int
    remaining_ocr_analysis_tokens: int
    reason: str | None  # NULL si allowed=True ; sinon raison FR ("quota conversation atteint")
```

### CircuitState

```python
@dataclass
class CircuitState:
    service: str                      # ex. "llm_openrouter"
    state: Literal['closed', 'open', 'half_open']
    error_count: int
    error_window: deque[datetime]     # rolling window N derniers timestamps d'erreur
    opened_at: datetime | None
```

### LoopDetectionResult

```python
@dataclass(frozen=True)
class LoopDetectionResult:
    triggered: bool
    reason: Literal['none', 'too_many_calls', 'identical_args_3x']
    last_tool_name: str | None
    last_args_hash: str | None        # SHA256 des args
```

## Flow de masquage PII

```mermaid
flowchart TD
    A[user message arrive] --> B[mask_pii(user_message)]
    B --> C[copie masquée → trace agent_run.user_message_masked]
    A --> D[message original passé au LLM]
    D --> E[LLM réponse]
    E --> F[mask_pii(llm_response)]
    F --> G[copie masquée → trace agent_run.llm_response_masked + tool_call_log]
    E --> H[message intact retourné à l'utilisateur final]
```

**Garantie** : aucune mutation in-place ; `mask_pii()` retourne toujours une
nouvelle string. Le compteur `pii_masked_count` est incrémenté à chaque
substitution effectuée.

## Migration `0037_f58_guardrails.py` — squelette

```python
"""F58 — Agent guardrails (tool kill-switch + token quotas + run flags + step flow).

Revision ID: 0037
Revises: 0036
Create Date: 2026-05-06 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0037'
down_revision = '0036'

def upgrade() -> None:
    # 1) Table agent_tool_status (no RLS — global admin-managed)
    op.create_table(
        'agent_tool_status',
        sa.Column('tool_name', sa.String(100), primary_key=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disabled_by', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['disabled_by'], ['account_user.id'], ondelete='SET NULL'),
    )
    # 2) account: 3 sous-quotas
    op.add_column('account', sa.Column('daily_token_quota', sa.Integer, nullable=False, server_default='50000'))
    op.add_column('account', sa.Column('daily_conversation_quota', sa.Integer, nullable=False, server_default='30000'))
    op.add_column('account', sa.Column('daily_ocr_analysis_quota', sa.Integer, nullable=False, server_default='20000'))
    op.create_check_constraint(
        'ck_account_quota_sum',
        'account',
        'daily_conversation_quota + daily_ocr_analysis_quota <= daily_token_quota',
    )
    # 3) agent_run: 6 flags guardrails
    op.add_column('agent_run', sa.Column('injection_detected', sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column('agent_run', sa.Column('pii_masked_count', sa.Integer, nullable=False, server_default='0'))
    op.add_column('agent_run', sa.Column('language_corrected', sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column('agent_run', sa.Column('loop_detected', sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column('agent_run', sa.Column('circuit_breaker_open', sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column('agent_run', sa.Column('mode', sa.String(20), nullable=False, server_default='langgraph'))
    op.create_check_constraint(
        'ck_agent_run_mode',
        'agent_run',
        "mode IN ('langgraph', 'raw', 'minimal')",
    )
    op.create_index('idx_agent_run_metrics', 'agent_run', ['account_id', 'started_at', 'injection_detected'])
    op.create_index('idx_agent_run_mode', 'agent_run', ['mode', 'started_at'])
    # 4) agent_run_step: flow
    op.add_column('agent_run_step', sa.Column('flow', sa.String(20), nullable=False, server_default='conversation'))
    op.create_check_constraint(
        'ck_agent_run_step_flow',
        'agent_run_step',
        "flow IN ('conversation', 'ocr_analysis')",
    )
    op.create_index('idx_agent_run_step_token_acct', 'agent_run_step', ['account_id', 'ts', 'flow'])

def downgrade() -> None:
    op.drop_index('idx_agent_run_step_token_acct', table_name='agent_run_step')
    op.drop_constraint('ck_agent_run_step_flow', 'agent_run_step')
    op.drop_column('agent_run_step', 'flow')
    op.drop_index('idx_agent_run_mode', table_name='agent_run')
    op.drop_index('idx_agent_run_metrics', table_name='agent_run')
    op.drop_constraint('ck_agent_run_mode', 'agent_run')
    for c in ('mode', 'circuit_breaker_open', 'loop_detected', 'language_corrected', 'pii_masked_count', 'injection_detected'):
        op.drop_column('agent_run', c)
    op.drop_constraint('ck_account_quota_sum', 'account')
    for c in ('daily_ocr_analysis_quota', 'daily_conversation_quota', 'daily_token_quota'):
        op.drop_column('account', c)
    op.drop_table('agent_tool_status')
```

## Validation

- ✅ Pas de nouvelle table métier sans `account_id` qui violerait P2 (la table
  `agent_tool_status` est volontairement globale, justifiée admin-only).
- ✅ Append-only sur `agent_run.*` flags (P3).
- ✅ Index alignés avec les requêtes attendues du dashboard admin.
- ✅ Forward-only (Q4) : pas de backfill obligatoire ; defaults appliqués.
- ✅ Reversible (downgrade fourni).
