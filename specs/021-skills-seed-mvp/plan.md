# Implementation Plan: Seed des Skills MVP (F21)

**Branch**: `021-skills-seed-mvp` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-skills-seed-mvp/spec.md`

## Summary

Livrer un script de seed Python idempotent qui :
- charge des fixtures YAML (sous `backend/scripts/seeds/skills/`),
- crée/met à jour 3 skills critiques (`skill_esg_diagnostic`, `skill_score_gcf`, `skill_dossier_gcf_via_boad`) en `published` quand sources `verified`, sinon `draft`,
- crée 6+ shells `draft` (skill_score_boad, skill_score_ifc, skill_carbon_calc, skill_dossier_sunref_ecobank, skill_dossier_fem_via_pnud, skill_intermediaire_boad, skill_attestation, skill_credit_score),
- inclut 5 golden examples par skill critique (champ JSONB `golden_examples` du modèle `Skill` F19, pas de table dédiée),
- vérifie la `tool_whitelist` via `app.orchestrator.tool_registry.TOOL_REGISTRY` (runtime, F14),
- réutilise `app.skills.validation.validate_skill_payload` (F20) pour cohérence,
- bumpe `version` uniquement si content_hash change.

Tests pytest unitaires + intégration ≥ 80 % de couverture sur le code F21 ajouté.

## Technical Context

**Language/Version**: Python 3.11+ (venv local `backend/.venv`)
**Primary Dependencies**: SQLAlchemy 2.x, FastAPI, PyYAML (à ajouter si absent), pytest, ruff
**Storage**: PostgreSQL via `app.db.get_db`, modèle `Skill` (F19) avec colonne JSONB `golden_examples` ; pas de nouvelle table.
**Testing**: pytest avec fixtures `backend/tests/conftest.py` existant ; couverture `--cov=backend/scripts --cov=backend/app/skills/seed_helpers`.
**Target Platform**: CLI script (`python -m backend.scripts.seed_skills`), exécuté en dev local.
**Project Type**: Backend mono-repo (FastAPI), CLI utility script.
**Performance Goals**: Run complet < 30 s sur dev local (SC-002).
**Constraints**: Idempotent, non-destructif (jamais published→draft), bump version basé content_hash, exit code non-zéro si une skill critique skippée.
**Scale/Scope**: ~10 skills, ≤ 15 golden examples, ≤ 30 sources liées au total.

## Constitution Check

| # | Principle | Gate question | Status |
|---|-----------|--------------|--------|
| P1 | Sourçage anti-hallucination | Skills critiques liées à `Source` `verified` (sinon draft) ? | PASS |
| P2 | Multi-tenant RLS | F21 manipule `skill` (catalogue global) — RLS non applicable. | N/A |
| P3 | Audit log append-only | Le seed log un événement `admin_event` (`source_of_change=import`) par skill créée/MAJ. | PASS |
| P4 | Versioning + snapshot | Bump `version` si content_hash change ; jamais published→draft. | PASS |
| P5 | Money typé | Pas de valeur monétaire dans F21. | N/A |
| P6 | Pivot Indicateur unique | F21 ne touche pas aux indicateurs. | N/A |
| P7 | Plateforme fermée | Pas de rôle Intermédiaire ajouté ; skills sont du contenu admin. | PASS |
| P8 | Édition manuelle + sync LLM | Le seed n'écrase jamais un `prompt_expert` modifié manuellement (sauf `--force`). | PASS |
| P9 | Tool-use LLM fiable | Tool whitelist validée contre TOOL_REGISTRY F14 ; eval gating prévu via `validate_skill_payload`. | PASS |
| P10 | UX bottom sheet | F21 backend uniquement, pas de UI. | N/A |

**Gates**: tous PASS / N/A. Pas de violation à tracer.

### Contraintes techniques (rappel)

- Stack imposée : FastAPI + PostgreSQL ; pas de modification de migrations Alembic globales (F19/F20 fournissent déjà `skill` et `skill_source`).
- Pas de dépendance LLM live dans le script seed (eval LLM réel = manuel post-seed).
- Langue par défaut FR.

## Project Structure

### Documentation (this feature)

```text
specs/021-skills-seed-mvp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── seed-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── skills/
│       └── seed_helpers.py        # NEW : content_hash, load_yaml, build_payload
├── scripts/
│   ├── seed_skills.py             # NEW : entry-point CLI (idempotent)
│   └── seeds/
│       └── skills/
│           ├── critical/
│           │   ├── skill_esg_diagnostic.yaml
│           │   ├── skill_score_gcf.yaml
│           │   └── skill_dossier_gcf_via_boad.yaml
│           └── shells/
│               ├── skill_score_boad.yaml
│               ├── skill_score_ifc.yaml
│               ├── skill_carbon_calc.yaml
│               ├── skill_dossier_sunref_ecobank.yaml
│               ├── skill_dossier_fem_via_pnud.yaml
│               ├── skill_intermediaire_boad.yaml
│               ├── skill_attestation.yaml
│               └── skill_credit_score.yaml
└── tests/
    ├── unit/
    │   └── test_seed_helpers.py       # NEW
    └── integration/
        └── test_seed_skills_e2e.py    # NEW (intégration BDD)
```

**Structure Decision**: monolithic backend, fichiers nouveaux uniquement (`backend/app/skills/seed_helpers.py`, `backend/scripts/seed_skills.py`, `backend/scripts/seeds/skills/`, `backend/tests/unit|integration/`). Aucune modification de fichier existant critique. Pas de nouvelle migration Alembic.

## Complexity Tracking

Aucune violation à tracer.
