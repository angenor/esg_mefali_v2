"""F54 — alter agent_run : ajout system_prompt_hash + prompt_version (FR-015).

Cette migration ALTER ajoute deux colonnes nullable à la table
``agent_run`` créée par F53. Aucune donnée existante n'est altérée ni
supprimée — pure addition idempotente.

- ``system_prompt_hash CHAR(64) NULL`` : SHA-256 hex du system prompt utilisé
  pour ce tour. Renseigné par le runner LangGraph en fin de tour.
- ``prompt_version VARCHAR(16) NULL`` : alignement avec ``PROMPT_VERSION``
  (ex. ``"2026.05"``). Permet la rejouabilité (US7).

Index : aucun nouvel index nécessaire (lookup uniquement par run_id, déjà PK).

Cf. :doc:`specs/054-agent-context-builder/data-model.md` section AgentRun.

Revision ID: 0033_f54_alter_agent_run_prompt_hash
Revises: 0032_f53_agent_run_steps
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_f54_alter_agent_run_prompt_hash"
down_revision: str | None = "0032_f53_agent_run_steps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajout des colonnes nullable system_prompt_hash + prompt_version."""
    # CHAR(64) pour SHA-256 hex (64 hex chars exactement).
    op.add_column(
        "agent_run",
        sa.Column("system_prompt_hash", sa.CHAR(length=64), nullable=True),
    )
    op.add_column(
        "agent_run",
        sa.Column("prompt_version", sa.String(length=16), nullable=True),
    )

    # CHECK CONSTRAINT : si présent, doit être 64 chars hex.
    op.execute(
        """
        ALTER TABLE agent_run
        ADD CONSTRAINT agent_run_prompt_hash_format
        CHECK (
            system_prompt_hash IS NULL
            OR system_prompt_hash ~ '^[0-9a-f]{64}$'
        )
        """
    )


def downgrade() -> None:
    """Drop des colonnes (rollback safe — pas de perte de données métier)."""
    op.execute(
        "ALTER TABLE agent_run DROP CONSTRAINT IF EXISTS agent_run_prompt_hash_format"
    )
    op.drop_column("agent_run", "prompt_version")
    op.drop_column("agent_run", "system_prompt_hash")
