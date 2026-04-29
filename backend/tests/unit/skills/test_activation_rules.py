"""Tests F19 — règles d'activation."""

from __future__ import annotations

import pytest

from app.skills.activation_rules import (
    ActivationRules,
    Match,
    matches_context,
    parse_rules,
)


def test_empty_rules_never_match() -> None:
    rules = ActivationRules()
    assert matches_context(rules, {"page": "/x", "intent": "analyse"}) is False


def test_page_glob_match() -> None:
    rules = ActivationRules(any_of=[Match(page="/profil/projets/*")])
    assert matches_context(rules, {"page": "/profil/projets/abc"}) is True
    assert matches_context(rules, {"page": "/autre"}) is False


def test_intent_match() -> None:
    rules = ActivationRules(any_of=[Match(intent=["analyse", "mutation"])])
    assert matches_context(rules, {"intent": "analyse"}) is True
    assert matches_context(rules, {"intent": "navigation"}) is False


def test_combined_rule_requires_all_fields() -> None:
    rules = ActivationRules(
        any_of=[Match(page="/profil/projets/*", intent=["analyse"])]
    )
    ctx_ok = {"page": "/profil/projets/42", "intent": "analyse"}
    ctx_bad = {"page": "/profil/projets/42", "intent": "mutation"}
    assert matches_context(rules, ctx_ok) is True
    assert matches_context(rules, ctx_bad) is False


def test_offre_match() -> None:
    rules = ActivationRules(
        any_of=[
            Match(
                entity_type="candidature",
                offre_id_match={"fonds_code": "GCF", "intermediaire_code": "BOAD"},
            )
        ]
    )
    ctx = {
        "entity_type": "candidature",
        "offre": {"fonds_code": "GCF", "intermediaire_code": "BOAD"},
    }
    assert matches_context(rules, ctx) is True
    ctx_bad = {
        "entity_type": "candidature",
        "offre": {"fonds_code": "GEF", "intermediaire_code": "BOAD"},
    }
    assert matches_context(rules, ctx_bad) is False


def test_any_of_with_alternatives() -> None:
    rules = ActivationRules(
        any_of=[
            Match(page="/profil/projets/*"),
            Match(entity_type="candidature"),
        ]
    )
    assert matches_context(rules, {"page": "/profil/projets/x"}) is True
    assert matches_context(rules, {"entity_type": "candidature"}) is True
    assert matches_context(rules, {"page": "/random"}) is False


def test_parse_rules_handles_none_and_empty() -> None:
    assert parse_rules(None).any_of == []
    assert parse_rules({}).any_of == []


def test_parse_rules_validates_structure() -> None:
    parsed = parse_rules({"any_of": [{"page": "/a", "intent": ["analyse"]}]})
    assert len(parsed.any_of) == 1
    assert parsed.any_of[0].page == "/a"


def test_parse_rules_rejects_extra_fields() -> None:
    with pytest.raises(Exception):  # noqa: B017,PT011
        parse_rules({"any_of": [{"unknown_field": 1}]})
