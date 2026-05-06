"""F54 / FR-004 — build_system_prompt : assemble les blocs en prompt final.

Pipeline :

1. ``build_prompt_parts(...)`` construit un :class:`PromptParts` (immutable)
   à partir du ``BusinessContext``, ``EnrichedPageContext``, skills, tools,
   messages, sheet_result, role.
2. ``build_system_prompt(...)`` rend la chaîne, applique la troncature si
   nécessaire (cf. :mod:`app.agent.context.truncation`) et retourne
   ``(prompt_str, TruncationReport)``.

Service pur (NFR-004) — n'importe **pas** ``app.chat.api`` ni
``app.agent.runner``.

Les blocs sont générés par des fonctions pures :func:`render_business_block`,
:func:`render_page_block`, etc. — testables en isolation.

Logging FR-010 : un log structuré ``prompt_built`` est émis à chaque appel
de :func:`build_system_prompt`.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.agent.context.admin_mode import (
    mark_mutation_tools_require_confirmation,
    render_admin_banner,
)
from app.agent.context.escape import clean_user_str
from app.agent.context.models import (
    BusinessContext,
    BusinessContextRender,
    ChatMsgRender,
    EnrichedPageContext,
    EntrepriseSummary,
    IndicateurSummary,
    PageContextRender,
    PromptParts,
    SkillRender,
    ToolRender,
    TruncationReport,
)
from app.agent.context.money_format import (
    Money as ContextMoney,
)
from app.agent.context.money_format import (
    collect_currencies,
    format_money,
)
from app.agent.context.sheet_result import (
    extract_sheet_result,
    render_sheet_result_note,
)
from app.agent.context.truncation import (
    DEFAULT_BUDGET,
    DEFAULT_ENCODING,
    DEFAULT_HARD_LIMIT,
    truncate_prompt,
)
from app.agent.prompts.identity import IDENTITY_BLOCK
from app.agent.prompts.invariants import INVARIANTS_TEMPLATE, PROMPT_VERSION

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Render — pure functions
# ---------------------------------------------------------------------------


def render_identity_block() -> str:
    """Bloc d'identité ESG Mefali (FR-001) — toujours en tête."""
    return IDENTITY_BLOCK.rstrip()


def render_invariants_block() -> str:
    """Bloc des 10 invariants Module 0 (FR-001) — toujours sous l'identité."""
    return INVARIANTS_TEMPLATE.rstrip()


def render_metadata_block(
    *,
    devise_pme: str,
    langue: str,
    page: str,
) -> str:
    now_str = datetime.now(UTC).strftime("%Y-%m-%d")
    return (
        "# MÉTADONNÉES TOUR\n"
        f"- Date : {now_str}\n"
        f"- Page : {page}\n"
        f"- Devise PME : {devise_pme}\n"
        f"- Langue : {langue}\n"
        f"- Prompt version : {PROMPT_VERSION}"
    )


