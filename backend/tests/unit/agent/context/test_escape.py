"""F54 / T013 — Tests unitaires escape (FR-013).

Couvre :
- Échappement {} pour neutraliser f-strings/Jinja templates injectés.
- Troncature à MAX_FIELD_LEN avec ellipsis.
- Pipeline ``clean_user_str`` : None → '', cap longueur, escape combinés.
"""

from __future__ import annotations

import pytest

from app.agent.context.escape import (
    MAX_FIELD_LEN,
    clean_user_str,
    escape_template_chars,
    truncate_field,
)


@pytest.mark.unit
class TestEscapeTemplateChars:
    """``{`` → ``{{`` et ``}`` → ``}}`` pour neutraliser f-string/Jinja."""

    def test_escapes_single_braces(self) -> None:
        assert escape_template_chars("Hello {world}") == "Hello {{world}}"

    def test_escapes_already_doubled_braces(self) -> None:
        # On reste idempotent pour la sécurité défensive : tout ``{`` est doublé.
        assert escape_template_chars("{{ trouble }}") == "{{{{ trouble }}}}"

    def test_passthrough_no_braces(self) -> None:
        assert escape_template_chars("Hello world") == "Hello world"

    def test_empty_string(self) -> None:
        assert escape_template_chars("") == ""

    def test_jinja_like_payload(self) -> None:
        evil = "{% if user %}<script>{{ user.password }}</script>{% endif %}"
        out = escape_template_chars(evil)
        # Tous les ``{`` doivent avoir été doublés : le nombre de ``{`` est
        # nécessairement pair (chaque original devient ``{{``) et inversement
        # pour ``}``. Aucune occurrence isolée n'est acceptable.
        assert out.count("{") == 2 * evil.count("{")
        assert out.count("}") == 2 * evil.count("}")


@pytest.mark.unit
class TestTruncateField:
    """``truncate_field`` coupe à ``max_len`` et ajoute ``…`` (ellipsis)."""

    def test_passthrough_under_limit(self) -> None:
        assert truncate_field("hi", max_len=10) == "hi"

    def test_at_exact_limit(self) -> None:
        s = "a" * 10
        assert truncate_field(s, max_len=10) == s

    def test_above_limit(self) -> None:
        s = "a" * 600
        out = truncate_field(s, max_len=500)
        assert len(out) <= 500
        assert out.endswith("…")

    def test_default_max_len_is_500(self) -> None:
        assert MAX_FIELD_LEN == 500
        s = "a" * 1000
        out = truncate_field(s)
        assert len(out) <= 500
        assert out.endswith("…")


@pytest.mark.unit
class TestCleanUserStr:
    """Pipeline complet : None → '', escape, truncate."""

    def test_none_becomes_empty_string(self) -> None:
        assert clean_user_str(None) == ""

    def test_pipeline_escape_then_truncate(self) -> None:
        evil = "{nasty}" + "x" * 1000
        out = clean_user_str(evil, max_len=20)
        # ``{nasty}`` → ``{{nasty}}`` puis tronqué.
        assert out.startswith("{{nasty}}")
        assert len(out) <= 20

    def test_string_with_braces_short(self) -> None:
        assert clean_user_str("Forme: {SARL}") == "Forme: {{SARL}}"

    def test_empty_string_stays_empty(self) -> None:
        assert clean_user_str("") == ""

    def test_typical_pme_field(self) -> None:
        out = clean_user_str("SARL Boulangerie Sankoré")
        assert out == "SARL Boulangerie Sankoré"
