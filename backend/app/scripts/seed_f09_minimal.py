"""F09 T100 — Seed minimal F09.

Crée 1 source ``verified``, 2 indicateurs publiés, 1 référentiel ``transverse``
attaché à ces 2 indicateurs avec poids 60/40 (somme = 100), 1 facteur d'émission
mondial publié pour ``ELEC``.

Usage : ``python -m app.scripts.seed_f09_minimal``
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import text

from app.db import SessionLocal


def _ensure_admin(db) -> str:
    row = db.execute(
        text("SELECT id FROM account_user WHERE role='admin' ORDER BY created_at LIMIT 1")
    ).first()
    if row:
        return str(row[0])
    raise RuntimeError("No admin user found. Run scripts/seed_admin first.")


def _ensure_source(db, *, admin_id: str) -> str:
    row = db.execute(
        text("SELECT id FROM source WHERE title = 'F09 seed source' LIMIT 1")
    ).first()
    if row:
        return str(row[0])
    sid = str(uuid.uuid4())
    emb = "[" + ",".join("0.0" for _ in range(1024)) + "]"
    db.execute(
        text(
            """
            INSERT INTO source
              (id, url, title, publisher, captured_at, captured_by,
               verified_by, verified_at, embedding,
               verification_status, status_version)
            VALUES
              (CAST(:id AS UUID), :url, :title, :pub,
               :now, CAST(:cap AS UUID), CAST(:cap AS UUID), :now,
               CAST(:emb AS vector), 'verified', 1)
            """
        ),
        {
            "id": sid,
            "url": "https://example.com/f09-seed",
            "title": "F09 seed source",
            "pub": "Mefali",
            "now": datetime.now(tz=UTC),
            "cap": admin_id,
            "emb": emb,
        },
    )
    return sid


def _ensure_indicateur(
    db, *, code: str, name: str, pillar: str, source_id: str, admin_id: str
) -> str:
    existing = db.execute(
        text("SELECT id FROM indicateur WHERE code = :c"), {"c": code}
    ).first()
    if existing:
        return str(existing[0])
    iid = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO indicateur (id, code, name, definition, pillar, unite, "
            "value_type, status, version, created_by) "
            "VALUES (CAST(:id AS UUID), :c, :n, '', :p, 'unit', 'numeric', "
            "'published', 1, CAST(:by AS UUID))"
        ),
        {"id": iid, "c": code, "n": name, "p": pillar, "by": admin_id},
    )
    db.execute(
        text(
            "INSERT INTO indicateur_source(indicateur_id, source_id) "
            "VALUES (CAST(:i AS UUID), CAST(:s AS UUID))"
        ),
        {"i": iid, "s": source_id},
    )
    return iid


def _ensure_referentiel(
    db,
    *,
    code: str,
    name: str,
    indicateurs: list[tuple[str, float]],
    source_id: str,
    admin_id: str,
) -> str:
    existing = db.execute(
        text("SELECT id FROM referentiel WHERE code = :c"), {"c": code}
    ).first()
    if existing:
        return str(existing[0])
    rid = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO referentiel (id, code, name, publisher, type, formula_type, "
            "version, status, created_by) "
            "VALUES (CAST(:id AS UUID), :c, :n, 'Mefali', 'transverse', "
            "'weighted_sum', 1, 'published', CAST(:by AS UUID))"
        ),
        {"id": rid, "c": code, "n": name, "by": admin_id},
    )
    db.execute(
        text(
            "INSERT INTO referentiel_source(referentiel_id, source_id) "
            "VALUES (CAST(:r AS UUID), CAST(:s AS UUID))"
        ),
        {"r": rid, "s": source_id},
    )
    for ind_id, poids in indicateurs:
        db.execute(
            text(
                "INSERT INTO referentiel_indicateur"
                "(referentiel_id, indicateur_id, poids, source_id) "
                "VALUES (CAST(:r AS UUID), CAST(:i AS UUID), :p, CAST(:s AS UUID))"
            ),
            {"r": rid, "i": ind_id, "p": poids, "s": source_id},
        )
    return rid


def _ensure_facteur(db, *, code: str, source_id: str, admin_id: str) -> str:
    existing = db.execute(
        text("SELECT id FROM facteur_emission WHERE code = :c"), {"c": code}
    ).first()
    if existing:
        return str(existing[0])
    fid = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO facteur_emission (id, code, name, valeur, unite, pays_iso2, "
            "scope, categorie, source_id, version, valid_from_date, status, created_by) "
            "VALUES (CAST(:id AS UUID), :c, 'World electricity mix', 0.40, "
            "'kgCO2e/kWh', NULL, '2', 'energie', CAST(:s AS UUID), 1, "
            ":vf, 'published', CAST(:by AS UUID))"
        ),
        {"id": fid, "c": code, "s": source_id, "vf": date(2024, 1, 1), "by": admin_id},
    )
    return fid


def main() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        admin_id = _ensure_admin(db)
        source_id = _ensure_source(db, admin_id=admin_id)
        i1 = _ensure_indicateur(
            db, code="GHG_SCOPE1", name="GHG Scope 1",
            pillar="E", source_id=source_id, admin_id=admin_id,
        )
        i2 = _ensure_indicateur(
            db, code="WATER_USE", name="Water use",
            pillar="E", source_id=source_id, admin_id=admin_id,
        )
        ref_id = _ensure_referentiel(
            db,
            code="ESG_BASE",
            name="ESG Base",
            indicateurs=[(i1, 60.0), (i2, 40.0)],
            source_id=source_id,
            admin_id=admin_id,
        )
        fact_id = _ensure_facteur(db, code="ELEC", source_id=source_id, admin_id=admin_id)
        db.commit()
        print(f"Seed OK : referentiel={ref_id}, facteur={fact_id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
