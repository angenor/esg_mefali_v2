"""F09 — Smoke imports : modèles SQLAlchemy F09."""

from __future__ import annotations


def test_models_import():
    from app.models.critere import Critere
    from app.models.document_requis import DocumentRequis
    from app.models.facteur_emission import FacteurEmission
    from app.models.indicateur import Indicateur
    from app.models.referentiel import Referentiel
    from app.models.referentiel_indicateur import ReferentielIndicateur

    # Tablename sanity check.
    assert Indicateur.__tablename__ == "indicateur"
    assert Referentiel.__tablename__ == "referentiel"
    assert ReferentielIndicateur.__tablename__ == "referentiel_indicateur"
    assert Critere.__tablename__ == "critere"
    assert DocumentRequis.__tablename__ == "document_requis"
    assert FacteurEmission.__tablename__ == "facteur_emission"


def test_schemas_strict():
    import pytest

    from app.catalog.indicateurs.schemas import IndicateurCreate

    # extra="forbid" should reject unknown keys.
    with pytest.raises(Exception):  # noqa: B017
        IndicateurCreate(
            code="OK",
            name="N",
            pillar="E",
            unite="kg",
            value_type="numeric",
            unknown_field=42,
        )


def test_referentiel_validator_module_imports():
    from decimal import Decimal

    from app.catalog.referentiels.validator import (
        POIDS_TOTAL_TARGET,
        POIDS_TOTAL_TOL,
    )

    assert POIDS_TOTAL_TARGET == Decimal("100")
    assert POIDS_TOTAL_TOL == Decimal("0.01")


def test_facteur_lookup_imports():
    from app.catalog.facteurs_emission.lookup import get_facteur

    assert callable(get_facteur)


def test_referentiel_helper_get_referentiel_imports():
    from app.catalog.referentiels.service import get_referentiel

    assert callable(get_referentiel)
