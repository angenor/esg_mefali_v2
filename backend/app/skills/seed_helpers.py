"""F21 — Helpers purs pour le seed des skills MVP.

Fournit :

- ``content_hash`` : empreinte stable d'un payload de skill (détecte si
  ``version`` doit être bumpé entre deux runs).
- ``load_skill_yaml`` : lit une fixture YAML et retourne un ``dict``.
- ``validate_fixture_shape`` : vérifie la structure minimale d'une fixture.
- ``validate_golden_examples`` : vérifie format + cohérence whitelist.
- ``resolve_sources`` : transforme des refs ``(publisher, title_match)`` en
  ``UUID`` Sources (et liste les manquants/non-verified).
- ``should_publish`` : décide entre ``draft`` et ``published`` selon
  prérequis (sources verified + tools connus).
- ``known_tools`` : retourne l'ensemble des tools enregistrés dans le
  registry F14 (avec lazy register F15/F16).

Aucune fonction n'écrit en BDD : ces helpers sont purs, unit-testables sans
Postgres (sauf ``resolve_sources`` qui prend un ``Session``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

VALID_INTENTS: frozenset[str] = frozenset(
    {"analyse", "mutation", "navigation", "question"}
)
PROCEDURE_MIN_CHARS_CRITICAL: int = 200
PROMPT_MAX_CHARS: int = 6000  # ~1500 tokens à 4 chars/token
GOLDEN_MIN_COUNT: int = 5
REQUIRED_FIXTURE_FIELDS: tuple[str, ...] = (
    "name",
    "domain",
    "prompt_expert",
    "tool_whitelist",
    "activation_rules",
)


def content_hash(payload: dict[str, Any]) -> str:
    """Hash SHA-256 des champs sémantiques d'une skill.

    Inclut uniquement les champs qui rendent une mise à jour signifiante :
    ``prompt_expert``, ``activation_rules``, ``tool_whitelist``, ``procedure``.
    L'ordre des clés est canonicalisé via ``json.dumps(sort_keys=True)`` pour
    être insensible à l'ordre d'insertion.
    """
    payload_keys = ("prompt_expert", "activation_rules", "tool_whitelist", "procedure")
    canonical = {k: payload.get(k) for k in payload_keys}
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def load_skill_yaml(path: Path) -> dict[str, Any]:
    """Parse un fichier YAML et retourne le dict racine."""
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"Fixture YAML invalide (root non-dict) : {path}")
    return data


def validate_fixture_shape(
    data: dict[str, Any], *, is_critical: bool = False
) -> list[str]:
    """Vérifie la structure minimale d'une fixture (errors list, vide si OK)."""
    errors: list[str] = []
    for fname in REQUIRED_FIXTURE_FIELDS:
        if fname not in data:
            errors.append(f"Champ requis manquant : {fname}")
            continue
        val = data[fname]
        if fname in ("name", "domain", "prompt_expert") and (
            not isinstance(val, str) or not val.strip()
        ):
            errors.append(f"Champ {fname} doit être une chaîne non vide.")
        if fname == "tool_whitelist" and (
            not isinstance(val, list) or not all(isinstance(t, str) for t in val)
        ):
            errors.append("tool_whitelist doit être une liste de strings.")
        if fname == "activation_rules" and not isinstance(val, dict):
            errors.append("activation_rules doit être un objet.")

    prompt = data.get("prompt_expert", "") or ""
    if isinstance(prompt, str) and len(prompt) > PROMPT_MAX_CHARS:
        errors.append(
            f"prompt_expert trop long ({len(prompt)} > {PROMPT_MAX_CHARS} chars)."
        )

    lang = data.get("language_default", "fr")
    if lang != "fr":
        errors.append(
            f"language_default doit être 'fr' (langue par défaut), got '{lang}'."
        )

    status_target = data.get("status_target", "draft")
    if status_target not in ("draft", "published"):
        errors.append(
            f"status_target invalide : {status_target!r} (attendu draft|published)."
        )

    if is_critical:
        procedure = data.get("procedure", "") or ""
        if (
            not isinstance(procedure, str)
            or len(procedure) < PROCEDURE_MIN_CHARS_CRITICAL
        ):
            errors.append(
                f"procedure doit faire ≥ {PROCEDURE_MIN_CHARS_CRITICAL} chars "
                f"pour une skill critique (actuel : {len(procedure)})."
            )

    return errors


