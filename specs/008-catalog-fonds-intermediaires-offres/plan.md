# Implementation Plan: F08 — Catalogue Fonds, Intermédiaires & Offres

**Branch**: `008-catalog-fonds-intermediaires-offres` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-catalog-fonds-intermediaires-offres/spec.md`

## Summary

Livrer la modélisation à 3 entités (FondsSource, Intermediaire, Offre) reliées par une table d'accréditation datée, avec calcul `effective` déterministe (intersection critères / union documents) et comparateur d'intermédiaires. Réutilise massivement le squelette F06 (registry, crud_router générique, ETag/If-Match, search trigram, publish gate) et la canonicalisation Source de F07. Toutes les opérations sont auditées (F04) ; les Money utilisent le type F01 (peg FCFA-EUR 655.957). Les tables sont GLOBALES (pas d'`account_id`), précédent posé par F07 pour les entités catalogue partagées.

## Technical Context

**Language/Version** : Python 3.12+ (backend) ; TypeScript 5.x (frontend Nuxt 4).
**Primary Dependencies** :
- Backend : FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 (`extra='forbid'`), httpx, `decimal.Decimal` pour Money.
- Frontend : Nuxt 4 (Composition API), Pinia, TailwindCSS v4, gsap (bottom sheet), `@vueuse/core`.
- Réutilisé F06 : `app.core.registry`, `app.api.admin.crud_router`, `app.core.etag`, `app.core.publish_gate`, `app.core.search_trigram`.
- Réutilisé F07 : `app.services.source_canonical`.
- Réutilisé F04 : `app.services.audit_log`.
- Réutilisé F01 : `app.core.money` (type Money, peg FCFA-EUR 655.957).
**Storage** : PostgreSQL 16 + pgvector (dockerisé via docker-compose.yml racine), 4 nouvelles tables (`fonds_source`, `intermediaire`, `accreditation`, `offre`), index GIN/btree, indexes trigram pour recherche.
**Testing** : pytest + pytest-asyncio + httpx AsyncClient + factory-boy (backend) ; Vitest + @nuxt/test-utils + Playwright (frontend, smoke E2E sur comparateur).
**Target Platform** : Linux server (Europe ou Afrique de l'Ouest, jamais USA — contrainte constitution).
**Project Type** : Web application (backend FastAPI + frontend Nuxt 4 séparés).
**Performance Goals** : `GET /admin/offres/{id}/effective` < 200 ms p95. Comparateur < 2 s pour 10 offres dérivées (SC-003). Liste paginée < 300 ms p95 pour 500 offres.
**Constraints** :
- Calcul `effective` déterministe testé sur 5 cas d'école (NFR-001/SC-002).
- 100 % des opérations CRUD auditées avec diff JSON (FR-012).
- Publish gate : au moins 1 source `verified` rattachée, sinon 409 (FR-011).
- ETag/If-Match obligatoire sur tous PUT/DELETE (FR-013).
- Money typé Decimal partout, peg FCFA-EUR 655.957 (FR-016, P5 constitution).
**Scale/Scope** : MVP 100 fonds, 200 intermédiaires, 500 offres ; archi dimensionnable 10×.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question | Status | Notes |
|---|-----------|---------------|--------|-------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle pointe-t-elle vers une `Source` `verified` ? | ✅ | FR-011 publish gate ; `source_ids[]` sur Fonds/Intermédiaire/Offre ; `source_id` sur Accreditation ; chaque critère JSONB porte `source_id`. |
| P2 | Multi-tenant RLS | Tables avec `account_id` + RLS ? | ⚠ déféré justifié | **Catalogue global** — Fonds/Intermédiaires/Offres sont partagés à toute la plateforme (précédent F07 pour Source). RLS appliquée GLOBALEMENT : `SELECT` autorisé pour utilisateurs authentifiés sur `status='published'` ; `INSERT/UPDATE/DELETE` réservé au rôle `admin`. Voir Complexity Tracking. |
| P3 | Audit log append-only | Toute mutation journalisée ? | ✅ | FR-012 ; tous les CRUD passent par `audit_log` (F04) avec diff JSON et `source_of_change='admin'`. |
| P4 | Versioning + snapshot candidatures | `version`, `valid_from`, `valid_to` ? | ✅ | F04 versioning appliqué à Fonds/Intermédiaire/Offre/Accreditation. Pas de `snapshot_json` ici (candidatures = F26). |
| P5 | Money typé | `Money = {amount, currency}` partout ? | ✅ | FR-016 ; `plafond_money`, `plancher_money`, plafonds Accreditation, `frais_effectifs` calculés ; type `Money` F01. |
| P6 | Pivot Indicateur unique | Données ESG via `Indicateur` ? | ✅ | F08 ne stocke pas de données ESG PME ; les critères/seuils des Fonds référenceront (à terme) le pivot Indicateur F09. |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôle Intermédiaire ? | ✅ | `Intermediaire` est uniquement une **entité de catalogue** ; aucun rôle utilisateur créé. Pas de webhook ni de flux push. |
| P8 | Édition manuelle + sync LLM | Champs LLM modifiables ? | ✅ | F08 est purement back-office admin manuel ; pas d'écriture LLM. |
| P9 | Tool-use LLM fiable | Nouveaux tools LangGraph ? | ✅ N/A | F08 n'introduit pas de tool LLM ; les futurs tools `search_offre` (F25) consommeront `GET /catalog/offres`. |
| P10 | UX bottom sheet | Composants interactifs en bottom sheet ? | ✅ | Tous les formulaires admin (création Fonds/Intermédiaire/Accreditation/Offre) en bottom sheet animé gsap. Le comparateur est une vue d'affichage. |

**Verdict** : Aucun ❌. Un ⚠ déféré justifié sur P2 (catalogue global), aligné avec le précédent F07. Voir Complexity Tracking.

### Contraintes techniques (rappel) appliquées

- Backend `.venv`, Postgres dockerisé via `docker-compose.yml` racine, frontend `pnpm dev`.
- Hébergement EU/AO uniquement.
- Conformité RGPD/loi ivoirienne — F08 ne traite pas de données personnelles PME (catalogue partagé verrouillé), donc pas d'impact direct, mais auth requise (plateforme fermée).
- Langue : `accepted_languages` côté Offre (FR par défaut, EN explicite).

## Project Structure

### Documentation (this feature)

```text
specs/008-catalog-fonds-intermediaires-offres/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── admin-fonds.openapi.yaml
│   ├── admin-intermediaires.openapi.yaml
│   ├── admin-accreditations.openapi.yaml
│   ├── admin-offres.openapi.yaml
│   └── catalog-public.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── core/
│   │   ├── money.py                       # F01
│   │   ├── etag.py                        # F06
│   │   ├── publish_gate.py                # F06
│   │   ├── registry.py                    # F06
│   │   ├── search_trigram.py              # F06
│   │   └── effective_calculator.py        # NOUVEAU
│   ├── models/
│   │   ├── fonds_source.py                # NOUVEAU
│   │   ├── intermediaire.py               # NOUVEAU
│   │   ├── accreditation.py               # NOUVEAU
│   │   └── offre.py                       # NOUVEAU
│   ├── schemas/
│   │   ├── fonds_source.py                # Pydantic v2 strict
│   │   ├── intermediaire.py
│   │   ├── accreditation.py
│   │   ├── offre.py
│   │   ├── critere.py                     # JSONB typé
│   │   └── effective.py                   # arbre 2 niveaux
│   ├── services/
│   │   ├── audit_log.py                   # F04
│   │   ├── source_canonical.py            # F07
│   │   ├── effective_calculator.py        # wrapper du core
│   │   ├── needs_refresh_hook.py          # NOUVEAU
│   │   └── outdated_lazy_check.py         # NOUVEAU
│   ├── api/
│   │   ├── admin/
│   │   │   ├── crud_router.py             # F06
│   │   │   ├── fonds.py                   # FR-001/006
│   │   │   ├── intermediaires.py          # FR-002/007
│   │   │   ├── accreditations.py          # FR-003
│   │   │   ├── offres.py                  # FR-004/005/009/010
│   │   │   └── recheck.py                 # POST /admin/offres/recheck-status
│   │   └── catalog/                       # PME public
│   │       ├── fonds.py
│   │       ├── intermediaires.py
│   │       └── offres.py                  # FR-020
│   └── db/
│       └── alembic/versions/
│           └── 008_xxxx_catalog_fonds_offre.py
└── tests/
    ├── unit/
    │   ├── test_effective_calculator.py        # SC-002 — 5 cas d'école
    │   ├── test_needs_refresh_hook.py
    │   └── test_outdated_lazy_check.py
    ├── integration/
    │   ├── test_admin_fonds.py
    │   ├── test_admin_intermediaires.py
    │   ├── test_admin_accreditations.py
    │   ├── test_admin_offres.py
    │   ├── test_catalog_public.py
    │   └── test_publish_gate_f08.py
    └── e2e/                                    # smoke via Playwright frontend

