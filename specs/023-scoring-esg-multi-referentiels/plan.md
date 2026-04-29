# Implementation Plan: Scoring ESG Multi-Référentiels

**Branch**: `023-scoring-esg-multi-referentiels` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/023-scoring-esg-multi-referentiels/spec.md`

## Summary

Livrer le moteur de scoring ESG MVP : un service déterministe `compute_score(entity_type, entity_id, referentiel_code, account_id)` qui calcule un score sur 100 (avec sous-scores E/S/G) à partir des indicateurs publiés liés à un référentiel (F09) et des valeurs PME stockées sur `entreprise` (F11). Persistance des calculs dans une nouvelle table `score_calculation` (immutable, append-only). Trois endpoints REST `/me/scoring/...` (liste, détail, recalcul). Couverture partielle gérée par renormalisation des poids. Aucune dépendance LLM. Audit log via `record_audit`. RLS strict (policy `account_id = current_setting('app.current_account_id')`). Out of scope MVP : activation contextuelle fonds+intermédiaire, benchmarking sectoriel, historique time-series, recalcul auto debounced, formules `custom`.

## Technical Context

**Language/Version**: Python 3.11 (backend FastAPI), pas de frontend dans cette feature MVP.
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Decimal arithmetic.
**Storage**: PostgreSQL 16 + RLS (réutilisation), nouvelle table `score_calculation`.
**Testing**: pytest + pytest-asyncio, fixtures DB existantes (transaction-per-test).
**Target Platform**: Linux server (Europe / Afrique de l'Ouest).
**Project Type**: web service backend (extension du monorepo).
**Performance Goals**: < 500 ms p95 pour un calcul 30 indicateurs (cible NFR-001 = 200 ms ; marge MVP).
**Constraints**: déterminisme, RLS strict, append-only, money typé non utilisé (scores numériques sans devise), source_id présent sur chaque indicateur couvert.
**Scale/Scope**: ~10k PME × ~10 référentiels publiés × ~30 indicateurs ; 3 endpoints + 1 service + 1 modèle + 1 migration.

## Constitution Check

| # | Principle | Gate question | Status |
|---|-----------|---------------|--------|
| P1 | Sourçage anti-hallucination | `score_calculation.details_json.indicateurs_couverts[].source_id` présent et provient de `referentiel_indicateur.source_id` (NOT NULL en F09). Aucune nouvelle Source créée. | ✅ |
| P2 | Multi-tenant RLS | `score_calculation.account_id NOT NULL` + policy RLS identique aux tables F11/F12. Tous les accès `/me/scoring/...` filtrés par `account_id` JWT. | ✅ |
| P3 | Audit log append-only | Chaque calcul appelle `record_audit(entity_type='score_calculation', entity_id=row.id, source_of_change='manual'\|'system', field='compute', new={ref,score})`. Pas de mutation des lignes existantes. | ✅ |
| P4 | Versioning + snapshot | `score_calculation.referentiel_id` + `referentiel_version` snapshotent la version résolue à `t0`. Pas de rétroactivité. Le détail `details_json` capture aussi les `indicateur_id` couverts. | ✅ |
| P5 | Money typé | N/A — pas de valeur monétaire. | ✅ |
| P6 | Pivot Indicateur unique | Le calcul lit exclusivement `indicateur` + `referentiel_indicateur` ; pas de table dédiée par axe E/S/G ni par référentiel. Grille ESG = projection. | ✅ |
| P7 | Plateforme fermée | Endpoints `/me/scoring/...` réservés rôle PME (`get_current_pme`). Pas de surface intermédiaire. | ✅ |
| P8 | Édition manuelle + sync LLM | Pas de champ alimenté LLM dans cette feature. La PME édite ses valeurs côté F11/F12 ; on lit ce que F11/F12 expose. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM dans MVP (le tool `recompute_score` F17 est différé). | ✅ |
| P10 | UX bottom sheet | N/A — pas de composant UI dans cette feature MVP backend-only. | ✅ |

**Verdict** : tous les gates passent. Pas d'amendement constitutionnel requis.

## Project Structure

```text
specs/023-scoring-esg-multi-referentiels/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── scoring-api.yaml
├── checklists/
│   └── requirements.md
└── tasks.md

backend/
├── app/
│   └── scoring/
│       ├── __init__.py
│       ├── engine.py             # compute_score(...) + WeightedSumFormula
│       ├── value_source.py       # ValueSourceResolver (entreprise.<col>)
│       ├── normalizer.py         # normalize(value, seuil_min, seuil_max, value_type, enum_values)
│       ├── service.py            # orchestration : load referentiel + indicateurs, persist
│       ├── schemas.py            # Pydantic ScoreOut, ScoreDetailOut
│       └── router.py             # /me/scoring/* endpoints
├── alembic/versions/
│   └── 0016_f23_score_calculation.py
└── app/models/
    └── score_calculation.py
```

## Phase 0 - Research (résumé)

Voir [research.md](./research.md). Décisions clés :
- Une seule formule MVP : `weighted_sum` avec renormalisation des poids des indicateurs couverts (sinon coverage partielle pénaliserait artificiellement).
- Normalisation indicateurs numériques : si `seuil_min/seuil_max` présents → linéaire bornée 0-100. Sinon, valeur supposée déjà 0-100, clampée. Indicateurs `boolean` → 0 ou 100. Indicateurs `enum` → mapping ordinal selon position dans `enum_values` (premier = 0, dernier = 100). Indicateurs `text/json` → exclus en manquants MVP.
- Mapping valeur PME : table dictionnaire `VALUE_SOURCE_MAP[indicateur.code]` → callable lisant un attribut de `EntrepriseRow`. Pas de migration F09 nécessaire en MVP.
- Snapshot : `referentiel_id` + `referentiel_version` (entier). Pas de copie complète des indicateurs (déjà tracée par F04 versioning).

## Phase 1 - Design

- [data-model.md](./data-model.md) — table `score_calculation`.
- [contracts/scoring-api.yaml](./contracts/scoring-api.yaml) — 3 endpoints REST.
- [quickstart.md](./quickstart.md) — seed minimal pour reproduire un calcul.

## Phase 2 - Tasks

Voir [tasks.md](./tasks.md) (généré par `/speckit-tasks`).
