"""F54 / FR-006 — Stratégie de troncature ordonnée du system prompt.

Algorithme `truncate_prompt(parts, budget)` :

1. Calculer ``tokens_total(prompt_str(parts))``.
2. Si ≤ budget → retourner directement.
3. Sinon, appliquer dans l'ordre les steps qui suivent et recalculer après
   chacune. Un step ne s'applique que s'il a quelque chose à couper.

Steps :

- ``step1_indicateurs_old``      — limite à 5 indicateurs récents par axe
  E/S/G (15 max, ré-équilibre par axe).
- ``step2_projets_archived``     — retire les projets ``archive`` et les
  candidatures clôturées.
- ``step3_tools_dont_use_when``  — retire les ``dont_use_when`` des tools
  (garde uniquement ``use_when`` + nom).
- ``step4_sources_verbatim``     — coupe le verbatim des sources (garde
  id+titre+url uniquement).
- ``step5_skills_secondary``     — cap à 3 skills (les 3 plus pertinents).
- ``step6_messages_oldest``      — cap à 8 messages (les 8 plus récents).

NFR-002 : si le résultat reste > ``hard_limit`` (6000), un warning est
loggé et on accepte le dépassement plutôt que de casser le tour.

Renvoie ``(prompt_str, TruncationReport)`` avec observabilité complète
(parts coupées, steps appliqués, before/after).
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable

from app.agent.context.models import (
    BusinessContextRender,
    ChatMsgRender,
    PromptParts,
    SkillRender,
    ToolRender,
    TruncationReport,
)
from app.agent.context.tokens import count_tokens

logger = logging.getLogger(__name__)


DEFAULT_BUDGET: int = 4000
DEFAULT_HARD_LIMIT: int = 6000
DEFAULT_ENCODING: str = "cl100k_base"

#: Limite minimale de skills après troncature (FR-006 step 5).
SKILLS_AFTER_TRUNCATION: int = 3

#: Limite minimale de messages après troncature (FR-006 step 6).
MESSAGES_AFTER_TRUNCATION: int = 8

#: Limite indicateurs par axe E/S/G après troncature step 1.
INDICATEURS_PER_AXE_AFTER_TRUNCATION: int = 5


# ---------------------------------------------------------------------------
# Renderer du prompt assemblé (string final)
# ---------------------------------------------------------------------------


def render_parts(parts: PromptParts) -> str:
    """Concatène un :class:`PromptParts` en string finale séparée par
    deux retours à la ligne.

    L'ordre est :
    1. Identité (jamais tronqué)
    2. Invariants (jamais tronqué)
    3. Bandeau admin (si présent)
    4. Skills actifs
    5. Outils disponibles
    6. Arbre de décision tools
    7. Contexte porteur (PME)
    8. Contexte page courante
    9. Note bottom sheet (si présent)
    10. Métadonnées (date, devise, langue)
    11. Messages récents (chat history)
    """
    blocks: list[str] = [parts.identity, parts.invariants]
    if parts.admin_banner:
        blocks.append(parts.admin_banner)
    if parts.skills:
        blocks.append(_render_skills(parts.skills))
    if parts.tools:
        blocks.append(_render_tools(parts.tools))
    if parts.decision_tree:
        blocks.append(parts.decision_tree)
    if parts.business_ctx and parts.business_ctx.text:
        blocks.append(parts.business_ctx.text)
    if parts.page_ctx and parts.page_ctx.text:
        blocks.append(parts.page_ctx.text)
    if parts.sheet_result_note:
        blocks.append(parts.sheet_result_note)
    if parts.metadata:
        blocks.append(parts.metadata)
    if parts.recent_messages:
        blocks.append(_render_messages(parts.recent_messages))
    return "\n\n".join(blocks)


def _render_skills(skills: list[SkillRender]) -> str:
    if not skills:
        return ""
    out = ["# SKILLS ACTIFS"]
    for s in skills:
        line = f"- **{s.code}** ({s.version})"
        if s.procedure_short:
            line += f" — {s.procedure_short}"
        out.append(line)
    return "\n".join(out)


def _render_tools(tools: list[ToolRender]) -> str:
    if not tools:
        return ""
    out = ["# OUTILS DISPONIBLES"]
    for t in tools:
        line = f"- **{t.name}**"
        if t.use_when:
            line += f" — utiliser quand : {t.use_when}"
        if t.dont_use_when:
            line += f" ; ne pas utiliser quand : {t.dont_use_when}"
        if t.schema_summary:
            line += f" ; schéma : {t.schema_summary}"
        out.append(line)
    return "\n".join(out)


def _render_messages(messages: list[ChatMsgRender]) -> str:
    if not messages:
        return ""
    out = ["# DERNIERS MESSAGES"]
    for m in messages:
        out.append(f"- [{m.role}] {m.content}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Steps de troncature
# ---------------------------------------------------------------------------


def _step1_keep_5_indicateurs_per_axe(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 1 — Ré-équilibre indicateurs : 5 récents par axe E/S/G max."""
    bcr = parts.business_ctx
    by_axe: dict[str, list[str]] = bcr.indicateurs_par_axe
    if not by_axe:
        return parts, False

    new_by_axe: dict[str, list[str]] = OrderedDict()
    changed = False
    for axe, lines in by_axe.items():
        if len(lines) > INDICATEURS_PER_AXE_AFTER_TRUNCATION:
            new_by_axe[axe] = lines[:INDICATEURS_PER_AXE_AFTER_TRUNCATION]
            changed = True
        else:
            new_by_axe[axe] = list(lines)

    if not changed:
        return parts, False

    # Reconstruit le texte business_ctx avec la nouvelle vue par axe.
    new_text = _replace_indicateurs_par_axe(bcr.text, new_by_axe)
    new_business_ctx = BusinessContextRender(
        text=new_text,
        indicateurs_par_axe=new_by_axe,
    )
    return parts.model_copy(update={"business_ctx": new_business_ctx}), True


