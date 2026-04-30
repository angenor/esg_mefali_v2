# Implementation Plan: F26 — Générateur de Dossiers de Candidature

**Branch**: `026-generateur-dossiers-candidatures` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Backend MVP livrant le générateur de dossiers de candidature : pour une candidature donnée, le service charge la skill associée à l'offre (F19/F21), pré-remplit les sections `auto` à partir du profil entreprise (F11), du projet (F12) et des scores ESG (F23), fait rédiger les sections `narratif` par la skill (LLM stub injectable côté tests), persiste un `Dossier` avec sections markdown et statut, expose les endpoints PME (lancer, consulter, éditer, regénérer, exporter Word/PDF, checklist documentaire), produit l'annexe sources (F03) auto-déduite des citations, et garantit RLS + audit append-only.

**Scope MVP backend uniquement.** Frontend Nuxt, EN exhaustif, multi-candidatures parallèles, streaming SSE, attestation ESG → marqués `[DEFERRED]`.

## Technical Context

- **Language/Version**: Python 3.12 (backend, conforme au `pyproject.toml`)
- **Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, python-docx (export Word), weasyprint (export PDF, déjà présent F24)
- **Storage**: PostgreSQL 16 + pgvector (réutilisation, 1 nouvelle migration `0018_f26_template_dossier_dossier`)
- **Testing**: Pytest + pytest-asyncio + httpx (backend) ; tests stub pour LLM (interface `LLMNarrativeWriter`)
- **Target Platform**: Backend Linux ; pas de frontend MVP
- **Performance Goals**: génération séquentielle 10–15 sections < 90s avec LLM stub (tests mockés < 1s)
- **Constraints**: RLS active (PME ne voit que ses dossiers), audit append-only via `record_audit` (F04), Money typé pour les montants, sources F03 déduites des citations
- **Scale/Scope**: 1 nouvelle table `template_dossier`, 1 nouvelle table `dossier`, 6 endpoints PME, 1 endpoint admin (CRUD template), 1 service générateur, 1 service exporter

## Constitution Check

| # | Principle | Status | Justification |
|---|-----------|--------|---------------|
| P1 | Sourçage anti-hallucination | ✅ | Sections narratives chiffrées doivent porter ≥1 citation Source ; validateur intégré au service ; annexe sources auto. |
| P2 | Multi-tenant RLS | ✅ | `dossier` porte `account_id` + RLS ; templates restent admin-only ; endpoints PME `Depends(get_current_pme)`. |
| P3 | Audit append-only | ✅ | `record_audit` à chaque create/edit/regenerate/export. |
| P4 | Versioning + snapshot candidature | ✅ | `dossier.version` simple incrémentale ; `dossier.candidature_id` FK figée ; aucune mutation sur `candidature.snapshot_json`. |
| P5 | Money typé | ✅ | Sections `auto` qui mentionnent un montant utilisent `Money` (`app/utils/money.py`). |
| P6 | Pivot indicateur unique | ✅ | N/A — pas de touche aux indicateurs. |
| P7 | Plateforme fermée | ✅ | Endpoints PME `/me/...` + admin `/admin/template-dossier` strictement protégés. |
| P8 | Édition manuelle + sync LLM | ✅ | L'édition manuelle d'une section passe le statut `en_revision` ; la regénération écrase. |
| P9 | Tool-use LLM fiable | ✅ | Tool LLM `generate_dossier(candidature_id, language?)` whitelisté ; erreurs structurées. |
| P10 | UX bottom sheet | ✅ | N/A — backend MVP, frontend différé. |

**Verdict**: tous les gates passent.

## Project Structure

```text
backend/
├── app/
│   ├── dossier/                            # NEW package F26
│   │   ├── __init__.py
│   │   ├── schemas.py                      # Pydantic
│   │   ├── llm_writer.py                   # interface LLMNarrativeWriter (stub injectable)
│   │   ├── prefill.py                      # remplissage des sections "auto"
│   │   ├── service.py                      # DossierGeneratorService
│   │   ├── checklist_service.py
│   │   ├── exporter.py                     # Word + PDF
│   │   ├── source_extractor.py
│   │   ├── validators.py                   # règle "chiffre → ≥1 source"
│   │   ├── repository.py                   # CRUD SQLAlchemy
│   │   ├── tool.py                         # tool LLM generate_dossier
│   │   └── router.py
│   ├── models/
│   │   ├── template_dossier.py             # NEW
│   │   └── dossier.py                      # NEW
│   └── main.py                             # MODIFIED: include router
├── alembic/versions/
│   └── 0018_f26_template_dossier_dossier.py
└── tests/
    ├── unit/dossier/
    └── integration/dossier/

specs/026-generateur-dossiers-candidatures/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/requirements.md
```