def validate_golden_examples(
    examples: list[Any], whitelist: list[str], *, min_count: int = GOLDEN_MIN_COUNT
) -> list[str]:
    """Vérifie qu'une liste de golden examples est exploitable."""
    errors: list[str] = []
    if not isinstance(examples, list):
        return ["golden_examples doit être une liste."]
    if len(examples) < min_count:
        errors.append(
            f"≥ {min_count} golden examples requis (actuel : {len(examples)})."
        )
    whitelist_set = set(whitelist or [])
    for idx, ex in enumerate(examples):
        if not isinstance(ex, dict):
            errors.append(f"golden_examples[{idx}] doit être un objet.")
            continue
        for required in (
            "input_message",
            "page_context",
            "intent",
            "expected_tool",
        ):
            if required not in ex:
                errors.append(f"golden_examples[{idx}].{required} manquant.")
        intent = ex.get("intent")
        if intent is not None and intent not in VALID_INTENTS:
            errors.append(
                f"golden_examples[{idx}].intent invalide : {intent!r} "
                f"(attendu : {sorted(VALID_INTENTS)})."
            )
        expected_tool = ex.get("expected_tool")
        if (
            expected_tool is not None
            and whitelist_set
            and expected_tool not in whitelist_set
        ):
            errors.append(
                f"golden_examples[{idx}].expected_tool {expected_tool!r} "
                f"absent de tool_whitelist."
            )
    return errors


def resolve_sources(
    db: Session, refs: list[dict[str, str]]
) -> tuple[list[UUID], list[dict[str, str]], list[str]]:
    """Résout des refs ``(publisher, title_match)`` en UUID ``Source``.

    Retourne ``(found_ids, missing_refs, non_verified_publishers)``.
    """
    if not refs:
        return [], [], []
    found_ids: list[UUID] = []
    missing: list[dict[str, str]] = []
    non_verified: list[str] = []
    for ref in refs:
        publisher = ref.get("publisher")
        title_match = ref.get("title_match")
        if not publisher or not title_match:
            missing.append(ref)
            continue
        row = db.execute(
            text(
                "SELECT id, verification_status FROM source "
                "WHERE publisher = :publisher AND title ILIKE :title "
                "ORDER BY captured_at DESC LIMIT 1"
            ),
            {"publisher": publisher, "title": f"%{title_match}%"},
        ).first()
        if row is None:
            missing.append(ref)
            continue
        found_ids.append(row._mapping["id"])
        if row._mapping["verification_status"] != "verified":
            non_verified.append(publisher)
    return found_ids, missing, non_verified


def should_publish(
    *,
    status_target: str,
    missing_sources: list[dict[str, str]],
    non_verified_publishers: list[str],
    unknown_tools: list[str],
) -> tuple[str, list[str]]:
    """Décide du statut final + reasons.

    - Si ``unknown_tools`` non vide : retourne ``("skip", reasons)`` (la
      skill ne sera pas insérée du tout).
    - Si ``status_target == 'draft'`` : reste ``draft``.
    - Si ``status_target == 'published'`` mais sources manquantes ou non
      verified : bascule en ``draft`` avec warning.
    """
    reasons: list[str] = []
    if unknown_tools:
        reasons.append(f"Tools inconnus dans whitelist : {sorted(unknown_tools)}")
        return "skip", reasons
    if status_target == "draft":
        return "draft", reasons
    if missing_sources:
        reasons.append(f"{len(missing_sources)} source(s) introuvable(s) en base.")
        return "draft", reasons
    if non_verified_publishers:
        reasons.append(
            "Sources non verified : "
            + ", ".join(sorted(set(non_verified_publishers)))
        )
        return "draft", reasons
    return "published", reasons


_FALLBACK_TOOLS: frozenset[str] = frozenset(
    {
        "respond_user",
        "ask_qcu",
        "ask_qcm",
        "ask_yes_no",
        "ask_select",
        "ask_number",
        "ask_file_upload",
        "show_summary_card",
        "show_kpi_card",
        "show_radar_chart",
        "show_bar_chart",
        "show_line_chart",
    }
)


def known_tools() -> set[str]:
    """Retourne l'ensemble des tools enregistrés dans le registry F14.

    Lit ``TOOL_REGISTRY`` (sans muter l'etat global : pas d'auto-register
    pour ne pas polluer les tests d'autres modules). Complete avec un
    fallback statique si le registry est vide (modules non importes).
    """
    try:
        from app.orchestrator.tool_registry import TOOL_REGISTRY

        if TOOL_REGISTRY:
            tools = set(TOOL_REGISTRY.keys())
            # Toujours inclure les tools "noyau" attendus par F20 meme s'ils
            # ne sont pas formellement registres (compat F14 fallback).
            tools.update(_FALLBACK_TOOLS)
            return tools
    except Exception:  # noqa: BLE001
        pass
    return set(_FALLBACK_TOOLS)


__all__ = [
    "GOLDEN_MIN_COUNT",
    "PROCEDURE_MIN_CHARS_CRITICAL",
    "PROMPT_MAX_CHARS",
    "REQUIRED_FIXTURE_FIELDS",
    "VALID_INTENTS",
    "content_hash",
    "known_tools",
    "load_skill_yaml",
    "resolve_sources",
    "should_publish",
    "validate_fixture_shape",
    "validate_golden_examples",
]
