# Feature Specification: F19 — Moteur de Skills (loader, fusion prompt, injection sources, intégration LangGraph)

**Feature Branch**: `019-skills-engine-loader`
**Created**: 2026-04-29
**Status**: Draft
**Phase**: 4 — Skills (Playbooks Métier)
**Dépendances**: F03 (sources), F06 (back-office workflow draft→published), F09 (catalog référentiels), F14 (orchestrator).

## Contexte

F19 livre **le moteur** des Skills :
- Schéma BDD `skill` + table de liaison `skill_source` (n-n) ;
- Loader contextuel `skill_loader.py` (1–2 skills max selon page/intent/entité) ;
- Fusion prompt `skill_fusion.py` (system invariants + skill expert + sources pré-résolues + procédure + tools whitelistés) ;
- Intersection avec `tool_selector` (F14) déjà branchée via `skill_whitelist`.
- Snapshot version par thread (US8) — interface livrée, persistence reportée à F20.

F20 livrera le CRUD admin. F21 livrera les skills MVP seedées.

## User Stories (priorisées)

### US1 — Schéma BDD Skill (P1)
Table `skill` (`name`, `version`, `domain`, `prompt_expert`, `procedure`, `tool_whitelist TEXT[]`, `activation_rules JSONB`, `golden_examples JSONB`, `status ENUM('draft','published')`, `created_by`, `verified_by`, `valid_from`, `valid_to`, audit). Table `skill_source` (FK `skill_id`, FK `source_id`, PK composite).

### US2 — Loader contextuel (P1)
`load_active_skills(context, session) -> list[Skill]` retourne 1 à 2 skills, en filtrant `status='published'` ET sources liées toutes `verified`.

### US3 — Fusion prompt (P1)
`build_prompt(global_invariants, skill, sources_resolved, context, tools) -> str` : sections markdown `## Invariants`, `## Skill: <name>`, `## Sources de référence`, `## Procédure`, `## Tools disponibles`, `## Contexte`.

### US4 — Injection sources pré-résolues (P1)
`resolve_sources(source_ids, session) -> list[ResolvedSource]` charge titre, publisher, extrait court ≤ 200 caractères, URL, ID, pour les sources `verified` uniquement.

### US5 — Intersection tool_whitelist (P1)
Déjà câblé dans F14 `tool_selector.select(..., skill_whitelist=...)`. F19 fournit le whitelist depuis la skill chargée (`skill.tool_whitelist`).

### US6 — Priorité 1–2 skills max (P1)
Ordre : dossier > scoring > diagnostic > générale. En cas d'égalité : sources les plus à jour (max `date_publi`).

### US7 — Draft jamais servi (P1)
`status != 'published'` ou source liée `non-verified` → skill exclue du loader.

### US8 — Snapshot version (P2 — interface seulement)
`snapshot_skill_version(thread_id, skill_id, version)` interface ; persistence en table dédiée reportée à F20.

## Exigences fonctionnelles

- **FR-001** : Migration alembic `0014_f19_skill` créant `skill` + `skill_source` + ENUM `skill_status`.
- **FR-002** : Modèle SQLAlchemy `Skill` + `SkillSource`.
- **FR-003** : Validateur Pydantic `ActivationRules` avec `any_of: list[Match]`. Match accepte `page` (str glob), `intent` (list str), `entity_type` (str), `offre_id_match` (`fonds_code`/`intermediaire_code`).
- **FR-004** : `app/skills/loader.py:load_active_skills(context, session)` :
  - SELECT skills published seules ;
  - filtre par `activation_rules` matchés contre `context` ;
  - filtre par sources toutes `verified` ;
  - tri par priorité de domaine puis `max(source.date_publi)` desc ;
  - tronque à 2.
- **FR-005** : `app/skills/fusion.py:build_prompt(...)` retourne un markdown structuré.
- **FR-006** : `app/skills/sources.py:resolve_sources(source_ids, session)` (filtre `verified`, troncature 200 chars).
- **FR-007** : `app/skills/snapshot.py:snapshot_skill_version(thread_id, skill_id, version)` interface (no-op persistence + log).
- **FR-008** : `SKILL_PROMPT_MAX_TOKENS=1500` dans `app/config.py` (estimation `len(text)//4`).
- **FR-009** : Endpoint interne `POST /internal/skill-loader/test` (FastAPI router) — body `{context: dict}`, retourne `{skills: [...], prompt: str}`. Garde dev/test.

## Exigences non-fonctionnelles

- NFR-001 : Latence loader < 100 ms p95 (mesure à l'œil).
- NFR-002 : Cache hors-MVP.
- NFR-003 : Le prompt fusionné ne dépasse pas `SKILL_PROMPT_MAX_TOKENS * 4` caractères.

## Hors-scope MVP F19

- CRUD admin (F20).
- Skills seedées (F21).
- Composition récursive, A/B testing, marketplace, drafting LLM.
- Persistence snapshot (F20).

## Success Criteria

- SC-001 : skill `skill_esg_diagnostic` (fixture test) chargée sur page+intent attendus.
- SC-002 : 2 skills candidates → priorité respectée.
- SC-003 : skill draft ou source non-verified → jamais servie.
- SC-004 : prompt fusionné < `SKILL_PROMPT_MAX_TOKENS * 4` caractères.
- SC-005 : snapshot ne lève pas, retourne identifiant version.
