# Phase 0 — Research (F21)

## Decision 1 — Format de fixtures

**Decision**: YAML (PyYAML).
**Rationale**: lisibilité prompts multi-ligne, commentaires possibles pour notes métier. Fixé dans Clarifications session 2026-04-29.
**Alternatives considered**: JSON (rejet : pas de commentaires, multi-ligne moins ergonomique) ; TOML (rejet : moins courant en Python data-fixtures).

## Decision 2 — Stockage golden examples

**Decision**: champ JSONB `golden_examples` du modèle `Skill` (F19), pas de table dédiée.
**Rationale**: la table `skill` (F19, `backend/app/models/skill.py`) expose déjà `golden_examples: list[Any]` JSONB ; pas besoin de migration.
**Alternatives considered**: nouvelle table `golden_example` (rejet : sur-ingénierie pour ≤ 15 lignes ; rupture avec F19/F20 qui valident déjà ce champ via `validate_skill_payload`).

## Decision 3 — Validation tool registry

**Decision**: import runtime de `app.orchestrator.tool_registry.TOOL_REGISTRY`.
**Rationale**: source de vérité unique F14, déjà utilisée par `app.skills.validation._known_tools()`.
**Alternatives considered**: liste statique YAML versionnée (rejet : drift garanti).

## Decision 4 — Comportement source non `verified`

**Decision**: skill basculée en `draft`, warning loggué, pas d'échec global.
**Rationale**: F21 ne doit pas dépendre d'un seed F07 complet en dev local. Cohérent avec FR-014.

## Decision 5 — Stratégie de versioning

**Decision**: bump `version` (Integer, default 1) uniquement si `content_hash(prompt_expert + activation_rules + tool_whitelist + procedure)` diffère.
**Rationale**: idempotence stricte (re-run sans changement = pas de bump). Cohérent avec FR-013.
**Alternatives considered**: bump à chaque run (rejet : pollution historique) ; pas de bump (rejet : perd la sémantique de version F19/F20).

## Decision 6 — Tool inconnu dans whitelist

**Decision**: skip la skill, log error, exit code 1 final si ≥ 1 skip.
**Rationale**: prévient l'insertion d'une skill cassée tout en permettant aux autres skills de réussir. Cohérent avec FR-005.

## Decision 7 — Audit log

**Decision**: insérer un row `admin_event` (table existante de F06/F20) par skill créée/MAJ, avec `source_of_change='import'`.
**Rationale**: cohérence Constitution P3 (append-only). Réutilise `app.admin.audit.write_admin_event` si signature compatible ; sinon log applicatif simple.

## Open / deferred

- Contenu réel des `prompt_expert` métier validé humain-in-the-loop : MVP insère un placeholder structuré (sections Étape 1..N). À itérer hors scope sprint F21.
- Eval LLM live (≥ 0.8 tool_match_rate) : exécuté manuellement via endpoint `/admin/skills/{id}/run-eval` post-seed (hors scope script F21).
