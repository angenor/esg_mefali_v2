"""F18 — Index pgvector ivfflat sur chat_message.embedding (cosinus).

Ajoute (non destructif) un index ivfflat lists=100 sur la colonne
``chat_message.embedding`` pour permettre la recherche sémantique du tool
``recall_history``. L'opération est idempotente (``IF NOT EXISTS``) et
le rollback supprime simplement l'index.

Choix MVP : ivfflat avec ``lists = 100`` est adapté à < 100 000 messages.
HNSW reste une migration future post-MVP si le volume dépasse cette borne.

Revision ID: 0013_f18_chat_message_embedding_index
Revises: 0012_f12_projets_documents
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_f18_chat_message_embedding_index"
down_revision: str | None = "0012_f12_projets_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée l'index ivfflat cosinus sur ``chat_message.embedding``."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_message_embedding
          ON chat_message
          USING ivfflat (embedding vector_cosine_ops)
          WITH (lists = 100)
        """
    )
    # Aide le planificateur à exploiter le nouvel index sans attendre le
    # prochain autovacuum.
    op.execute("ANALYZE chat_message")


def downgrade() -> None:
    """Supprime l'index (rollback non destructif)."""
    op.execute("DROP INDEX IF EXISTS idx_chat_message_embedding")
