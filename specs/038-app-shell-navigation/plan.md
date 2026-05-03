# Implementation Plan: App Shell, Layout & Navigation (F38)

**Branch**: `038-app-shell-navigation` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/038-app-shell-navigation/spec.md`

## Summary

Construire le squelette d'application Nuxt 4 commun à toute la PME : trois layouts (`default`, `public`, `auth`), composants de chrome (`TheSidebar`, `TheHeader`, `TheBottomNav`, `TheCommandPalette`, `TheBreadcrumbs`, `TheNotificationsBell`, `TheAvatarMenu`, `TheRouteProgress`, `TheOfflineBanner`, `TheErrorBoundary`), un store Pinia `useNotificationsStore` synchronisé en temps réel via SSE (`/me/events` de F41) avec fallback polling 60 s sur `GET /me/notifications` (F34 déjà disponible), une middleware `pme-only.ts` symétrique de `admin.ts` existante, et un composable `useBreadcrumbs()` lisant `route.meta.breadcrumb`. Toutes les interactions s'appuient sur les primitives F37 (`UiPopover`, `UiBadge`, `UiAvatar`, `UiToastHost`, `UiTooltip`, `UiButton`) et les tokens F36. Aucune dépendance UI tierce ; positionnement via `@floating-ui/vue` déjà installé ; animations via `gsap` avec respect strict de `prefers-reduced-motion` (composable `useReducedMotion` réutilisé). Backend : aucune nouvelle table ; un endpoint stub `GET /me/events` (SSE keepalive) est livré pour permettre au shell de fonctionner avant l'arrivée complète de F41 (le contrat reste compatible avec F41).

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3.5 (Composition API, `<script setup>`) côté frontend ; Python 3.12 + FastAPI côté backend (uniquement pour le stub SSE et le pluggage du router).
**Primary Dependencies** : Nuxt 4 (auto-imports, layouts, middleware), Pinia, Tailwind v4, gsap 3.12, `@floating-ui/vue`, primitives F37 (`Ui*`). Backend : FastAPI, `sse-starlette` (à ajouter pour le stub SSE — nouvelle dépendance backend).
**Storage** : Aucune nouvelle table SQL. La table `notifications` existe déjà (F34) et est lue par le shell via `GET /me/notifications`. État frontend in-memory dans Pinia (`useNotificationsStore`).
**Testing** : `vitest` + `@vue/test-utils` + `happy-dom` (frontend) ; `pytest` + httpx pour le stub SSE (backend). Test e2e basique via Playwright laissé hors-scope MVP de F38 (sera couvert par F35).
**Target Platform** : navigateurs evergreen (Chromium 120+, Safari 17+, Firefox 120+) ; viewports mobile (320 → 768) et desktop (768 → 1920) ; SSR Nuxt 4 actif (les layouts doivent être SSR-safe).
**Project Type** : web application — frontend Nuxt 4 + backend FastAPI. F38 modifie majoritairement le frontend ; un patch backend minimal pour le SSE stub.
**Performance Goals** : transition de route perçue < 100 ms (SC-002) ; ouverture palette < 200 ms (SC-006) ; latence SSE < 2 s (SC-007) ; le shell ne doit ajouter au bundle initial PME que ≤ 35 kB gzipped (chrome + stores + middlewares).
**Constraints** : SSR-safe (pas d'accès `window`/`document` au top-level) ; `prefers-reduced-motion` strict ; conformité P2 RLS (lecture notifications déjà filtrée par `account_id` côté F34) ; conformité P7 (aucun rôle externe ajouté) ; cibles tactiles ≥ 44 × 44 px ; FR par défaut (P10/Langue).
**Scale/Scope** : 3 layouts + 10 composants shell + 1 store + 1 middleware + 1 composable + 1 stub SSE backend ≈ 25 fichiers source + ~15 fichiers de tests.

## Constitution Check

Référence : [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? | ✅ N/A — aucune donnée ESG/financière introduite ; le shell affiche raison sociale + notifications produites ailleurs. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + RLS ? | ✅ Aucune nouvelle table. Lectures via endpoints F02/F34 déjà soumis à `app.current_account_id`. |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée ? | ✅ La seule mutation côté shell (`marquer notification lue`) délègue à `PATCH /me/notifications/{id}/read` (F34) qui journalise déjà. Aucun bypass. |
| P4 | Versioning + snapshot candidatures | Versioning des nouveaux référentiels ? | ✅ N/A. |
| P5 | Money typé | `Money = {amount: Decimal, currency}` côté présentation ? | ✅ N/A — le shell n'affiche pas de montants. |
| P6 | Pivot Indicateur unique | ESG par axe ? | ✅ N/A. |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôles externes ? | ✅ Seuls les rôles `PME` et `Admin` sont reconnus par les middlewares (`pme-only.ts`, `admin.ts` existant). |
| P8 | Édition manuelle + sync LLM | Champs LLM modifiables ? | ✅ N/A — le shell ne touche pas de champs LLM. |
| P9 | Tool-use LLM fiable | Nouveaux tools LLM ? | ✅ N/A — aucun tool LLM ajouté. |
| P10 | UX bottom sheet | Composants interactifs en bottom-sheet ? | ✅ La palette est un overlay clavier-first, pas un input de réponse au LLM (US3 du F38) ; le menu avatar et le popover notifications sont des affichages, pas des saisies. La règle « inputs LLM en bottom sheet » reste portée par F39. |

**Verdict** : aucun gate violé. F38 est une feature transversale frontend + un stub SSE backend, sans donnée métier introduite.

### Contraintes techniques (rappel)

- Stack imposée respectée (Nuxt 4 + Tailwind v4 + Pinia + gsap, déjà en `package.json`).
- SSR-safe obligatoire : middleware `auth.global.ts` lit la session via cookies httpOnly côté serveur ; les composants shell évitent tout accès `window`/`document` au top-level (encapsulation dans `onMounted`).
- Hébergement EU/Afrique de l'Ouest : N/A pour le code frontend ; aucune dépendance hébergée hors-EU n'est ajoutée. `sse-starlette` est publiée sur PyPI.
- Langue : libellés du shell tous en français (FR-024) ; sélecteur EN désactivé au MVP.
- Conformité P2 : aucune lecture de données métier nouvelle ; les routes consommées sont déjà gardées par RLS.

## Project Structure

### Documentation (this feature)

```text
specs/038-app-shell-navigation/
├── plan.md              # ce fichier
├── research.md          # Phase 0 — décisions techniques
├── data-model.md        # Phase 1 — contrats des composants shell + state stores
├── quickstart.md        # Phase 1 — comment lancer le shell + smoke-test des layouts
├── contracts/
│   ├── route-meta.md         # contrat des `route.meta` (layout/auth/breadcrumb)
│   ├── sse-events.md         # contrat SSE `/me/events` (stub F38, complet F41)
│   └── shell-components.md   # API des composants `The*` (props/events/slots)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (sortira de /speckit-tasks)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── app.vue                              # racine — déjà présente, ajoutera <UiToastHost /> + <NuxtErrorBoundary>
│   ├── layouts/
│   │   ├── default.vue                      # NEW — layout PME (sidebar + header + content)
│   │   ├── public.vue                       # NEW — header minimal + footer
│   │   └── auth.vue                         # NEW — split-screen
│   ├── components/
│   │   ├── shell/                           # NEW — composants de charpente
│   │   │   ├── TheSidebar.vue
│   │   │   ├── TheHeader.vue
│   │   │   ├── TheBottomNav.vue
│   │   │   ├── TheCommandPalette.vue
│   │   │   ├── TheBreadcrumbs.vue
│   │   │   ├── TheNotificationsBell.vue
│   │   │   ├── TheAvatarMenu.vue
│   │   │   ├── TheRouteProgress.vue
│   │   │   ├── TheOfflineBanner.vue
│   │   │   └── TheErrorBoundary.vue
│   │   └── ui/                              # primitives F37 (déjà présentes — réutilisées)
│   ├── composables/
│   │   ├── useAuth.ts                       # déjà présent — étendu si besoin (logout flow)
│   │   ├── useBreadcrumbs.ts                # NEW — lit route.meta.breadcrumb
│   │   ├── useCommandPalette.ts             # NEW — registre d'actions + filtre
│   │   ├── useNotificationsStream.ts        # NEW — SSE + fallback polling
│   │   ├── useOnlineStatus.ts               # NEW — wrapper `navigator.onLine`
│   │   └── useReducedMotion.ts              # déjà présent — réutilisé
│   ├── stores/
│   │   ├── auth.ts                          # déjà présent — réutilisé
│   │   └── notifications.ts                 # NEW — Pinia store (compteur + 5 dernières non lues)
│   ├── middleware/
│   │   ├── auth.global.ts                   # déjà présent — étendu (preserveDestination + 401 handler)
│   │   ├── pme-only.ts                      # NEW — interdit aux comptes admin les routes PME
│   │   └── admin.ts                         # déjà présent — réutilisé
│   ├── pages/
│   │   ├── dashboard.vue                    # NEW (stub) — pour valider la navigation
│   │   ├── profil.vue                       # NEW (stub)
│   │   ├── projets/index.vue                # NEW (stub)
│   │   ├── scoring.vue                      # NEW (stub)
│   │   ├── parametres.vue                   # NEW (stub)
│   │   └── notifications.vue                # NEW (stub) — cible du popover cloche
│   └── types/
│       └── route-meta.d.ts                  # NEW — extension Vue Router meta
└── tests/
    └── unit/
        ├── shell/
        │   ├── TheSidebar.spec.ts
        │   ├── TheHeader.spec.ts
        │   ├── TheBottomNav.spec.ts
        │   ├── TheCommandPalette.spec.ts
        │   ├── TheBreadcrumbs.spec.ts
        │   ├── TheNotificationsBell.spec.ts
        │   ├── TheAvatarMenu.spec.ts
        │   ├── TheOfflineBanner.spec.ts
        │   └── TheErrorBoundary.spec.ts
        ├── stores/
        │   └── notifications.spec.ts
        ├── composables/
        │   ├── useBreadcrumbs.spec.ts
        │   ├── useCommandPalette.spec.ts
        │   ├── useNotificationsStream.spec.ts
        │   └── useOnlineStatus.spec.ts
        └── middleware/
            ├── auth.global.spec.ts          # nouveau cas : preserveDestination + 401
            └── pme-only.spec.ts

backend/
├── app/
│   ├── notifications/
│   │   └── stream.py                        # NEW — endpoint SSE stub `GET /me/events`
│   └── main.py                              # PATCH — include du router stream
└── tests/
    └── notifications/
        └── test_stream.py                   # NEW — smoke-test SSE keepalive
```

**Structure Decision** : alignement strict avec la convention Nuxt 4 d'auto-imports. Les composants de chrome partagés vivent sous `components/shell/` avec préfixe `The` (Vue style guide pour les singletons), distinct des primitives `ui/` de F37. Les middlewares de routing (`auth.global.ts` global, `pme-only.ts` named) restent dans `middleware/`. Le stub SSE backend est ajouté au package `notifications/` existant (F34) sous `stream.py` pour préserver la cohérence de domaine ; il sera remplacé/étendu sans rupture de contrat lors de l'implémentation complète de F41.

## Complexity Tracking

> Aucune violation constitutionnelle à justifier.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (aucune) | — | — |
