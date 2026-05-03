# Implementation Plan: Onboarding Tour & Auth UX Polish (F42)

**Branch**: `042-onboarding-auth-polish` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/042-onboarding-auth-polish/spec.md`

## Summary

Polir les pages d'authentification existantes (login, register, forgot-password, reset-password, index public) et installer un onboarding multi-étapes (wizard d'inscription 3 steps + tour guidé 6 étapes + empty state landing) qui amène la PME jusqu'à son premier chat fonctionnel. La feature est **principalement frontend** (Nuxt 4) ; côté backend, elle ajoute une fine couche de préférences utilisateur (`onboarding_state` typé) exposée par `GET/PATCH /me/preferences`. Le backend d'auth (F02) est déjà complet : cookies sécurisés, REFRESH_TTL = 30 jours (aligné sur la clarification "Rester connecté"), `password_reset_tokens` (table dédiée déjà migrée), endpoints `/auth/register`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`. Cette feature consomme l'existant et y greffe : (1) durcissement de la force de mot de passe (zxcvbn ≥ 3/4), (2) invalidation de toutes les sessions à la suite d'un reset réussi, (3) durée de validité du token reset = 60 min (à vérifier vs F02 et ajuster si besoin), (4) endpoint `/me/preferences` pour persister l'état du tour, (5) lecture de `completion_pct` profil entreprise (F11 — `entreprise/completeness.py`). Le tour utilise driver.js déjà installé ; gsap pour transitions ; respect strict de `prefers-reduced-motion` via le composable existant `useReducedMotion`. i18n : pas de plugin officiel installé — chaînes centralisées dans un fichier statique `frontend/app/locales/fr.ts` consommé via un composable léger `useT()`, sans introduire de dépendance lourde.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x + Vue 3 / Nuxt 4 (frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic, argon2-cffi (déjà), zxcvbn-python (à ajouter, optionnel — la validation de score peut aussi se faire purement front avec `zxcvbn-ts`).
- Frontend: Nuxt 4, Pinia, Tailwind v4, gsap, driver.js (déjà installés), `@zxcvbn-ts/core` + `@zxcvbn-ts/language-common` + `@zxcvbn-ts/language-fr` (à ajouter), `nuxt-security` (déjà).
**Storage**: PostgreSQL 16 + pgvector. Une seule nouvelle table : `user_preferences` (1-1 avec `account_user`) — ou alternative : colonnes ajoutées sur `account_user` (cf. research). RLS obligatoire (P2).
**Testing**:
- Backend : pytest (`backend/tests/`) — tests unitaires (validation reset password, endpoint /me/preferences) + tests d'intégration (RLS sur user_preferences, invalidation sessions sur reset).
- Frontend : vitest (`frontend/app/__tests__/`, `frontend/app/composables/__tests__/`) — composables `useOnboardingTour`, `usePasswordStrength`, `useT` ; tests de pages (login, register wizard) avec `@vue/test-utils`.
- E2E : Playwright (déjà configuré sous `frontend/tests/e2e/` en F38) — parcours register 3-step, login + redirect deep link, forgot/reset complet, tour guidé skip + complete + relance manuelle.
**Target Platform**: Web responsive — desktop ≥ 1024 px (split-screen complet), tablette 768–1023 px (split-screen compacté), mobile < 768 px (formulaire pleine largeur, illustration cachée). Navigateurs cibles : 2 dernières versions de Chrome, Firefox, Safari, Edge.
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4) — structure déjà établie.
**Performance Goals**: Login LCP < 1,2 s sur connexion 4G typique cible (SC-005). Wizard register : transition step → step < 100 ms perçus (gsap 200 ms, mais perception immédiate). Tour driver.js : pas de jank > 16 ms sur transitions popover.
**Constraints**:
- Anti-énumération d'utilisateurs (FR-006, FR-008) : aucun message ni code HTTP différenciant.
- `prefers-reduced-motion: reduce` : neutralise toutes les animations (FR-018).
- i18n FR strict (FR-019) — aucune chaîne en dur.
- a11y ≥ 95 Lighthouse (SC-004).
- Hébergement Europe / Afrique de l'Ouest (constitution).
**Scale/Scope**: ~5 pages frontend (4 existantes à polir + 1 nouvelle `welcome.vue`) + 1 page publique enrichie + 1 layout auth split-screen + 1 bandeau global `EmailVerificationBanner.vue` + 3 nouveaux composables (`useOnboardingTour`, `usePasswordStrength`, `useT`) + 1 endpoint backend `/me/preferences` + 1 migration Alembic. Volume utilisateur : MVP ouest-africain — quelques centaines de comptes pendant la phase pilote, montée à quelques milliers en année 1. Pas de contrainte de débit forte sur ces endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Pas de donnée factuelle ESG ni de catalogue introduits ici. | ✅ N/A |
| P2 | Multi-tenant RLS | La nouvelle table `user_preferences` portera `account_id NOT NULL` + politique RLS `USING (account_id = current_setting('app.current_account_id')::uuid)`. Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Toute mutation de `user_preferences.onboarding_state` et tout `password_reset` réussi DOIT écrire en `audit_log` avec `source_of_change='manual'`. | ✅ |
| P4 | Versioning + snapshot candidatures | N/A (pas de référentiel ni candidature). | ✅ N/A |
| P5 | Money typé | N/A. | ✅ N/A |
| P6 | Pivot Indicateur unique | N/A. | ✅ N/A |
| P7 | Plateforme fermée aux intermédiaires | Roles inchangés (PME, Admin). Pas d'inscription "fonds/banque". | ✅ |
| P8 | Édition manuelle + sync LLM | Pas de champ alimenté par LLM dans cette feature. La préférence `onboarding_state` est purement utilisateur. | ✅ N/A |
| P9 | Tool-use LLM fiable | Pas de nouveau tool LLM. | ✅ N/A |
| P10 | UX bottom sheet | Aucun input interactif (radios/file upload/sliders) dans une bulle LLM ici — la feature est hors flux chat. Les popovers driver.js sont des **highlights pédagogiques non interactifs** (texte + boutons "Suivant"/"Passer"), conformes à l'esprit de P10. | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 → CGU/RGPD validés DPO avant prod (FR-024) ✓
- Langue : français par défaut ✓ (FR-019)