frontend/
├── pages/admin/
│   ├── fonds/
│   │   ├── index.vue
│   │   ├── [id]/
│   │   │   ├── index.vue
│   │   │   └── comparator.vue          # FR-008
│   │   └── nouveau.vue
│   ├── intermediaires/{index,nouveau,[id]}.vue
│   ├── accreditations/{index,nouveau}.vue
│   └── offres/
│       ├── index.vue
│       ├── [id]/{index,refresh}.vue
│       └── nouveau.vue
├── components/catalog/
│   ├── FondsForm.vue
│   ├── IntermediaireForm.vue
│   ├── AccreditationForm.vue
│   ├── OffreForm.vue
│   ├── CritereJsonbEditor.vue
│   ├── EffectiveTree.vue
│   └── ComparatorTable.vue
├── components/shared/
│   ├── BottomSheet.vue                  # F06
│   ├── EtagGuard.vue                    # F06
│   └── SourceLinker.vue                 # F07
├── stores/{fonds,intermediaires,accreditations,offres}.ts
├── composables/{useFondsApi,useIntermediairesApi,useAccreditationsApi,useOffresApi,useEffective}.ts
└── tests/{unit,e2e}
```

**Structure Decision** : Web application (Option 2). Aucune nouvelle racine.

## Phase 0 — Outline & Research

Voir [research.md](./research.md). Sujets résolus :
1. Schéma JSONB typé pour critères.
2. Algorithme intersection critères (règles typées par operator).
3. Hook `needs_refresh` synchrone (vs queue).
4. Outdated detection lazy (vs cron).
5. Exposition catalogue PME (`/catalog/*`).
6. Money pour plafonds multi-devises.

## Phase 1 — Design & Contracts

### Data model
Voir [data-model.md](./data-model.md). 4 tables : `fonds_source`, `intermediaire`, `accreditation`, `offre`.

### API contracts
Voir [contracts/](./contracts/). 5 fichiers OpenAPI 3.1.

### Quickstart
Voir [quickstart.md](./quickstart.md).

### Agent context update
`CLAUDE.md` racine pointera entre `<!-- SPECKIT START -->` et `<!-- SPECKIT END -->` vers `specs/008-catalog-fonds-intermediaires-offres/plan.md`.

## Tests Strategy

| Couche | Outils | Couverture cible |
|--------|--------|------------------|
| Unit (calc) | pytest, paramétrage | 100 % branches `effective_calculator` ; 5 cas d'école nominatifs (SC-002) |
| Unit (services) | pytest | `needs_refresh_hook`, `outdated_lazy_check`, validators Pydantic |
| Integration | pytest-asyncio + httpx + Postgres testcontainers | CRUD × 4 entités, publish gate, ETag/If-Match concurrency, RLS, `/effective`, `/comparator`, `/recheck-status` |
| Frontend unit | Vitest | Stores Pinia, composables API, validation form |
| E2E | Playwright | Smoke : Fonds → Inter → Accreditation → Offre → `/effective` ; comparateur 3 offres alignées |

Cible globale 80 % couverture. TDD obligatoire sur `effective_calculator`.

## Phasing

### Phase A — Schéma & Backend CRUD (P1)
- A1 : Migration Alembic 4 tables + index + RLS.
- A2 : Modèles SQLAlchemy 2 + schemas Pydantic v2 strict.
- A3 : Enregistrement registry F06, branchement crud_router générique.
- A4 : Publish gate F06 + audit_log F04.
- A5 : Tests integration CRUD + ETag.

### Phase B — Calcul effective (P1)
- B1 : `effective_calculator.py` core (intersection typée, union docs, sommes).
- B2 : Endpoint `GET /admin/offres/{id}/effective`.
- B3 : Tests unitaires 5 cas d'école.

### Phase C — Lifecycle & cohérence (P1)
- C1 : Hook `needs_refresh` synchrone branché aux PUT Fonds/Intermédiaire `published`.
- C2 : `outdated_lazy_check` greffé aux GET Offres + endpoint `POST /admin/offres/recheck-status`.
- C3 : Tests integration cohérence.

### Phase D — Endpoints lecture PME (P1)
- D1 : Routes `/catalog/*` filtrées status, auth rôle PME.
- D2 : Tests integration RLS.

### Phase E — Frontend admin (P1)
- E1 : Pages liste paginée + recherche trigram.
- E2 : Bottom sheets de création/édition (BottomSheet.vue F06 réutilisé).
- E3 : Détail Offre `EffectiveTree.vue`.
- E4 : Page comparator (FR-008).
- E5 : Smoke E2E Playwright.

### Phase F — Submission mode (P2)
- F1 : ENUM `submission_mode`, héritage deadline.
- F2 : Tests `rolling` vs `call_for_proposals`.

### Phase G — Hardening
- G1 : Quickstart + curl examples.
- G2 : Doc OpenAPI auto.
- G3 : Revue accessibilité bottom sheets.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| P2 RLS — pas d'`account_id` sur Fonds/Intermédiaire/Offre/Accreditation | Le catalogue est partagé : 1 seul corpus pour toutes les PME. La duplication par account_id n'a pas de sens métier. Précédent F07 a posé la même règle pour `Source`. | Forcer un `account_id=NULL_TENANT` artificiel rejeté car (a) tordrait l'enforcement RLS, (b) compliquerait `crud_router` réutilisé, (c) n'apporte aucune isolation supplémentaire. RLS appliquée sur politique différente : `SELECT` ouvert si `status='published'` aux authentifiés ; `INSERT/UPDATE/DELETE` restreint au rôle `admin`. Politique testée explicitement. |

## Outputs

- `plan.md` (ce fichier)
- `research.md`
- `data-model.md`
- `contracts/*.openapi.yaml` (5 fichiers)
- `quickstart.md`
- `tasks.md` généré par `/speckit-tasks`
