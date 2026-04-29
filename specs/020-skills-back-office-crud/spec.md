# Feature Specification: F20 — CRUD Skills Back-Office

**Feature Branch**: `020-skills-back-office-crud`
**Created**: 2026-04-29
**Status**: Draft
**Phase**: 4 — Skills (Playbooks Métier)
**Dépendances**: F04 (versioning, audit), F06 (workflow draft→published), F07 (sources verified), F19 (skill loader, table skill).

## Contexte

F19 a livré la table `skill` + le moteur (loader, fusion, snapshot interface).
F20 livre le **CRUD admin** strict avec :
- workflow `draft → published` réutilisant la sémantique F06 ;
- versioning automatique sur édition `published` (cohérent F04 + F19) ;
- validation au save : `tool_whitelist` ⊂ registry code, sources `verified`, prompt ≤ `SKILL_PROMPT_MAX_TOKENS`, activation_rules schéma JSON strict ;
- anti-injection sur `prompt_expert` ;
- eval gating MVP sur `golden_examples` (interface — exécution sandbox stub MVP, branchement F14 reportable F35) ;
- audit log enrichi avec diffs structurés.

Le frontend Vue (US2 form admin) est **DEFERRED** au scope frontend post-backend.

## User Stories (priorisées)

### US1 — Liste paginée des skills (P1)
`GET /admin/skills/` retourne items avec `name, domain, version, status, created_by, updated_at, sources_count`.

### US2 — Lecture d'une skill (P1)
`GET /admin/skills/{id}` retourne la skill complète + ETag (basé sur `version`).

### US3 — Création draft (P1)
`POST /admin/skills/` (status forcé à `draft`, version=1) avec validation au save.

### US4 — Édition (P1)
`PUT /admin/skills/{id}` :
- si `status='draft'` : update in-place + audit `update` ;
- si `status='published'` : crée une nouvelle ligne `(name, version+1, status='draft')`.

### US5 — Publication (P1)
`POST /admin/skills/{id}/publish` :
- toutes les sources liées doivent être `verified` (sinon 422 cohérent F06) ;
- validations re-jouées (double check) ;
- eval gating optionnel — header `X-Skip-Eval-Gating: true` autorisé en MVP, override loggé ;
- transition `draft → published`, audit `publish`.

### US6 — Versioning historisé (P1)
`GET /admin/skills/{id}/versions` retourne toutes versions partageant le même `name`.

### US7 — Anti-injection (P1)
Module `app/skills/anti_injection.py:scan(text) -> list[Issue]`. Patterns :
- "ignore previous instructions" (insensible casse) ;
- "you are now ...", "tu es désormais ..." ;
- "</system>", "<system>", "system:" en début de ligne ;
- regex secrets : `sk-[A-Za-z0-9]{20,}`, `ghp_[A-Za-z0-9]{20,}` ;
- caractères de contrôle (sauf `\n`, `\t`).
Si issues détectées → 422 `prompt_injection_detected`. Override via flag `override_injection: true` + `override_reason` (loggé audit).

### US8 — Eval runner (P1 — interface)
`POST /admin/skills/{id}/run-eval` exécute les `golden_examples` (stub MVP) :
- pour chaque example, `tool_match` si `expected_tool ∈ skill.tool_whitelist`, `payload_valid` si `expected_payload` est un dict non vide ;
- retourne `{tool_match_rate, payload_valid_rate, fallback_rate, examples_count, gating_pass}` ;
- branchement réel pipeline F14 reportable F35.

### US9 — Estimation de tokens (P1)
`POST /admin/skills/_estimate-tokens` body `{text: str}` → `{tokens: int}` (estimation `len//4`).

### US10 — Audit log structuré (P1)
Chaque mutation logge `audit_log` avec `before/after` par section.

## Exigences fonctionnelles

- **FR-001** : Endpoints REST listés.
- **FR-002** : Transitions `draft → published`.
- **FR-003** : Validation `app/skills/validation.py:validate_skill_payload(payload, db)` (tool_whitelist, sources verified, prompt size, activation_rules, golden ≥ 5).
- **FR-004** : Anti-injection bloquant + override loggé.
- **FR-005** : Versioning `(name, version+1)` sur édition published.
- **FR-006** : Publish rejette 422 si source non `verified`.
- **FR-007** : Eval gating `SKILL_EVAL_GATING_TOOL_MATCH_MIN=0.8`, `SKILL_EVAL_GATING_PAYLOAD_VALID_MIN=0.9`. Override header MVP.
- **FR-008** : Audit log via `write_admin_event` avec diff structuré.
- **FR-009** : `name` immutable après création.
- **FR-010** : `GET /admin/skills/{id}/versions` par `name`.

## Exigences non-fonctionnelles

- NFR-001 : Save < 2 s.
- NFR-002 : Eval runner MVP < 1 s.
- NFR-003 : Diffs structurés par section.
- NFR-004 : Hot reload F19 (sans cache > 60 s).

## Hors-scope MVP

- Frontend Vue admin — DEFERRED.
- Eval continu / pipeline F14 réel — F35.
- Marketplace, copie, suggestions LLM — post-MVP.

## Success Criteria

- SC-001 : Création + édit + run-eval + publish < 30 min.
- SC-002 : Source `pending` → 422.
- SC-003 : Injection → 422.
- SC-004 : Gating fail → publish bloqué (sauf override).
- SC-005 : v1 published → v2 draft, v1 reste accessible.
- SC-006 : Couverture tests `app/skills/` ≥ 80%.