**Structure Decision** : nouveau package `app/dossier/` (cohérent avec `app/scoring/`, `app/matching/`, `app/rapports/`).

## Phase 0 — Research

- **Migration unique** : ajout `template_dossier` + `dossier`. RLS sur `dossier` via `account_id`. Pas d'altération aux tables existantes.
- **Skill ↔ offre** : la liaison `skill_id ↔ offre` est portée par `template_dossier.skill_id`. Si pas de template publié pour l'offre → erreur métier `template_not_found`.
- **LLM stub** : interface `LLMNarrativeWriter.write_section(skill, section_spec, context, language) -> {markdown, source_ids, length}`. Implémentation par défaut `EchoWriter` pour MVP/tests (markdown formaté + citations dérivées des sources de la skill).
- **Money** : conversion via `app/utils/money.py` (taux 655.957) pour la section "Plan de financement".
- **Audit** : `record_audit` cibles : `dossier_created`, `dossier_section_edited`, `dossier_section_regenerated`, `dossier_exported`.
- **Sources** : extraction par regex `[[source:UUID]]` dans markdown ; dédoublonnage ensembliste.
- **Word/PDF** : `python-docx` pour `.docx`, `weasyprint` pour PDF (déjà installé F24). Fichiers stockés sous `storage/dossiers/{account_id}/{dossier_id}/`.
- **Checklist** : union `document_requis` filtrés par `fonds_id` (de l'offre) ∪ `intermediaire_id` (de l'offre), dédoublonnés par `name` lowercased trimmed ; status `present` calculé via lookup `document_entreprise` (F22).

## Phase 1 — Design

### Endpoints

```
POST   /me/candidatures/{candidature_id}/dossier              body {language?}
GET    /me/candidatures/{candidature_id}/dossier
PATCH  /me/candidatures/{candidature_id}/dossier/sections/{section_key}  body {markdown}
POST   /me/candidatures/{candidature_id}/dossier/sections/{section_key}/regenerate
POST   /me/candidatures/{candidature_id}/dossier/export?format=word|pdf
GET    /me/candidatures/{candidature_id}/dossier/checklist

POST   /admin/template-dossier                              body {offre_id, name, language, structure_json, skill_id?}
GET    /admin/template-dossier/{id}
PATCH  /admin/template-dossier/{id}                          body {status?, structure_json?, ...}
```

### Erreurs standardisées

| Code | HTTP |
|------|------|
| `candidature_not_found` | 404 |
| `template_not_found` | 422 |
| `skill_not_published` | 422 |
| `language_not_accepted` | 422 |
| `dossier_not_found` | 404 |
| `section_not_found` | 404 |
| `validation_error` | 422 |
| `export_failed` | 500 |
| `unauthorized` | 403 |

### Modèle de données (résumé)

`template_dossier`:
- `id` UUID PK
- `offre_id` UUID FK → offre
- `skill_id` UUID FK NULL → skill
- `name` TEXT
- `language` TEXT (`fr` | `en`)
- `structure_json` JSONB — `[{key, title, type:'auto'|'narratif'|'document', skill_section_id?, target_length?, prefill_source?}]`
- `status` TEXT (`draft` | `published` | `archived`)
- `version` INT
- `source_id` UUID FK NULL → source
- `created_by` UUID FK NULL → account_user
- `created_at`, `updated_at`

`dossier`:
- `id` UUID PK
- `account_id` UUID FK NOT NULL (RLS)
- `candidature_id` UUID FK UNIQUE NOT NULL → candidature
- `template_id` UUID FK → template_dossier
- `language` TEXT NOT NULL (`fr` | `en`)
- `status` TEXT (`en_generation` | `genere` | `en_revision` | `exporte`)
- `sections_json` JSONB — `[{key, title, type, markdown, source_ids:[uuid], length}]`
- `source_ids` UUID[] (annexe agrégée)
- `version` INT default 1
- `word_file_path` TEXT NULL
- `pdf_file_path` TEXT NULL
- `generated_at`, `created_at`, `updated_at`

### RLS

- `dossier` : SELECT/INSERT/UPDATE/DELETE par `account_id` courant ; admin bypass via `app.bypass_rls=on`.
- `template_dossier` : admin-only.

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

Aucune violation. Une seule migration neuve, une seule famille d'endpoints, un seul service public.
