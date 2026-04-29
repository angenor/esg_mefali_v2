"""F18 — Tests unitaires des compacteurs purs."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.chat.memory.compactors import (
    DEFAULT_DESC_LIMIT,
    PROFILE_ALLOWED_KEYS,
    PROJECT_ACTIVE_DENYLIST,
    compact_profile,
    compact_projets,
    estimate_tokens,
    extract_embedding_text,
    fit_to_budget,
)

# --- compact_profile ----------------------------------------------------


class TestCompactProfile:
    def test_returns_none_when_empty(self) -> None:
        assert compact_profile(None) is None
        assert compact_profile({}) is None

    def test_keeps_only_whitelisted_keys(self) -> None:
        raw = {
            "raison_sociale": "Acme SARL",
            "secteur_activite": "Énergie",
            "password": "leak",
            "jwt": "token",
            "refresh_token": "secret",
            "email_dirigeant": "ceo@example.com",
            "internal_account_id": "uuid",
        }
        out = compact_profile(raw)
        assert out is not None
        assert "raison_sociale" in out
        assert "secteur_activite" in out
        for forbidden in (
            "password",
            "jwt",
            "refresh_token",
            "email_dirigeant",
            "internal_account_id",
        ):
            assert forbidden not in out

    def test_truncates_long_description(self) -> None:
        long_desc = "abc " * 200  # 800 chars
        out = compact_profile(
            {"raison_sociale": "X", "description_activite": long_desc}
        )
        assert out is not None
        assert len(out["description_activite"]) <= DEFAULT_DESC_LIMIT
        assert out["description_activite"].endswith("…")

    def test_excludes_empty_values(self) -> None:
        out = compact_profile(
            {"raison_sociale": "X", "secteur_activite": None, "ville": ""}
        )
        assert out is not None
        assert "secteur_activite" not in out
        assert "ville" not in out

    def test_preserves_money_typed_ca(self) -> None:
        out = compact_profile(
            {
                "raison_sociale": "X",
                "chiffre_affaires": {
                    "amount": Decimal("850000.00"),
                    "currency": "XOF",
                },
            }
        )
        assert out is not None
        assert out["chiffre_affaires"]["currency"] == "XOF"
        assert out["chiffre_affaires"]["amount"] == Decimal("850000.00")

    def test_whitelist_is_frozen(self) -> None:
        assert isinstance(PROFILE_ALLOWED_KEYS, frozenset)


# --- compact_projets ---------------------------------------------------


class TestCompactProjets:
    @staticmethod
    def _projet(**kwargs):
        base = {
            "id": "p-1",
            "nom": "Projet alpha",
            "statut": "actif",
            "secteur": "Agriculture",
            "description": "Petit projet agricole",
        }
        base.update(kwargs)
        return base

    def test_empty_input_returns_empty_list(self) -> None:
        assert compact_projets(None) == []
        assert compact_projets([]) == []

    def test_filters_out_inactive_statuses(self) -> None:
        projets = [
            self._projet(id="a", statut="actif"),
            self._projet(id="b", statut="cloture"),
            self._projet(id="c", statut="annule"),
            self._projet(id="d", statut="rejete"),
            self._projet(id="e", statut="en_cours"),
        ]
        out = compact_projets(projets)
        ids = [p["id"] for p in out]
        assert "a" in ids and "e" in ids
        for inactif in PROJECT_ACTIVE_DENYLIST:
            assert all(p.get("statut") != inactif for p in out)

    def test_caps_at_max_n(self) -> None:
        projets = [self._projet(id=f"p-{i}") for i in range(20)]
        out = compact_projets(projets, max_n=10)
        assert len(out) == 10

    def test_truncates_description(self) -> None:
        projets = [self._projet(description="x" * 1000)]
        out = compact_projets(projets, desc_limit=200)
        assert len(out) == 1
        assert len(out[0]["description"]) <= 200
        assert out[0]["description"].endswith("…")

    def test_preserves_money(self) -> None:
        projets = [
            self._projet(
                montant_total={"amount": Decimal("1500000"), "currency": "XOF"}
            )
        ]
        out = compact_projets(projets)
        assert out[0]["montant_total"]["currency"] == "XOF"


# --- extract_embedding_text -------------------------------------------


class TestExtractEmbeddingText:
    def test_plain_content_passthrough(self) -> None:
        assert extract_embedding_text("Hello world", None) == "Hello world"

    def test_uses_label_when_payload_present(self) -> None:
        assert (
            extract_embedding_text("", {"label": "Graphique CA"})
            == "Graphique CA"
        )

    def test_uses_title_fallback(self) -> None:
        assert extract_embedding_text("", {"title": "Bar chart"}) == "Bar chart"

    def test_combines_label_and_description(self) -> None:
        out = extract_embedding_text(
            "", {"label": "CA", "description": "Évolution annuelle"}
        )
        assert "CA" in out and "Évolution annuelle" in out

    def test_falls_back_to_content_when_payload_has_no_label(self) -> None:
        assert (
            extract_embedding_text("Mon texte", {"foo": "bar"}) == "Mon texte"
        )

    def test_strips_whitespace(self) -> None:
        assert extract_embedding_text("  hello  ", None) == "hello"


# --- estimate_tokens ---------------------------------------------------


class TestEstimateTokens:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("", 0),
            ("a", 1),
            ("a" * 4, 1),
            ("a" * 100, 25),
        ],
    )
    def test_basic(self, text: str, expected: int) -> None:
        assert estimate_tokens(text) == expected

    def test_handles_unicode(self) -> None:
        assert estimate_tokens("Énergie") >= 1


# --- fit_to_budget -----------------------------------------------------


class TestFitToBudget:
    @staticmethod
    def _render(profile, projets, messages) -> str:
        parts = []
        if profile:
            parts.append("PROFILE:" + " ".join(f"{k}={v}" for k, v in profile.items()))
        for p in projets:
            parts.append(f"P:{p.get('nom','')}|{p.get('description','')}")
        for m in messages:
            parts.append(f"M:{m.get('role','')}|{m.get('content','')}")
        return "\n".join(parts)

    def test_no_compaction_if_under_budget(self) -> None:
        profile, projets, messages, est = fit_to_budget(
            profile={"raison_sociale": "X"},
            projets=[],
            messages=[{"role": "user", "content": "hi"}],
            render=self._render,
            budget=10_000,
        )
        assert profile == {"raison_sociale": "X"}
        assert messages == [{"role": "user", "content": "hi"}]
        assert est <= 10_000

    def test_truncates_descriptions_pass_1(self) -> None:
        long = "x" * 300
        projets = [
            {"nom": f"p{i}", "description": long, "statut": "actif"}
            for i in range(5)
        ]
        _, projets_out, _, est = fit_to_budget(
            profile=None,
            projets=projets,
            messages=[],
            render=self._render,
            budget=200,
        )
        assert est <= 200
        for p in projets_out:
            assert len(p.get("description") or "") <= 100

    def test_reduces_projects_pass_2(self) -> None:
        projets = [
            {"nom": f"p{i}", "description": "abcd" * 30, "statut": "actif"}
            for i in range(10)
        ]
        _, projets_out, _, est = fit_to_budget(
            profile=None,
            projets=projets,
            messages=[],
            render=self._render,
            budget=80,
        )
        assert len(projets_out) <= 7
        assert est <= 80

    def test_reduces_messages_window_pass_3(self) -> None:
        messages = [
            {
                "role": "user" if i % 2 else "assistant",
                "content": "abcd" * 50,
            }
            for i in range(20)
        ]
        _, _, messages_out, _ = fit_to_budget(
            profile=None,
            projets=[],
            messages=messages,
            render=self._render,
            budget=60,
        )
        assert 5 <= len(messages_out) <= 12

    def test_messages_floor_never_below_5(self) -> None:
        messages = [
            {"role": "user", "content": "z" * 1000} for _ in range(20)
        ]
        _, _, messages_out, _ = fit_to_budget(
            profile=None,
            projets=[],
            messages=messages,
            render=self._render,
            budget=10,
        )
        assert len(messages_out) == 5