def render_business_block(ctx: BusinessContext) -> BusinessContextRender:
    """Construit le bloc "CONTEXTE PME" + la vue indicateurs par axe E/S/G.

    Tous les fields user-controlled sont déjà passés par
    :func:`clean_user_str` au niveau du loader. On les insère tels quels.
    """
    monies: list[ContextMoney | None] = _collect_monies(ctx)
    currencies = collect_currencies(monies)
    fx_rate_usd: Any = None  # Pas de snapshot USD pour le MVP — TODO F58.

    out: list[str] = ["# CONTEXTE PORTEUR (PME)"]

    # Entreprise.
    if ctx.entreprise is not None:
        out.append(_render_entreprise(ctx.entreprise, currencies, fx_rate_usd))
    else:
        out.append("## Entreprise\n_Aucun profil enregistré._")

    # Projets actifs.
    out.append("## Projets actifs")
    if ctx.projets_actifs:
        for p in ctx.projets_actifs:
            mline = ""
            if p.montant_demande is not None:
                m = ContextMoney(
                    amount=p.montant_demande.amount,
                    currency=p.montant_demande.currency,
                )
                mline = f" — {format_money(m, native_currencies=currencies, fx_rate_usd_to_xof=fx_rate_usd)}"
            titre = clean_user_str(p.titre)
            statut = clean_user_str(p.statut)
            line = f"- **{titre}** (`{statut}`){mline}"
            if p.description_courte:
                line += f"\n  {clean_user_str(p.description_courte)}"
            out.append(line)
    else:
        out.append("Aucun projet enregistré.")

    # Candidatures en cours.
    out.append("## Candidatures en cours")
    if ctx.candidatures_en_cours:
        for c in ctx.candidatures_en_cours:
            line = f"- candidature `{c.id}` (statut `{c.statut}`)"
            if c.score is not None:
                line += f" — score {c.score}/100"
            out.append(line)
    else:
        out.append("Aucune candidature en cours.")

    # Score crédit.
    if ctx.score_credit is not None:
        s = ctx.score_credit
        out.append("## Score crédit (le plus récent)")
        out.append(f"- Score global : **{s.gauge}/100**")
        if s.sub_scores:
            sub_str = ", ".join(f"{k}={v}" for k, v in s.sub_scores.items())
            out.append(f"- Sous-scores : {sub_str}")
        if s.lacunes_principales:
            lac = ", ".join(s.lacunes_principales[:5])
            out.append(f"- Lacunes principales : {lac}")
    else:
        out.append("## Score crédit")
        out.append("Aucun scoring calculé.")

    # Plan d'action.
    if ctx.plan_action_steps:
        out.append("## Plan d'action en cours")
        for step in ctx.plan_action_steps:
            out.append(f"- [{step.statut}] {step.titre}")

    # Indicateurs par axe E/S/G (vue, pas stockage — P6).
    by_axe = _group_indicateurs_by_axe(ctx.indicateurs_recents)
    if any(by_axe.values()):
        out.append("## INDICATEURS RÉCENTS")
        for axe in ("E", "S", "G"):
            lines = by_axe.get(axe, [])
            if not lines:
                continue
            out.append(f"### Axe {axe}")
            out.extend(f"- {ln}" for ln in lines)

    return BusinessContextRender(
        text="\n".join(out),
        indicateurs_par_axe=dict(by_axe),
    )


def render_page_block(page_ctx: EnrichedPageContext) -> PageContextRender:
    """Construit le bloc "CONTEXTE PAGE COURANTE"."""
    out: list[str] = ["# CONTEXTE PAGE COURANTE"]
    out.append(f"- Route : {clean_user_str(page_ctx.page) or '/'}")

    if page_ctx.entity_type is None:
        out.append("- Aucune entité ciblée.")
        return PageContextRender(text="\n".join(out))

    out.append(f"- Type d'entité : {page_ctx.entity_type}")
    if page_ctx.entity_id:
        out.append(f"- ID : `{page_ctx.entity_id}`")

    if not page_ctx.data:
        out.append("_Aucune donnée chargée (entité inexistante ou cross-tenant)._")
        return PageContextRender(text="\n".join(out))

    out.append("- Données :")
    for k, v in page_ctx.data.items():
        out.append(f"  - {k} : {_brief_repr(v)}")

    if page_ctx.related:
        out.append(f"- Entités liées : {len(page_ctx.related)}")
        for rel in page_ctx.related[:5]:
            out.append(f"  - {_brief_repr(rel)}")

    return PageContextRender(text="\n".join(out))


def render_skills_block_models(skills: Iterable[Any]) -> list[SkillRender]:
    """Convertit la liste de skills (objets F19) en :class:`SkillRender`."""
    out: list[SkillRender] = []
    for s in skills:
        try:
            code = clean_user_str(getattr(s, "code", None) or getattr(s, "name", "skill"))
            version = str(getattr(s, "version", None) or "v1")
            proc = clean_user_str(
                getattr(s, "procedure_short", None)
                or getattr(s, "description", None)
                or "",
                max_len=200,
            )
            out.append(SkillRender(code=code, version=version, procedure_short=proc))
        except Exception:  # noqa: BLE001 - tolérant aux schémas variables.
            continue
    return out


