"""F07 — Tests unitaires de la canonicalisation d'URL.

Spec :
- forcer https
- lower-case host
- retrait du préfixe www.
- retrait du slash final (sauf si la racine "/")
- retrait des params utm_*, fbclid, gclid, mc_cid, mc_eid
- conservation des fragments (#page=...)
- idempotence
"""

from __future__ import annotations

import pytest

from app.catalog.sources.canonicalize import canonicalize_url


@pytest.mark.unit
class TestCanonicalize:
    def test_force_https(self):
        assert canonicalize_url("http://example.com/foo") == "https://example.com/foo"

    def test_lowercase_host(self):
        assert canonicalize_url("https://Example.COM/Foo") == "https://example.com/Foo"

    def test_remove_www(self):
        assert canonicalize_url("https://www.example.com/foo") == "https://example.com/foo"

    def test_remove_trailing_slash(self):
        assert canonicalize_url("https://example.com/foo/") == "https://example.com/foo"

    def test_keep_root_slash(self):
        # Racine seule : on conserve "/" pour rester un URL valide
        assert canonicalize_url("https://example.com/") == "https://example.com/"

    def test_strip_utm(self):
        out = canonicalize_url(
            "https://example.com/p?utm_source=x&utm_medium=y&utm_campaign=z"
        )
        assert out == "https://example.com/p"

    def test_strip_tracking_ids(self):
        out = canonicalize_url(
            "https://example.com/p?fbclid=AAA&gclid=BBB&mc_cid=C&mc_eid=D"
        )
        assert out == "https://example.com/p"

    def test_keep_other_params(self):
        out = canonicalize_url("https://example.com/p?a=1&utm_source=x&b=2")
        # ordre conservé pour les params non-tracking
        assert out == "https://example.com/p?a=1&b=2"

    def test_keep_fragment(self):
        out = canonicalize_url("https://example.com/doc#page=42")
        assert out == "https://example.com/doc#page=42"

    def test_idempotent(self):
        once = canonicalize_url("http://WWW.Example.com/a/?utm_source=x#f")
        twice = canonicalize_url(once)
        assert once == twice
        assert once == "https://example.com/a#f"

    def test_combined(self):
        out = canonicalize_url(
            "HTTP://WWW.Example.COM/Path/?utm_source=x&q=1&fbclid=A#frag"
        )
        assert out == "https://example.com/Path?q=1#frag"

    def test_strips_whitespace(self):
        assert canonicalize_url("  https://example.com/x  ") == "https://example.com/x"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            canonicalize_url("not-a-url")
        with pytest.raises(ValueError):
            canonicalize_url("")
