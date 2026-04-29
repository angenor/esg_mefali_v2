"""Tests du classifier d'intention F14 (US2) — règles déterministes MVP."""

from __future__ import annotations

import pytest

from app.orchestrator.intent_classifier import classify, clear_cache


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    clear_cache()
    yield
    clear_cache()


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Ajoute un projet d'agroforesterie", "mutation"),
        ("supprime ce projet", "mutation"),
        ("Modifie mon profil", "mutation"),
        ("compare ma performance ESG aux pairs", "analyse"),
        ("Analyse mon profil", "analyse"),
        ("Aide moi", "aide"),
        ("Comment ça marche ?", "aide"),
        ("Oui", "question_fermee"),
        ("Non merci", "question_fermee"),
        ("Va à la page profil", "navigation"),
        ("Mon profil personnel", "profilage"),
        ("Texte aléatoire sans intention", "autre"),
    ],
)
def test_rule_based_classification(message: str, expected: str) -> None:
    assert classify(message) == expected


def test_cache_isolation_across_threads() -> None:
    classify("ajoute un projet", thread_id="t1")
    assert classify("texte vide", thread_id="t2") == "autre"


def test_cache_persists_when_no_rule_matches_after_first_hit() -> None:
    classify("ajoute X", thread_id="t3")
    result = classify("blah", thread_id="t3")
    assert result == "mutation"
