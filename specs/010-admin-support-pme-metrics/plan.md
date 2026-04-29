# Implementation Plan: Support PME Admin & Métriques Admin

**Branch**: `010-admin-support-pme-metrics` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-admin-support-pme-metrics/spec.md`

## Summary

Livrer le pack support admin (lecture seule des comptes PME, reset password via Resend, révocation/régénération d'attestations, journalisation symétrique de chaque consultation admin) et le tableau de bord admin agrégé (sources, catalogue, PME, activité, LLM, coûts) pour la plateforme ESG Mefali. La feature s'appuie strictement sur les fondations F02 (auth + RLS), F04 (audit append-only via `record_audit`), F06 (back-office skeleton). Aucune nouvelle exposition de rôle, plateforme reste fermée (PME + Admin). Ajout de trois tables (`llm_usage_log`, `llm_pricing`, `email_delivery_log`) et de quelques colonnes (`revoked_at`, `revoked_by`, `revoked_reason` sur `attestations`). Cache d'agrégats in-process TTL 60s, retry email via `BackgroundTasks` FastAPI.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x / Node 20 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Resend SDK (HTTP client `httpx` en interface `EmailSender`), Nuxt 4, Vue 3, chart.js (déjà en place F01), Pinia
**Storage**: PostgreSQL 16 + pgvector (réutilisation de la base existante)
**Testing**: Pytest + pytest-asyncio + httpx (backend), Vitest + Playwright (frontend)
**Target Platform**: Backend Linux (Europe ou Afrique de l'Ouest), Frontend SSR + SPA
**Project Type**: Web application (backend + frontend monorepo)
**Performance Goals**: Dashboard < 1.5s P95, fiche compte PME < 2s P95 (10 projets / 50 candidatures / 1000 messages), recherche admin < 500ms sur 10k comptes
**Constraints**: Plateforme fermée PME + Admin uniquement, RLS active, audit append-only, hébergement Europe/Afrique de l'Ouest, RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010
**Scale/Scope**: 10k comptes PME en cible Phase 1, ~50 admins, ~5 000 appels LLM/jour ; 6 endpoints admin nouveaux + 2 pages Nuxt + 3 migrations DB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée factuelle (catalogue/référentiel) introduite : la feature lit l'existant et journalise. Les agrégats du dashboard sont calculés par requête SQL, sans nouvelle Source. | ✅ |
| P2 | Multi-tenant RLS | `llm_usage_log` porte `account_id` nullable + RLS (admin lit tout, PME lit ses lignes uniquement). `llm_pricing` global admin-only. `email_delivery_log` accessible admin uniquement. | ✅ |
| P3 | Audit log append-only | Chaque consultation admin et chaque action de support produit deux lignes via `record_audit` (F04) avec `source_of_change='admin'`. Aucune mutation hors whitelist (audit "tentative refusée"). | ✅ |
| P4 | Versioning + snapshot candidatures | `llm_pricing` versionné par `valid_from`/`valid_to` ; aucun calcul rétroactif. Pas de mutation sur les candidatures dans cette feature. | ✅ |
| P5 | Money typé | `llm_pricing.prompt_per_1k_money` et `completion_per_1k_money` utilisent le type `Money(amount, currency)` du Module 0 (XOF/EUR). | ✅ |
| P6 | Pivot Indicateur unique | N/A — la feature ne touche pas aux indicateurs ESG. | ✅ |
| P7 | Plateforme fermée | Aucun nouveau rôle. Endpoints `/admin/*` strictement protégés `require_role('admin')`. Page publique `/verify/{id}` est une lecture côté F30 ; cette feature livre seulement les hooks (champs `revoked_*`). | ✅ |
| P8 | Édition manuelle + sync LLM | Aucun champ LLM-alimenté dans cette feature ; les agrégats sont des lectures. | ✅ |
| P9 | Tool-use LLM fiable | N/A — pas de nouveau tool LLM. | ✅ |
| P10 | UX bottom sheet | Toutes les confirmations destructives (revoke, regenerate, reset) passent par un bottom sheet avec saisie de motif et bouton "Répondre librement" pour le motif. | ✅ |

**Verdict** : tous les gates passent. Pas d'amendement constitutionnel requis.

### Contraintes techniques rappelées

- Backend `.venv`, frontend `pnpm dev`, Postgres dockerisé seul.
- Hébergement Europe ou Afrique de l'Ouest uniquement.
- Langue : français par défaut.
- Pas de Redis : cache d'agrégats en mémoire process avec TTL 60s + invalidation explicite.
- Resend abstraction `EmailSender` (interface) pour faciliter futur swap (Postmark/SES).
- BackgroundTasks FastAPI pour retry email (3 tentatives, backoff 1m / 5m / 15m).

## Project Structure

### Documentation (this feature)

```text
specs/010-admin-support-pme-metrics/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI fragment)
│   └── admin-api.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── admin/
│   │   ├── routes/
│   │   │   ├── pme.py            # GET /admin/pme, /admin/pme/{id}
│   │   │   ├── users.py          # POST /admin/users/{id}/reset-password, /unlock
│   │   │   ├── attestations.py   # POST /admin/attestations/{id}/revoke, /regenerate
│   │   │   └── dashboard.py      # GET /admin/dashboard/stats, /llm-usage
│   │   ├── services/
│   │   │   ├── pme_view.py       # agrégation lecture seule + audit_admin_view
│   │   │   ├── support_actions.py
│   │   │   ├── attestation_admin.py
│   │   │   ├── dashboard_stats.py # cache TTL 60s
│   │   │   └── pii_filter.py     # filtre motif public
│   │   └── deps.py               # require_role('admin')
│   ├── email/
│   │   ├── sender.py             # EmailSender interface + ResendEmailSender
│   │   ├── templates/            # reset_password.html, attestation_revoked.html
│   │   └── retry.py              # BackgroundTasks 3-step backoff
│   ├── llm/
│   │   └── usage_logger.py       # log_llm_usage(...) appelé par wrapper LLM
│   ├── models/
│   │   ├── llm_usage_log.py
│   │   ├── llm_pricing.py
│   │   └── email_delivery_log.py
│   └── audit/
│       └── admin_view.py         # helper audit_admin_view(account_id, section)
├── alembic/versions/
│   ├── 010_a_llm_usage_log.py
│   ├── 010_b_llm_pricing.py
│   ├── 010_c_email_delivery_log.py
│   └── 010_d_attestation_revocation_columns.py
└── tests/
    ├── unit/admin/...
    ├── integration/admin/...
    └── contract/admin/...

frontend/
├── app/
│   ├── pages/admin/
│   │   ├── pme/
│   │   │   ├── index.vue         # liste paginée + recherche
│   │   │   └── [id].vue          # fiche lecture seule
│   │   └── dashboard.vue
│   ├── components/admin/
│   │   ├── PmeAccountList.vue
│   │   ├── PmeAccountDetail.vue
│   │   ├── DashboardCards.vue
│   │   ├── LlmUsageChart.vue
│   │   ├── ResetPasswordSheet.vue
│   │   ├── RevokeAttestationSheet.vue
│   │   └── RegenerateAttestationSheet.vue
│   └── composables/
│       ├── useAdminPme.ts
│       ├── useAdminDashboard.ts
│       └── useAdminActions.ts
└── tests/
    ├── unit/admin/...
    └── e2e/admin/...
```

**Structure Decision**: Web application (option 2). Backend `backend/app/admin/`, frontend `frontend/app/pages/admin/`. Réutilisation des dossiers existants (F06 a déjà créé le squelette `app/admin/` côté back et `pages/admin/` côté front).

## Phase 0 — Research

Voir [research.md](./research.md). Tous les points sont résolus :

- Provider email = Resend, abstrait derrière `EmailSender`.
- Cache agrégats = `cachetools.TTLCache` in-process, TTL 60s, invalidation programmatique sur révocation.
- Retry email = `BackgroundTasks` FastAPI + scheduler interne (3 tentatives, backoff 1m / 5m / 15m, plafond 21m).
- Filtre PII motif = regex (email / téléphone / IBAN) + lib `presidio-analyzer` light si déjà disponible, sinon regex maison.
- LLM usage log = lignes insérées par le wrapper LLM central (point d'extension dans `app/llm_client.py`).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) : nouvelles tables et colonnes.
- [contracts/admin-api.yaml](./contracts/admin-api.yaml) : OpenAPI 3.1 pour les 6 endpoints admin nouveaux.
- [quickstart.md](./quickstart.md) : pas-à-pas pour valider la feature en local.
- Mise à jour de `CLAUDE.md` (référence plan).

## Complexity Tracking

> Aucune violation de la constitution. Section vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