## Project Structure

### Documentation (this feature)

```text
specs/042-onboarding-auth-polish/
├── plan.md              # This file
├── research.md          # Phase 0 — décisions techniques (zxcvbn lib, table vs colonnes, etc.)
├── data-model.md        # Phase 1 — entité user_preferences + flux d'état du tour
├── quickstart.md        # Phase 1 — comment tester localement la feature complète
├── contracts/
│   ├── me-preferences-api.md   # Contrat REST GET/PATCH /me/preferences
│   └── frontend-components.md  # Contrats des composables/composants nouveaux
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── users/
│   │   ├── router.py              # ÉDIT — ajouter GET/PATCH /me/preferences
│   │   ├── service.py             # ÉDIT — get_preferences / update_preferences (audit log)
│   │   └── schemas.py             # NOUV — UserPreferencesOut, UserPreferencesPatch
│   ├── models/
│   │   └── user_preferences.py    # NOUV — modèle SQLAlchemy
│   ├── auth/
│   │   ├── service.py             # ÉDIT — invalidation sessions sur reset, vérif token ≤ 60 min
│   │   └── router.py              # ÉDIT — réponse reset = redirection / message succès
│   └── core/
│       └── password_strength.py   # NOUV — wrapper zxcvbn (option B Python OU front-only)
├── alembic/
│   └── versions/
│       └── 0042_user_preferences.py    # NOUV — migration table user_preferences + RLS
└── tests/
    ├── users/
    │   └── test_preferences.py    # NOUV — RLS, audit log, transitions d'état
    └── auth/
        └── test_password_reset_invalidation.py   # NOUV — sessions invalidées + TTL 60 min

frontend/
├── app/
│   ├── pages/
│   │   ├── index.vue              # ÉDIT — homepage publique (pitch, bénéfices, témoignage, CTA)
│   │   ├── login.vue              # ÉDIT — split-screen, password toggle, "Rester connecté", deep link
│   │   ├── register.vue           # ÉDIT — wizard 3 steps + progress bar + animation
│   │   ├── forgot-password.vue    # ÉDIT — message générique, anti-énumération, cooldown 60 s
│   │   ├── reset-password.vue     # ÉDIT — strength meter, redirect /login + message succès
│   │   └── onboarding/
│   │       └── welcome.vue        # NOUV — page de bienvenue post-register, déclenche le tour
│   ├── layouts/
│   │   └── auth.vue               # ÉDIT — split-screen (illustration <768px cachée)
│   ├── components/
│   │   ├── auth/
│   │   │   ├── PasswordStrengthMeter.vue  # NOUV
│   │   │   ├── PasswordVisibilityToggle.vue  # NOUV
│   │   │   ├── RegisterStepIdentifiants.vue  # NOUV
│   │   │   ├── RegisterStepEntreprise.vue    # NOUV (autocomplete secteur via F08)
│   │   │   ├── RegisterStepConsentements.vue # NOUV (CGU/RGPD)
│   │   │   ├── RegisterProgressBar.vue       # NOUV
│   │   │   └── ResendCooldownButton.vue      # NOUV (60 s anti-spam)
│   │   ├── onboarding/
│   │   │   ├── EmptyStateLanding.vue         # NOUV (CTA + 3 cartes pédagogiques)
│   │   │   └── OnboardingTourTrigger.vue     # NOUV (point d'entrée manuel — menu Aide)
│   │   ├── common/
│   │   │   └── EmailVerificationBanner.vue   # NOUV (bandeau global non bloquant)
│   │   └── home/
│   │       ├── PublicHero.vue                # NOUV (pitch + CTA)
│   │       ├── PublicBenefitsGrid.vue        # NOUV (3 bénéfices)
│   │       └── PublicTestimonial.vue         # NOUV (témoignage anonymisé)
│   ├── composables/
│   │   ├── useOnboardingTour.ts   # NOUV — orchestre driver.js + persiste via /me/preferences
│   │   ├── usePasswordStrength.ts # NOUV — wrap zxcvbn-ts, expose score 0-4 + critères + label FR
│   │   ├── useT.ts                # NOUV — lookup léger dans locales/fr.ts
│   │   ├── useReducedMotion.ts    # EXISTE — réutilisé
│   │   └── useAuth.ts             # ÉDIT — handle "rester connecté", deep link
│   ├── stores/
│   │   ├── auth.ts                # ÉDIT — flag `rememberMe`, état email vérifié
│   │   └── userPreferences.ts     # NOUV — Pinia store onboarding_state
│   ├── locales/
│   │   └── fr.ts                  # NOUV — toutes les chaînes FR de la feature
│   └── assets/
│       ├── images/
│       │   ├── auth-illustration.webp  # NOUV (LCP léger)
│       │   └── auth-illustration.avif  # NOUV (fallback moderne)
│       └── css/
│           └── tour.css           # NOUV — overrides driver.js (réduire mouvement, contraste)
└── tests/
    ├── e2e/
    │   ├── auth-login.spec.ts          # ÉDIT
    │   ├── auth-register-wizard.spec.ts # NOUV
    │   ├── auth-reset-password.spec.ts # NOUV
    │   ├── onboarding-tour.spec.ts     # NOUV
    │   └── empty-state-landing.spec.ts # NOUV
    └── unit/
        ├── usePasswordStrength.test.ts # NOUV
        └── useOnboardingTour.test.ts   # NOUV
```

**Structure Decision**: Web application standard du dépôt — backend FastAPI sous `backend/app/`, frontend Nuxt 4 sous `frontend/app/`. La feature ajoute une **nouvelle table** `user_preferences` (préférée à des colonnes sur `account_user` pour isoler les préférences évolutives sans impacter le schéma d'auth — voir research) + une **migration Alembic** + un **endpoint REST** `/me/preferences`. Côté frontend, la totalité est en Composition API + composants atomiques sous `components/auth|onboarding|common|home/`, alimentés par un store Pinia `userPreferences` et un composable orchestrateur `useOnboardingTour`. i18n : fichier statique TypeScript `frontend/app/locales/fr.ts` exposé par un composable `useT(key)` — choix justifié dans research (pas de nuxt-i18n pour ne pas alourdir le bundle MVP).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Section non utilisée.