def render_tools_block_models(tools: Iterable[Any]) -> list[ToolRender]:
    """Convertit la liste de tools (objets ToolDef de F14/F55) en
    :class:`ToolRender`."""
    out: list[ToolRender] = []
    for t in tools:
        try:
            name = str(getattr(t, "name", None) or "")
            if not name:
                continue
            use_when = clean_user_str(getattr(t, "use_when", "") or "", max_len=200)
            dont_use = getattr(t, "dont_use_when", None)
            dont_use_clean = (
                clean_user_str(dont_use, max_len=200) if dont_use else None
            )
            schema_summary = clean_user_str(
                getattr(t, "schema_summary", "") or "", max_len=200
            )
            out.append(
                ToolRender(
                    name=name,
                    use_when=use_when,
                    dont_use_when=dont_use_clean,
                    schema_summary=schema_summary,
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return out


def render_decision_tree_block(tools: Iterable[ToolRender]) -> str:
    """FR-012 — Génère un arbre de décision compact à partir des
    ``use_when`` / ``dont_use_when`` du tool registry.

    Pas de duplication : si la liste est vide, retourne une chaîne vide.
    """
    tools = list(tools)
    if not tools:
        return ""
    out = ["# ARBRE DE DÉCISION TOOLS"]
    out.append(
        "Sélectionne au plus 1–2 tools par tour, en cohérence avec ton intent."
    )
    for t in tools:
        line = f"- `{t.name}`"
        if t.use_when:
            line += f" → {t.use_when}"
        if t.dont_use_when:
            line += f" ; éviter quand : {t.dont_use_when}"
        out.append(line)
    return "\n".join(out)


def render_chat_messages(
    messages: Iterable[Any], *, cap: int = 15
) -> list[ChatMsgRender]:
    """Convertit les ``cap`` derniers messages historiques (FR-016) en
    :class:`ChatMsgRender`.

    Accepte des objets ``BaseMessage`` LangChain ou des dicts ``{role,
    content, timestamp}``. Les contenus sont nettoyés (FR-013).
    """
    raw = list(messages)
    if cap and len(raw) > cap:
        raw = raw[-cap:]

    out: list[ChatMsgRender] = []
    for m in raw:
        role: str
        content: str
        ts: datetime | None = None
        if isinstance(m, dict):
            role = str(m.get("role") or "user").lower()
            content = str(m.get("content") or "")
            ts_raw = m.get("timestamp") or m.get("created_at")
            if isinstance(ts_raw, datetime):
                ts = ts_raw if ts_raw.tzinfo else ts_raw.replace(tzinfo=UTC)
        else:
            cls = type(m).__name__
            role_map = {
                "HumanMessage": "user",
                "AIMessage": "assistant",
                "ToolMessage": "tool",
                "SystemMessage": "system",
            }
            role = role_map.get(cls, "user")
            content = str(getattr(m, "content", "") or "")
        if role not in ("user", "assistant", "tool", "system"):
            role = "user"
        clean_content = clean_user_str(content, max_len=400)
        out.append(ChatMsgRender(role=role, content=clean_content, timestamp=ts))
    return out


# ---------------------------------------------------------------------------
# build_prompt_parts + build_system_prompt
# ---------------------------------------------------------------------------


def build_prompt_parts(
    *,
    business_ctx: BusinessContext,
    page_ctx: EnrichedPageContext,
    active_skills: Iterable[Any] | None = None,
    available_tools: Iterable[Any] | None = None,
    recent_messages: Iterable[Any] | None = None,
    last_user_message: dict | None = None,
    user_role: str = "pme",
    metadata: dict | None = None,
) -> PromptParts:
    """Assemble un :class:`PromptParts` immutable (FR-004).

    Paramètres :
    - ``business_ctx`` : produit par :func:`load_business_context`.
    - ``page_ctx`` : produit par :func:`load_page_context`.
    - ``active_skills`` : liste de skills (F19) — tolère des objets variés.
    - ``available_tools`` : liste de ToolDef (F14/F55) — tolère des objets variés.
    - ``recent_messages`` : 15 derniers messages (FR-016).
    - ``last_user_message`` : dict du dernier message utilisateur — utilisé
      pour extraire un éventuel ``sheet_result`` (FR-017).
    - ``user_role`` : ``"pme"`` ou ``"admin"`` (FR-018).
    - ``metadata`` : dict ``{date?, devise_pme, langue}``.
    """
    business_render = render_business_block(business_ctx)
    page_render = render_page_block(page_ctx)

    skills = render_skills_block_models(active_skills or [])
    tools = render_tools_block_models(available_tools or [])

    if user_role == "admin":
        tools = mark_mutation_tools_require_confirmation(tools)

    decision_tree = render_decision_tree_block(tools)

    msgs = render_chat_messages(recent_messages or [], cap=15)

    sheet_result = extract_sheet_result(last_user_message)
    sheet_note = render_sheet_result_note(sheet_result)

    admin_banner = (
        render_admin_banner(business_ctx.account_id) if user_role == "admin" else None
    )

    md = metadata or {}
    metadata_block = render_metadata_block(
        devise_pme=str(md.get("devise_pme") or _devise_pme_default(business_ctx)),
        langue=str(md.get("langue") or "fr"),
        page=str(md.get("page") or page_ctx.page),
    )

    return PromptParts(
        identity=render_identity_block(),
        invariants=render_invariants_block(),
        skills=skills,
        tools=tools,
        business_ctx=business_render,
        page_ctx=page_render,
        decision_tree=decision_tree,
        metadata=metadata_block,
        recent_messages=msgs,
        sheet_result_note=sheet_note,
        admin_banner=admin_banner,
    )


def build_system_prompt(
    *,
    business_ctx: BusinessContext,
    page_ctx: EnrichedPageContext,
    active_skills: Iterable[Any] | None = None,
    available_tools: Iterable[Any] | None = None,
    recent_messages: Iterable[Any] | None = None,
    last_user_message: dict | None = None,
    user_role: str = "pme",
    metadata: dict | None = None,
    budget_tokens: int = DEFAULT_BUDGET,
    hard_limit: int = DEFAULT_HARD_LIMIT,
    encoding: str = DEFAULT_ENCODING,
    cache_hit_business_ctx: bool = False,
) -> tuple[str, TruncationReport]:
    """Pipeline complet : build_parts → render → count → truncate (FR-004).

    Renvoie ``(prompt_str, report)``. Émet un log ``prompt_built`` avec
    observabilité complète (FR-010).
    """
    start = time.perf_counter()

    parts = build_prompt_parts(
        business_ctx=business_ctx,
        page_ctx=page_ctx,
        active_skills=active_skills,
        available_tools=available_tools,
        recent_messages=recent_messages,
        last_user_message=last_user_message,
        user_role=user_role,
        metadata=metadata,
    )

    prompt_str, report = truncate_prompt(
        parts,
        budget=budget_tokens,
        hard_limit=hard_limit,
        encoding=encoding,
    )

    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "prompt_built account_id=%s page=%s tokens=%d/%d truncated=%s duration_ms=%d cache_hit=%s",
        business_ctx.account_id,
        page_ctx.page,
        report.tokens_after,
        report.budget,
        report.parts_truncated,
        duration_ms,
        cache_hit_business_ctx,
        extra={
            "event": "prompt_built",
            "account_id": str(business_ctx.account_id),
            "page": page_ctx.page,
            "tokens_total": report.tokens_after,
            "parts_truncated": list(report.parts_truncated),
            "duration_ms": duration_ms,
            "cache_hit_business_ctx": cache_hit_business_ctx,
            "warning_emitted": report.warning_emitted,
        },
    )

    return prompt_str, report


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _collect_monies(ctx: BusinessContext) -> list[ContextMoney | None]:
    """Liste des Money apparaissant dans le ctx pour collect_currencies."""
    out: list[ContextMoney | None] = []
    if ctx.entreprise and ctx.entreprise.ca_dernier_exercice is not None:
        m = ctx.entreprise.ca_dernier_exercice
        out.append(ContextMoney(amount=m.amount, currency=m.currency))
    for p in ctx.projets_actifs:
        if p.montant_demande is not None:
            m = p.montant_demande
            out.append(ContextMoney(amount=m.amount, currency=m.currency))
    return out


def _devise_pme_default(ctx: BusinessContext) -> str:
    if ctx.entreprise and ctx.entreprise.devise_principale:
        return ctx.entreprise.devise_principale
    return "XOF"


def _render_entreprise(
    ent: EntrepriseSummary,
    native_currencies: set[str],
    fx_rate_usd_to_xof: Any,
) -> str:
    # Défense en profondeur (FR-013) : on re-applique clean_user_str même si
    # le loader est censé déjà nettoyer (au cas où un consommateur F55+
    # construirait un EntrepriseSummary à la main).
    raison = clean_user_str(ent.raison_sociale)
    out = [f"## Entreprise — {raison}"]
    if ent.secteur_label or ent.secteur_naf:
        s = clean_user_str(ent.secteur_label or "")
        naf = clean_user_str(ent.secteur_naf or "")
        if naf:
            s = f"{s} (NAF/CITI {naf})" if s else f"NAF/CITI {naf}"
        out.append(f"- Secteur : {s}")
    if ent.taille:
        out.append(f"- Taille : {ent.taille}")
    if ent.effectif:
        out.append(f"- Effectif : {ent.effectif}")
    out.append(f"- Pays : {ent.pays}")
    out.append(f"- Devise principale : {ent.devise_principale}")
    if ent.ca_dernier_exercice is not None:
        m = ContextMoney(
            amount=ent.ca_dernier_exercice.amount,
            currency=ent.ca_dernier_exercice.currency,
        )
        ca = format_money(
            m,
            native_currencies=native_currencies,
            fx_rate_usd_to_xof=fx_rate_usd_to_xof,
        )
        out.append(f"- CA dernier exercice : {ca}")
    if ent.gouvernance_resume:
        out.append(f"- Gouvernance : {clean_user_str(ent.gouvernance_resume)}")
    return "\n".join(out)


def _group_indicateurs_by_axe(
    indicateurs: list[IndicateurSummary],
) -> dict[str, list[str]]:
    """Vue par axe E/S/G générée à la volée (P6 — pas de stockage dupliqué).

    Renvoie ``{"E": [...], "S": [...], "G": [...]}`` (dict ordonné).
    """
    by_axe: dict[str, list[str]] = defaultdict(list)
    for i in indicateurs:
        line = f"`{i.code}` {i.libelle}"
        if i.unite:
            line += f" ({i.unite})"
        if i.referentiel_code:
            line += f" — réf. {i.referentiel_code}"
        if i.source_id is not None:
            line += f" — source `{i.source_id}`"
        by_axe[i.axe].append(line)
    # Ordre stable E,S,G.
    ordered = {axe: by_axe.get(axe, []) for axe in ("E", "S", "G")}
    return ordered


def _brief_repr(value: Any) -> str:
    """Représentation courte d'une valeur dict/list pour le bloc page."""
    s = clean_user_str(str(value), max_len=300)
    return s


__all__ = [
    "build_prompt_parts",
    "build_system_prompt",
    "render_business_block",
    "render_chat_messages",
    "render_decision_tree_block",
    "render_identity_block",
    "render_invariants_block",
    "render_metadata_block",
    "render_page_block",
    "render_skills_block_models",
    "render_tools_block_models",
]
