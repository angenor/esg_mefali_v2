"""F51 — Wizard candidature + simulation_savee.

Ajoute :
- colonnes sur ``candidature`` :
    * step_courant SMALLINT NOT NULL DEFAULT 1 (∈ [1..5])
    * progression_pct SMALLINT NOT NULL DEFAULT 0 (∈ [0..100])
    * draft_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb
  Note : ``snapshot_json`` (existant — F01/F04) reste l'unique colonne
  immuable post-submit, déjà protégée par ``candidature_snapshot_guard``.
  Cette migration **étend** le guard pour figer également
  ``draft_snapshot_json`` après ``submitted_at IS NOT NULL``.
- index partiels :
    * idx_candidature_drafts (account_id, updated_at DESC) WHERE statut='brouillon'
    * idx_candidature_submitted (account_id, submitted_at DESC) WHERE submitted_at NOT NULL
- table ``simulation_savee`` (historique simulateur) avec RLS tenant_isolation.

Revision ID: 0029_f51_wizard_and_simulation_savee
Revises: 0028_f50_ocr_status_processing
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029_f51_wizard_and_simulation_savee"
down_revision: str | None = "0028_f50_ocr_status_processing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Colonnes additionnelles sur candidature.
    op.execute(
        """
        ALTER TABLE candidature
            ADD COLUMN IF NOT EXISTS step_courant SMALLINT NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS progression_pct SMALLINT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS draft_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )

    # 2. CHECK constraints (idempotents — drop puis recreate).
    op.execute(
        "ALTER TABLE candidature DROP CONSTRAINT IF EXISTS chk_candidature_step_courant"
    )
    op.execute(
        """
        ALTER TABLE candidature
            ADD CONSTRAINT chk_candidature_step_courant
            CHECK (step_courant BETWEEN 1 AND 5)
        """
    )
    op.execute(
        "ALTER TABLE candidature DROP CONSTRAINT IF EXISTS chk_candidature_progression_pct"
    )
    op.execute(
        """
        ALTER TABLE candidature
            ADD CONSTRAINT chk_candidature_progression_pct
            CHECK (progression_pct BETWEEN 0 AND 100)
        """
    )

    # 3. Étendre le guard existant pour également figer draft_snapshot_json post-submit.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION candidature_snapshot_guard()
        RETURNS trigger AS $body$
        BEGIN
            -- Une candidature est considérée soumise dès que
            -- (snapshot_json IS NOT NULL AND submitted_at IS NOT NULL).
            -- Dans ce cas, snapshot_json, submitted_at, et draft_snapshot_json
            -- sont immuables (P4 + SC-008 + F51 SC-004).
            IF OLD.snapshot_json IS NOT NULL AND OLD.submitted_at IS NOT NULL THEN
                IF NEW.snapshot_json IS DISTINCT FROM OLD.snapshot_json THEN
                    RAISE EXCEPTION
                        'snapshot_json is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                    RAISE EXCEPTION
                        'submitted_at is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.draft_snapshot_json IS DISTINCT FROM OLD.draft_snapshot_json THEN
                    RAISE EXCEPTION
                        'draft_snapshot_json is frozen after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
    # Le trigger est déjà installé en 0004 ; pas besoin de DROP/CREATE.

    # 4. Index partiels pour la performance des listings.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_candidature_drafts
            ON candidature(account_id, updated_at DESC)
            WHERE statut = 'brouillon'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_candidature_submitted
            ON candidature(account_id, submitted_at DESC)
            WHERE submitted_at IS NOT NULL
        """
    )

    # 5. Table simulation_savee.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_savee (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id      UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id         UUID NOT NULL REFERENCES account_user(id),
            label           VARCHAR(120) NOT NULL,
            projet_id       UUID NULL REFERENCES projet(id) ON DELETE SET NULL,
            offre_id        UUID NULL REFERENCES offre(id) ON DELETE SET NULL,
            hypotheses_json JSONB NOT NULL,
            results_json    JSONB NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ NULL,
            version         INT NOT NULL DEFAULT 1,
            CONSTRAINT chk_simulation_savee_label_len
                CHECK (char_length(label) BETWEEN 1 AND 120)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_simulation_savee_account_recent
            ON simulation_savee(account_id, created_at DESC)
            WHERE deleted_at IS NULL
        """
    )

    # 6. RLS tenant_isolation sur simulation_savee.
    op.execute("ALTER TABLE simulation_savee ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON simulation_savee")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON simulation_savee
            USING (account_id = current_setting('app.current_account_id', true)::uuid)
            WITH CHECK (account_id = current_setting('app.current_account_id', true)::uuid)
        """
    )


def downgrade() -> None:
    # Rollback inverse : supprimer table simulation_savee + index + colonnes
    # candidature ajoutées. Le guard reste étendu mais inopérant pour
    # draft_snapshot_json (colonne disparue) — restaurer la version courte.
    op.execute("DROP TABLE IF EXISTS simulation_savee CASCADE")

    op.execute("DROP INDEX IF EXISTS idx_candidature_submitted")
    op.execute("DROP INDEX IF EXISTS idx_candidature_drafts")

    op.execute(
        "ALTER TABLE candidature DROP CONSTRAINT IF EXISTS chk_candidature_progression_pct"
    )
    op.execute(
        "ALTER TABLE candidature DROP CONSTRAINT IF EXISTS chk_candidature_step_courant"
    )
    op.execute(
        """
        ALTER TABLE candidature
            DROP COLUMN IF EXISTS draft_snapshot_json,
            DROP COLUMN IF EXISTS progression_pct,
            DROP COLUMN IF EXISTS step_courant
        """
    )

    # Restaurer le guard à sa forme F04 (sans la branche draft_snapshot_json).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION candidature_snapshot_guard()
        RETURNS trigger AS $body$
        BEGIN
            IF OLD.snapshot_json IS NOT NULL AND OLD.submitted_at IS NOT NULL THEN
                IF NEW.snapshot_json IS DISTINCT FROM OLD.snapshot_json THEN
                    RAISE EXCEPTION
                        'snapshot_json is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                    RAISE EXCEPTION
                        'submitted_at is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
