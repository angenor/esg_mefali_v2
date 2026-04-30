"""F33 - Tests unitaires url_matcher (purs, pas de DB)."""

from __future__ import annotations

import pytest

from app.extension.url_matcher import compile_pattern, match_url


class TestWildcard:
    def test_simple_wildcard_matches_subdomain(self) -> None:
        assert match_url("https://www.boad.org/appels", "*boad.org/*", "wildcard")

    def test_wildcard_does_not_match_other_domain(self) -> None:
        assert not match_url("https://example.com/x", "*boad.org/*", "wildcard")

    def test_wildcard_case_insensitive(self) -> None:
        assert match_url("https://WWW.BOAD.ORG/x", "*boad.org/*", "wildcard")

    def test_empty_url_returns_false(self) -> None:
        assert not match_url("", "*boad.org/*", "wildcard")


class TestRegex:
    def test_regex_anchor(self) -> None:
        assert match_url(
            "https://gcf.org/funding/abc",
            r"^https://gcf\.org/funding/.*$",
            "regex",
        )

    def test_regex_no_match(self) -> None:
        assert not match_url(
            "https://other.com/funding",
            r"^https://gcf\.org/funding/.*$",
            "regex",
        )

    def test_invalid_regex_returns_false(self) -> None:
        assert not match_url("https://x.com", "(unclosed", "regex")


class TestCompilePatternValidation:
    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError):
            compile_pattern("*", "bogus")

    def test_empty_pattern_raises(self) -> None:
        with pytest.raises(ValueError):
            compile_pattern("", "wildcard")

    def test_caching(self) -> None:
        p1 = compile_pattern("*test*", "wildcard")
        p2 = compile_pattern("*test*", "wildcard")
        assert p1 is p2
