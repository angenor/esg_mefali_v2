"""F01 — Initial schema (18 tables, multi-tenant prêt RLS, Money typé, pgvector).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-29

NOTES IMPORTANTES (T034) :
- Devise par défaut pour les seeds futures : XOF (FCFA).
- Peg fixe FCFA-EUR : 655,957 (UEMOA, à utiliser dans F27/F29).
- Cette migration prépare le multi-tenant mais n'active PAS RLS :
  * F02 activera ALTER TABLE ... ENABLE ROW LEVEL SECURITY et créera les
    politiques utilisant `current_setting('app.current_account_id')::uuid`.
  * F02 enforce aussi le CHECK sur `account_user.role IN ('pme','admin')`.
- F03 enforce `source_id NOT NULL` sur indicateur, critere, facteur_emission,
  document_requis, accreditation, template (laissé NULL en F01).
- F04 ajoute les triggers d'audit et révoque UPDATE/DELETE sur audit_log.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Helpers SQL réutilisés
COMMON_TIMESTAMPS = """
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
"""


def _money_check(prefix: str) -> str:
    """CHECK Money pour le couple <prefix>_amount / <prefix>_currency."""
    return (
        f"CHECK (({prefix}_amount IS NULL AND {prefix}_currency IS NULL) "
        f"OR ({prefix}_amount IS NOT NULL AND {prefix}_currency IS NOT NULL "
        f"AND char_length({prefix}_currency)=3))"
    )


def upgrade() -> None:
    # --- 1. Extensions Postgres ---
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # =========================================================
    # 2. CATALOGUE (sans account_id) — ordre FK
    # =========================================================

    # source
    op.execute(f"""
        CREATE TABLE source (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          url TEXT NULL,
          title TEXT NOT NULL,
          publisher TEXT NULL,
          version TEXT NULL,
          date_publi DATE NULL,
          page TEXT NULL,
          section TEXT NULL,
          captured_at TIMESTAMP NULL,
          captured_by UUID NULL,
          verified_by UUID NULL,
          verification_status TEXT NULL,
          created_by UUID NULL,
          {COMMON_TIMESTAMPS}
        )
    """)

    # account (racine multi-tenant)
    op.execute(f"""
        CREATE TABLE account (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          {COMMON_TIMESTAMPS}
        )
    """)

    # account_user (métier mais doit exister avant FK created_by partout)
    op.execute(f"""
        CREATE TABLE account_user (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NULL,
          role TEXT NULL,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)
    op.execute("CREATE INDEX ix_account_user_account_id ON account_user(account_id)")

    # Désormais on peut ajouter les FK created_by/captured_by/verified_by sur source
    op.execute(
        "ALTER TABLE source "
        "ADD CONSTRAINT fk_source_created_by FOREIGN KEY (created_by) REFERENCES account_user(id), "
        "ADD CONSTRAINT fk_source_captured_by FOREIGN KEY (captured_by) REFERENCES account_user(id), "
        "ADD CONSTRAINT fk_source_verified_by FOREIGN KEY (verified_by) REFERENCES account_user(id)"
    )

    # referentiel
    op.execute(f"""
        CREATE TABLE referentiel (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          version TEXT NOT NULL,
          valid_from DATE NULL,
          valid_to DATE NULL,
          status TEXT NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # indicateur
    op.execute(f"""
        CREATE TABLE indicateur (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          definition TEXT NULL,
          unite TEXT NULL,
          status TEXT NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # intermediaire
    op.execute(f"""
        CREATE TABLE intermediaire (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          type TEXT NULL,
          pays TEXT NULL,
          contact TEXT NULL,
          frais_json JSONB NULL,
          delais_json JSONB NULL,
          version INT NOT NULL DEFAULT 1,
          status TEXT NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # fonds_source
    op.execute(f"""
        CREATE TABLE fonds_source (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          organisation TEXT NULL,
          type TEXT NULL,
          thematique TEXT NULL,
          instruments TEXT[] NULL,
          plafond_amount NUMERIC(18,2) NULL,
          plafond_currency CHAR(3) NULL,
          plancher_amount NUMERIC(18,2) NULL,
          plancher_currency CHAR(3) NULL,
          eligibilite_geo TEXT[] NULL,
          submission_mode TEXT NULL,
          version INT NOT NULL DEFAULT 1,
          status TEXT NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          {_money_check("plafond")},
          {_money_check("plancher")}
        )
    """)

    # accreditation
    op.execute(f"""
        CREATE TABLE accreditation (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          intermediaire_id UUID NOT NULL REFERENCES intermediaire(id),
          fonds_id UUID NOT NULL REFERENCES fonds_source(id),
          date_debut DATE NULL,
          date_fin DATE NULL,
          plafond_amount NUMERIC(18,2) NULL,
          plafond_currency CHAR(3) NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          {_money_check("plafond")},
          UNIQUE (intermediaire_id, fonds_id, date_debut)
        )
    """)

    # offre
    op.execute(f"""
        CREATE TABLE offre (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          fonds_id UUID NOT NULL REFERENCES fonds_source(id),
          intermediaire_id UUID NULL REFERENCES intermediaire(id),
          accepted_languages TEXT[] NULL,
          version INT NOT NULL DEFAULT 1,
          status TEXT NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # critere (CHECK exclusif offre_id XOR referentiel_id)
    op.execute(f"""
        CREATE TABLE critere (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          offre_id UUID NULL REFERENCES offre(id),
          referentiel_id UUID NULL REFERENCES referentiel(id),
          expression_json JSONB NULL,
          indicateur_ids UUID[] NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          CHECK (
            (offre_id IS NOT NULL AND referentiel_id IS NULL)
            OR (offre_id IS NULL AND referentiel_id IS NOT NULL)
          )
        )
    """)

    # document_requis (CHECK : au moins un de fonds_id, intermediaire_id)
    op.execute(f"""
        CREATE TABLE document_requis (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          fonds_id UUID NULL REFERENCES fonds_source(id),
          intermediaire_id UUID NULL REFERENCES intermediaire(id),
          name TEXT NOT NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          CHECK (fonds_id IS NOT NULL OR intermediaire_id IS NOT NULL)
        )
    """)

    # facteur_emission
    op.execute(f"""
        CREATE TABLE facteur_emission (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          valeur NUMERIC(18,6) NOT NULL,
          unite TEXT NOT NULL,
          pays TEXT NULL,
          source_id UUID NULL REFERENCES source(id),
          version INT NOT NULL DEFAULT 1,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # template
    op.execute(f"""
        CREATE TABLE template (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          offre_id UUID NOT NULL REFERENCES offre(id),
          name TEXT NOT NULL,
          structure_json JSONB NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)

    # =========================================================
    # 3. MÉTIER (avec account_id NOT NULL indexé)
    # =========================================================

    # entreprise
    op.execute(f"""
        CREATE TABLE entreprise (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          name TEXT NOT NULL,
          secteur TEXT NULL,
          taille_ca_amount NUMERIC(18,2) NULL,
          taille_ca_currency CHAR(3) NULL,
          taille_effectifs INT NULL,
          localisation TEXT NULL,
          gouvernance TEXT NULL,
          pratiques_actuelles_json JSONB NULL,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          {_money_check("taille_ca")}
        )
    """)
    op.execute("CREATE INDEX ix_entreprise_account_id ON entreprise(account_id)")

    # projet
    op.execute(f"""
        CREATE TABLE projet (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NOT NULL REFERENCES entreprise(id),
          nom TEXT NOT NULL,
          description TEXT NULL,
          type_impact TEXT NULL,
          maturite TEXT NULL,
          montant_recherche_amount NUMERIC(18,2) NULL,
          montant_recherche_currency CHAR(3) NULL,
          structure_financement TEXT NULL,
          indicateurs_impact_json JSONB NULL,
          localisation TEXT NULL,
          statut TEXT NULL,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS},
          {_money_check("montant_recherche")}
        )
    """)
    op.execute("CREATE INDEX ix_projet_account_id ON projet(account_id)")

    # candidature
    op.execute(f"""
        CREATE TABLE candidature (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          projet_id UUID NOT NULL REFERENCES projet(id),
          offre_id UUID NOT NULL REFERENCES offre(id),
          statut TEXT NULL,
          snapshot_json JSONB NULL,
          soumission_at TIMESTAMP NULL,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_by UUID NULL REFERENCES account_user(id),
          {COMMON_TIMESTAMPS}
        )
    """)
    op.execute("CREATE INDEX ix_candidature_account_id ON candidature(account_id)")

    # chat_message (avec embedding vector(1024))
    op.execute(f"""
        CREATE TABLE chat_message (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          user_id UUID NULL REFERENCES account_user(id),
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          payload_json JSONB NULL,
          embedding vector(1024) NULL,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          {COMMON_TIMESTAMPS}
        )
    """)
    op.execute("CREATE INDEX ix_chat_message_account_id ON chat_message(account_id)")

    # audit_log (append-only — pas de updated_at, pas de deleted_at)
    op.execute("""
        CREATE TABLE audit_log (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NULL REFERENCES account_user(id),
          account_id UUID NULL REFERENCES account(id),
          timestamp TIMESTAMP NOT NULL DEFAULT now(),
          entity_type TEXT NOT NULL,
          entity_id UUID NOT NULL,
          field TEXT NULL,
          old_value JSONB NULL,
          new_value JSONB NULL,
          source_of_change TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          version INT NOT NULL DEFAULT 1,
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CONSTRAINT chk_audit_source CHECK (source_of_change IN ('manual','llm','import','admin'))
        )
    """)
    # NB : updated_at présent pour cohérence des tests "common columns".
    # En F04, on révoquera UPDATE/DELETE et triggers d'audit assureront append-only.
    op.execute("CREATE INDEX ix_audit_log_account_id ON audit_log(account_id)")
    op.execute("CREATE INDEX ix_audit_log_timestamp ON audit_log(timestamp)")
    op.execute("CREATE INDEX ix_audit_log_entity_type ON audit_log(entity_type)")
    op.execute("CREATE INDEX ix_audit_log_entity_id ON audit_log(entity_id)")


def downgrade() -> None:
    # Ordre INVERSE des CREATE pour respecter les FK
    for tbl in [
        "audit_log",
        "chat_message",
        "candidature",
        "projet",
        "entreprise",
        "template",
        "facteur_emission",
        "document_requis",
        "critere",
        "offre",
        "accreditation",
        "fonds_source",
        "intermediaire",
        "indicateur",
        "referentiel",
        "account_user",
        "account",
        "source",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")

    # Les extensions pgcrypto et vector NE SONT PAS supprimées (partagées).
