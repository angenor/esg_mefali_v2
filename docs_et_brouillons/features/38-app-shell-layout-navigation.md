# F38 — App Shell, Layout & Navigation

**Phase** : A — Fondations design (UI MVP)
**Modules brainstorm** : transversal — squelette de l'app PME
**Dépendances** : F36, F37, F02 (auth)
**Estimation** : 2 jours

## Contexte et objectif

Squelette commun à toutes les pages PME : **layout principal**, navigation latérale, top-bar (raison sociale, notifications, avatar), routing protégé, gestion auth, breadcrumbs, états globaux. Layouts séparés pour pages publiques (`/verify/{id}`) et auth (`/login`, `/register`). Style : épuré comme Linear — sidebar étroite, icônes outline, label visible au hover.

## User Stories

### US1 — Layout PME authentifié (P1)
Sidebar gauche (logo + nav), header sobre (raison sociale, cloche notifications, avatar menu), zone de contenu fluide.

### US2 — Layout public (P1)
`/verify/{id}` (F52) + accueil marketing : sans sidebar, header minimal, footer mentions légales.

### US3 — Layout auth (P1)
`/login`, `/register`, `/forgot-password`, `/reset-password` : split-screen (illustration/citation gauche, formulaire droite). Mobile : full-width form.

### US4 — Navigation principale (P1)
Rubriques sidebar : **Tableau de bord, Profil entreprise, Projets, Plan d'action, Scoring ESG, Empreinte carbone, Score crédit, Candidatures, Rapports & attestations, Bibliothèque, Paramètres**. Active state, badge compteur (notifications non lues).

### US5 — Top bar + commande globale (P1)
Breadcrumb + `<UiCommandPalette>` Cmd+K (recherche action/page) + cloche notifications (popover) + avatar dropdown (compte, paramètres, déconnexion).

### US6 — Mobile responsive (P1)
Sidebar → drawer hamburger sur < 1024 px. Bottom nav simplifiée mobile (4 icônes : Chat, Dashboard, Profil, Plus).

### US7 — Breadcrumbs auto (P1)
Composable `useBreadcrumbs()` lit `route.meta.breadcrumb`. Format `Accueil / Profil / Projets / Mon projet ABC`.

### US8 — Etats globaux (P1)
- Top progress bar 2 px brand-500 sur route-change.
- Toast queue global (`<UiToast>` F37).
- ErrorBoundary `<NuxtErrorBoundary>` avec page fallback + bouton "Recharger".
- Banner offline discret si connexion perdue.

### US9 — Switch langue / locale (P2)
FR / EN dans avatar dropdown. MVP FR actif, EN visible grisé. `@nuxtjs/i18n`.

### US10 — Guards de route (P1)
- `auth.global.ts` : redirige `/login` si pas de cookie session, sauf `meta.public = true`.
- `pme-only.ts` : interdit aux comptes admin.
- `admin-only.ts` : limite `/admin/*` aux admin.

## Exigences fonctionnelles

- **FR-001** : `frontend/app/layouts/{default,public,auth}.vue`.
- **FR-002** : `frontend/app/components/shell/{TheSidebar,TheHeader,TheBottomNav,TheCommandPalette,TheBreadcrumbs}.vue`.
- **FR-003** : Pinia stores `useAuthStore` + `useNotificationsStore`.
- **FR-004** : Middlewares Nuxt globaux.
- **FR-005** : Layout default écoute SSE `/me/events` (F41) pour push temps réel ; fallback polling 60 s.
- **FR-006** : Logout = `POST /auth/logout` + reset stores + redirect `/login`.
- **FR-007** : Cloche affiche 5 dernières non-lues (popover) + lien `/notifications`.

## Exigences non-fonctionnelles

- **NFR-001** : Transition route < 100 ms perçue.
- **NFR-002** : Sidebar respecte `prefers-reduced-motion`.
- **NFR-003** : Tap target 44 × 44 px mobile.

## Composants livrés

`layouts/default.vue, layouts/public.vue, layouts/auth.vue, components/shell/*, middleware/auth.global.ts, middleware/pme-only.ts, middleware/admin-only.ts, stores/auth.ts, stores/notifications.ts, composables/useBreadcrumbs.ts`.

## Success Criteria

- **SC-001** : Navigation entre 5 pages stub sans reload, transition fluide.
- **SC-002** : Cmd+K ouvre palette, "scoring" → navigate `/scoring`.
- **SC-003** : Logout → redirect login + cookies effacés (devtools vérifié).
- **SC-004** : Resize < 1024 px → drawer + bottom nav.

## Hors-scope MVP

- Recherche full-text palette → post-MVP (actions seulement).
- Multi-tenant switch → P7 constitution : 1 user = 1 account.
- i18n EN actif → différé.

## Risques et points de vigilance

- **SSR Nuxt** : sidebar + auth state cohérents reload froid/chaud.
- **Cmd+K** : conflit macOS, tester Ctrl+K aussi.
- Largeur sidebar fixe 256 / rail 64 / drawer mobile. Pas de slider custom.
