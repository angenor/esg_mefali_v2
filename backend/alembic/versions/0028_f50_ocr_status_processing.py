"""F50 — élargit ``chk_document_entreprise_ocr_status`` pour inclure ``processing``.

Le service ``relaunch_ocr`` et le composable frontend ``useOcrPolling`` utilisent
la valeur ``processing`` comme état intermédiaire, mais la migration F22 0015
ne l'avait pas listée dans le CHECK CONSTRAINT. Un document ne pouvait donc
jamais être effectivement marqué ``processing``, rendant le 409 ``ocr_in_progress``
inatteignable. Cette migration recharge le CHECK avec la liste complète.

Revision ID: 0028_f50_ocr_status_processing
Revises: 0027_f50_document_tags
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0028_f50_ocr_status_processing"
down_revision: str | None = "0027_f50_document_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE document_entreprise "
        "DROP CONSTRAINT IF EXISTS chk_document_entreprise_ocr_status"
    )
    op.execute(
        "ALTER TABLE document_entreprise "
        "ADD CONSTRAINT chk_document_entreprise_ocr_status "
        "CHECK (ocr_status IN ('pending', 'processing', 'done', 'deferred', 'failed'))"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE document_entreprise "
        "DROP CONSTRAINT IF EXISTS chk_document_entreprise_ocr_status"
    )
    op.execute(
        "ALTER TABLE document_entreprise "
        "ADD CONSTRAINT chk_document_entreprise_ocr_status "
        "CHECK (ocr_status IN ('pending', 'done', 'deferred', 'failed'))"
    )