def _replace_indicateurs_par_axe(text: str, by_axe: dict[str, list[str]]) -> str:
    """Remplace la sous-section indicateurs par axe dans le texte business.

    Stratégie simple : on cherche le marker ``## INDICATEURS RÉCENTS`` et on
    réécrit la section. Si absent, on append en fin de bloc.
    """
    marker = "## INDICATEURS RÉCENTS"
    section = [marker]
    for axe in ("E", "S", "G"):
        lines = by_axe.get(axe, [])
        if not lines:
            continue
        section.append(f"### Axe {axe}")
        section.extend(f"- {ln}" for ln in lines)
    new_section = "\n".join(section)

    if marker in text:
        # Remplace de marker jusqu'au prochain "## " ou fin.
        start = text.index(marker)
        rest = text[start + len(marker):]
        next_marker = rest.find("\n## ")
        if next_marker == -1:
            return text[:start] + new_section
        return text[:start] + new_section + rest[next_marker:]
    return text + "\n\n" + new_section


def _step2_drop_archived(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 2 — Retire la mention des projets archivés / candidatures clôturées
    du texte business_ctx.

    Les caps loader les ont déjà filtrés (statut != archive, statut ∈
    {brouillon, soumise, en_instruction}). Cette étape est donc défensive
    pour le cas où des projets archivés se seraient glissés.
    """
    text = parts.business_ctx.text
    changed = False
    new_lines: list[str] = []
    for line in text.split("\n"):
        if "archive" in line.lower() or "cloturee" in line.lower() or "clôturée" in line.lower():
            changed = True
            continue
        new_lines.append(line)
    if not changed:
        return parts, False
    new_business = parts.business_ctx.model_copy(update={"text": "\n".join(new_lines)})
    return parts.model_copy(update={"business_ctx": new_business}), True


def _step3_drop_dont_use_when(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 3 — Retire le ``dont_use_when`` de tous les tools."""
    if not parts.tools:
        return parts, False
    changed = False
    new_tools: list[ToolRender] = []
    for t in parts.tools:
        if t.dont_use_when:
            changed = True
            new_tools.append(t.model_copy(update={"dont_use_when": None}))
        else:
            new_tools.append(t)
    if not changed:
        return parts, False
    return parts.model_copy(update={"tools": new_tools}), True


def _step4_drop_sources_verbatim(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 4 — Coupe le verbatim des sources dans business_ctx (garde
    id+titre+url uniquement)."""
    text = parts.business_ctx.text
    changed = False
    new_lines: list[str] = []
    in_source_verbatim = False
    for line in text.split("\n"):
        if line.strip().startswith("> ") and in_source_verbatim:
            changed = True
            continue
        if "verbatim" in line.lower() or "extrait :" in line.lower():
            in_source_verbatim = True
            changed = True
            continue
        if line.strip() == "" and in_source_verbatim:
            in_source_verbatim = False
        new_lines.append(line)
    if not changed:
        return parts, False
    new_business = parts.business_ctx.model_copy(update={"text": "\n".join(new_lines)})
    return parts.model_copy(update={"business_ctx": new_business}), True


def _step5_cap_skills(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 5 — Cap à :data:`SKILLS_AFTER_TRUNCATION` skills (3)."""
    if len(parts.skills) <= SKILLS_AFTER_TRUNCATION:
        return parts, False
    return parts.model_copy(
        update={"skills": parts.skills[:SKILLS_AFTER_TRUNCATION]}
    ), True


def _step6_cap_messages(parts: PromptParts) -> tuple[PromptParts, bool]:
    """Step 6 — Cap à :data:`MESSAGES_AFTER_TRUNCATION` messages récents."""
    if len(parts.recent_messages) <= MESSAGES_AFTER_TRUNCATION:
        return parts, False
    # Garde les ``MESSAGES_AFTER_TRUNCATION`` plus récents (queue de la liste).
    return parts.model_copy(
        update={"recent_messages": parts.recent_messages[-MESSAGES_AFTER_TRUNCATION:]}
    ), True


# ---------------------------------------------------------------------------
# truncate_prompt (orchestration)
# ---------------------------------------------------------------------------


_STEPS: list[tuple[str, str, Callable[[PromptParts], tuple[PromptParts, bool]]]] = [
    ("step1_indicateurs_old", "indicateurs_old", _step1_keep_5_indicateurs_per_axe),
    ("step2_projets_archived", "projets_archived", _step2_drop_archived),
    ("step3_tools_dont_use_when", "tools_dont_use_when", _step3_drop_dont_use_when),
    ("step4_sources_verbatim", "sources_verbatim", _step4_drop_sources_verbatim),
    ("step5_skills_secondary", "skills_secondary", _step5_cap_skills),
    ("step6_messages_oldest", "messages_oldest", _step6_cap_messages),
]


def truncate_prompt(
    parts: PromptParts,
    *,
    budget: int = DEFAULT_BUDGET,
    hard_limit: int = DEFAULT_HARD_LIMIT,
    encoding: str = DEFAULT_ENCODING,
) -> tuple[str, TruncationReport]:
    """Applique la stratégie ordonnée et renvoie ``(prompt_str, report)``.

    Cf. :doc:`specs/054-agent-context-builder/research.md` (R8).
    """
    initial_str = render_parts(parts)
    tokens_before = count_tokens(initial_str, encoding=encoding)

    if tokens_before <= budget:
        return initial_str, TruncationReport(
            budget=budget,
            tokens_before=tokens_before,
            tokens_after=tokens_before,
            warning_emitted=False,
        )

    steps_applied: list[str] = []
    parts_truncated: list[str] = []
    current = parts

    for step_name, reason_label, fn in _STEPS:
        new_parts, did_apply = fn(current)
        if did_apply:
            steps_applied.append(step_name)
            parts_truncated.append(reason_label)
            current = new_parts
            tokens_now = count_tokens(render_parts(current), encoding=encoding)
            if tokens_now <= budget:
                break

    final_str = render_parts(current)
    tokens_after = count_tokens(final_str, encoding=encoding)

    over_hard_limit = tokens_after > hard_limit

    report = TruncationReport(
        budget=budget,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        warning_emitted=True,
        parts_truncated=parts_truncated,
        steps_applied=steps_applied,
    )

    # Logger structuré (FR-010) — `extra` permet aux LogProcessors de
    # parser proprement (compatible structlog si installé en aval).
    logger.warning(
        "prompt_budget_exceeded steps=%s tokens_before=%d tokens_after=%d budget=%d hard_limit=%d over_hard_limit=%s",
        steps_applied,
        tokens_before,
        tokens_after,
        budget,
        hard_limit,
        over_hard_limit,
        extra={
            "event": "prompt_budget_exceeded",
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "budget": budget,
            "hard_limit": hard_limit,
            "steps_applied": steps_applied,
            "over_hard_limit": over_hard_limit,
        },
    )

    return final_str, report


__all__ = [
    "DEFAULT_BUDGET",
    "DEFAULT_ENCODING",
    "DEFAULT_HARD_LIMIT",
    "INDICATEURS_PER_AXE_AFTER_TRUNCATION",
    "MESSAGES_AFTER_TRUNCATION",
    "SKILLS_AFTER_TRUNCATION",
    "render_parts",
    "truncate_prompt",
]
