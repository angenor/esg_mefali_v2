# Implementation Plan: Authentification & Rôles PME/Admin (Row-Level Security)

**Branch**: `002-auth-roles-rls` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-auth-roles-rls/spec.md`

## Summary

Mettre en place l'authentification email + mot de passe (deux rôles : `PME`, `Admin`), des jetons d'accès JWT (24 h) transportés en cookie httpOnly + Secure + SameSite=Strict, des refresh tokens rotatifs (TTL 30 j) avec détection de réutilisation, la réinitialisation de mot de passe par email (jeton 30 min usage unique), une politique de rate-limiting stricte sur les endpoints d'auth, et **l'isolation multi-tenant absolue par Row-Level Security PostgreSQL** sur toutes les tables métier portant `account_id`. Les Admins ont `account_id = NULL` et bypassent l'isolation via un setting de session contrôlé exclusivement par l'API. Une suite de tests d'isolation dédiée (≥ 5 cas) est livrée pour empêcher toute future régression de la confidentialité multi-tenant.

## Technical Context

**Language/Version**: Backend Python 3.12+ (FastAPI), Frontend TypeScript 5.x (Nuxt 4 / Vue 3.5).
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, passlib[bcrypt], python-jose[cryptography] (JWT), pydantic v2, slowapi (rate limiting), email-validator. Frontend : Nuxt 4, @vueuse/core, ofetch, nuxt-security (CSRF / headers).
**Storage**: PostgreSQL 16 + pgvector (Docker), schéma F01 (18 tables). Deux rôles SQL : `app_user` (RLS appliquée) et `migrator` (BYPASS RLS, utilisé par Alembic).
**Testing**: pytest + pytest-asyncio + httpx.AsyncClient + factory_boy ; suite RLS dédiée `tests/security/test_rls_isolation.py`. Frontend : vitest + @nuxt/test-utils ; e2e Playwright pour flux login/admin.
**Target Platform**: Backend Linux server (Docker en prod, hébergement Europe ou Afrique de l'Ouest, jamais USA). Frontend SSR Nuxt 4. Browsers modernes evergreen.
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4 séparés).
**Performance Goals**: P95 login < 300 ms, P95 /me < 100 ms, surcoût RLS sur requêtes métier < 5 ms vs sans RLS.
**Constraints**: Hébergement UE/Afrique de l'Ouest uniquement ; conformité RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 ; pas de logs de mots de passe / jetons en clair ; français par défaut ; pas de dépendance LLM dans cette feature.
**Scale/Scope**: MVP — quelques centaines de PME, < 10 admins. Tables touchées : nouvelle `refresh_tokens`, nouvelle `password_reset_tokens`, extension de `account_users` (colonnes `role`, `last_login_at`). Endpoints `/auth/*`, `/me`, `/admin/_rls_check`. Frontend : pages `/login`, `/register`, `/forgot-password`, `/reset-password`, middlewares `auth` et `admin`.

## Constitution Check

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée factuelle métier introduite par F02 (auth uniquement). | ✅ |
| P2 | Multi-tenant RLS | Cœur de F02. RLS activée sur TOUTES les tables métier `account_id NOT NULL` ; politique `USING (current_setting('app.is_admin','f')::bool OR account_id = current_setting('app.current_account_id')::uuid)`. Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Inscriptions, connexions (succès/échec), création d'admin, demandes/consommations de reset password, rotations de refresh, révocations en cascade : journalisées avec `source_of_change` ∈ {manual, admin}. | ✅ |
| P4 | Versioning + snapshot candidatures | N/A — F02 ne touche pas aux référentiels/critères/candidatures. | ✅ |
| P5 | Money typé | N/A — pas de valeurs monétaires dans F02. | ✅ |
| P6 | Pivot Indicateur unique | N/A. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | F02 N'INTRODUIT QUE deux rôles : `PME` et `Admin`. Aucun rôle Intermédiaire/Bank/Fund. | ✅ |
| P8 | Édition manuelle + sync LLM | N/A — pas d'alimentation LLM dans F02. | ✅ |
| P9 | Tool-use LLM fiable | N/A — F02 n'expose pas de tool LLM. | ✅ |
| P10 | UX bottom sheet | Les écrans d'auth sont des pages standalone (hors chat). Aucun composant interactif inline dans une bulle LLM. | ✅ |

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL 16/pgvector ; pas de LLM ni d'embeddings dans F02.
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP. La gestion des consentements et des données personnelles relève de F05 ; F02 prépare uniquement le socle d'authentification.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/002-auth-roles-rls/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── auth.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/
│   └── versions/
│       └── 0002_auth_rls.py            # ALTER account_users + create refresh_tokens + password_reset_tokens + ENABLE RLS + CREATE POLICY sur toutes les tables account-scoped + create roles app_user/migrator
├── app/
│   ├── core/
│   │   ├── security.py                 # bcrypt hashing, JWT encode/decode, CSRF token utils
│   │   ├── rate_limit.py               # slowapi config
│   │   └── session.py                  # set_local('app.current_account_id', ...) / set_local('app.is_admin', true)
│   ├── auth/
│   │   ├── router.py                   # /auth/register, /auth/login, /auth/refresh, /auth/logout, /auth/forgot-password, /auth/reset-password
│   │   ├── schemas.py                  # Pydantic v2 (RegisterIn, LoginIn, TokenOut, MeOut, ForgotIn, ResetIn)
│   │   ├── service.py                  # logique métier (création account, vérif passwd, rotation refresh, détection vol)
│   │   └── dependencies.py             # get_current_user, get_current_admin, set_session_context
│   ├── users/
│   │   ├── router.py                   # /me
│   │   └── service.py
│   ├── admin/
│   │   └── router.py                   # /admin/_rls_check
│   ├── middleware/
│   │   └── auth_session.py             # extrait JWT cookie, valide CSRF, attache user à request.state, set_local()
│   ├── models/
│   │   ├── account_user.py             # ajout role, last_login_at
│   │   ├── refresh_token.py            # nouvelle table
│   │   └── password_reset_token.py     # nouvelle table
│   ├── scripts/
│   │   └── seed_admin.py               # python -m app.scripts.seed_admin --email ... --password ...
│   ├── db.py                           # ajout : engine app_user (RLS) + helper transaction set_local
│   └── main.py                         # register routers + middleware
└── tests/
    ├── unit/
    │   ├── test_security.py
    │   └── test_password_policy.py
    ├── integration/
    │   ├── test_auth_register.py
    │   ├── test_auth_login.py
    │   ├── test_auth_refresh_rotation.py
    │   ├── test_auth_forgot_reset.py
    │   ├── test_me.py
    │   ├── test_admin_endpoints.py
    │   └── test_rate_limit.py
    └── security/
        └── test_rls_isolation.py       # ≥ 5 scénarios : SELECT, list, UPDATE, DELETE, requête sans contexte → 0 ligne

frontend/
└── app/
    ├── pages/
    │   ├── login.vue
    │   ├── register.vue
    │   ├── forgot-password.vue
    │   └── reset-password.vue
    ├── middleware/
    │   ├── auth.global.ts              # vérifie session via /me
    │   └── admin.ts                    # check role === 'admin'
    ├── composables/
    │   ├── useAuth.ts
    │   └── useCsrf.ts
    ├── stores/
    │   └── auth.ts                     # pinia store
    └── tests/
        ├── unit/
        │   └── useAuth.spec.ts
        └── e2e/
            ├── login.spec.ts
            └── admin-access.spec.ts
```

**Structure Decision**: Web application séparée — backend FastAPI sous `backend/` et frontend Nuxt 4 sous `frontend/` (déjà en place depuis F01). F02 ajoute deux nouvelles tables (`refresh_tokens`, `password_reset_tokens`), une migration Alembic activant RLS sur l'ensemble des tables `account_id NOT NULL`, deux rôles Postgres (`app_user`, `migrator`), un middleware FastAPI de session, 6 endpoints d'auth + `/me` + `/admin/_rls_check`, et 4 pages frontend + middlewares Nuxt.

## Complexity Tracking

> Aucune violation constitutionnelle à justifier — F02 est aligné par construction avec les invariants Module 0.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (aucune) | — | — |
