---

description: "Task list — F38 App Shell, Layout & Navigation"
---

# Tasks: App Shell, Layout & Navigation (F38)

**Input**: Design documents from `/specs/038-app-shell-navigation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Inclus (TDD imposé par la constitution + `make test` couvre vitest + pytest, gate `fail_under = 80`).

**Organization**: les tâches sont groupées par user story (US1 → US8) pour permettre une livraison incrémentale du MVP. Une fois la phase 2 (Foundational) terminée, US1, US2 et US5 peuvent être attaquées en parallèle.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers distincts, pas de dépendance bloquante en cours)
- **[Story]**: tag de user story (US1…US8), absent en Setup/Foundational/Polish
- Chemins absolus depuis la racine `esg_mefali_v2/`

## Path Conventions

- Frontend Nuxt 4 : `frontend/app/...`, tests `frontend/tests/unit/...`
- Backend FastAPI : `backend/app/...`, tests `backend/tests/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: préparer les dépendances et la structure de répertoires.

- [X] T001 Ajouter la dépendance backend `sse-starlette>=2.1` dans `backend/pyproject.toml` (groupe principal) et exécuter `uv pip install -e .` ou `pip install -e .` depuis `backend/.venv`.
- [X] T002 [P] Créer le répertoire `frontend/app/layouts/` (vide pour l'instant — accueillera default.vue / public.vue / auth.vue).
- [X] T003 [P] Créer le répertoire `frontend/app/components/shell/` (composants `The*`).
- [X] T004 [P] Créer les répertoires de tests : `frontend/tests/unit/shell/`, `frontend/tests/unit/middleware/`, `frontend/tests/unit/stores/` (les autres existent déjà).
- [X] T005 [P] Créer le répertoire `backend/tests/notifications/` et y ajouter un `__init__.py` vide.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: types, registres et stubs sans lesquels aucune US ne peut compiler/tester.

**⚠️ CRITICAL**: aucune US ne démarre tant que cette phase n'est pas verte.

- [X] T006 Créer `frontend/app/types/route-meta.d.ts` avec l'extension de `RouteMeta` (champs `layout`, `public`, `pmeOnly`, `adminOnly`, `breadcrumb`, `title`) conforme à `contracts/route-meta.md`.
- [X] T007 [P] Créer `frontend/app/composables/useOnlineStatus.ts` (SSR-safe, retourne `true` côté serveur, écoute `online`/`offline` côté client).
- [X] T008 [P] Créer `frontend/tests/unit/composables/useOnlineStatus.spec.ts` (mocks `window.addEventListener`, valide bascule on/off + cleanup).
- [X] T009 [P] Créer `frontend/app/composables/useBreadcrumbs.ts` avec retour `ComputedRef<Crumb[]>` lisant `useRoute().meta.breadcrumb`, supportant `Crumb[]` ou résolveur fonction, fallback `[{label:'Accueil',to:'/dashboard'}]` sur routes PME.
- [X] T010 [P] Créer `frontend/tests/unit/composables/useBreadcrumbs.spec.ts` (cas : meta absent, meta tableau, meta fonction, dernier segment non cliquable).
- [X] T011 Créer `frontend/app/stores/notifications.ts` (Pinia `defineStore('notifications', ...)`) avec state `{items, isStreamConnected, lastSyncedAt, loadError}`, getters `unreadCount` / `latestUnread`, actions `loadInitial`, `pushFromStream`, `markRead`, `markAllRead`, `reset` — conforme à `data-model.md §1.2`.
- [X] T012 [P] Créer `frontend/tests/unit/stores/notifications.spec.ts` (mocks `$fetch`, valide loadInitial → items, unreadCount, markRead idempotent, reset vide tout, plafond 50 items FIFO).
- [X] T013 Étendre `frontend/app/stores/auth.ts` : ajouter `logout()` (POST `/auth/logout`, `useNotificationsStore().reset()`, `navigateTo('/login')`) si non déjà présent ; ajouter le getter `isAuthenticated`. Vérifier la présence du champ `raison_sociale` dans le user (sinon ajouter mapping).
- [X] T014 [P] Mettre à jour `frontend/tests/unit/stores/auth.spec.ts` (ou créer si absent) : valider que `logout()` appelle l'endpoint, vide les stores et redirige.
- [X] T015 Créer `frontend/app/middleware/pme-only.ts` (named middleware Nuxt 4) : si `useAuthStore().user?.role === 'admin'` → `navigateTo('/admin')`, sinon laisser passer.
- [X] T016 [P] Créer `frontend/tests/unit/middleware/pme-only.spec.ts` (mocks store, valide redirection admin → /admin et passage PME).
- [X] T017 [P] Créer 6 pages stubs PME utilisées pour la validation manuelle/quickstart : `frontend/app/pages/dashboard.vue`, `pages/profil.vue`, `pages/projets/index.vue`, `pages/scoring.vue`, `pages/parametres.vue`, `pages/notifications.vue`. Chaque page : `definePageMeta({ layout: 'default', middleware: ['pme-only'], breadcrumb: [...], title: '...' })` + un `<h1>` placeholder FR.

**Checkpoint**: types, store notifications, store auth étendu, middleware PME-only, pages stubs prêts → US1…US8 peuvent commencer.

---

## Phase 3: User Story 1 — Squelette PME authentifié (Priority: P1) 🎯 MVP

**Goal**: layout `default` avec sidebar + header + zone de contenu fluide, navigation entre rubriques sans rechargement.

**Independent Test**: connecter un compte PME, naviguer entre 5 rubriques (dashboard, profil, projets, scoring, paramètres), vérifier sidebar/header cohérents et transition < 100 ms (S-002 du quickstart).

### Tests for User Story 1 (TDD)

- [X] T018 [P] [US1] `frontend/tests/unit/shell/TheSidebar.spec.ts` : item actif reflète `route.path`, 11 rubriques rendues, badge unreadCount sur item Notifications, mode `collapsed=true` rend tooltips, a11y `nav[aria-label="Navigation principale"]`.
- [X] T019 [P] [US1] `frontend/tests/unit/shell/TheHeader.spec.ts` : raison sociale affichée depuis `useAuthStore().user`, hauteur 56 px, hamburger émis < 1024 px (mock `matchMedia`).

### Implementation for User Story 1

- [X] T020 [P] [US1] Créer `frontend/app/components/shell/TheSidebar.vue` : props `{collapsed?: boolean}` + emit `update:collapsed`, registre interne 11 rubriques (label FR + icône Heroicons + route), state actif depuis `useRoute().path`, badge unreadCount via `useNotificationsStore().unreadCount`, mode rail 64 px / déplié 256 px, persistance toggle dans `localStorage` via `onMounted`.
- [X] T021 [P] [US1] Créer `frontend/app/components/shell/TheHeader.vue` : raison sociale (depuis store, fallback email), bouton hamburger émis `toggle-drawer` si viewport < 1024 px, slot pour `<TheBreadcrumbs />`, `<TheNotificationsBell />` et `<TheAvatarMenu />` (montés mais peuvent être squelettes — détaillés en US3/US6/US8).
- [X] T022 [US1] Créer `frontend/app/layouts/default.vue` : structure `<div class="flex h-screen">` + `<TheSidebar />` (≥ 1024 px) + `<div class="flex flex-col flex-1">` contenant `<TheHeader />` + `<main><NuxtErrorBoundary><slot/></NuxtErrorBoundary></main>`. SSR-safe. Appelle `useNotificationsStore().loadInitial()` en `onMounted` (côté client uniquement).
- [X] T023 [US1] Mettre à jour `frontend/app/app.vue` : remplacer le rendu actuel par `<NuxtLayout><NuxtPage /></NuxtLayout>` + `<UiToastHost />` global (si pas déjà). Ajouter `<TheRouteProgress />` et `<TheOfflineBanner />` en racine (composants livrés par US6 ; pour US1, peuvent être inclus en tant que stubs vides si US6 non encore terminée).
- [X] T024 [US1] Vérifier la navigation entre les 6 pages stubs (T017) : sidebar surligne le bon item, header reste présent, contenu change sans full reload. Ajouter un test d'intégration léger `frontend/tests/unit/shell/default-layout.spec.ts` qui monte le layout avec une `<RouterStub>` et vérifie la composition.

**Checkpoint US1**: layout PME fonctionnel — un agent PME se connecte et voit l'app habillée.

---

## Phase 4: User Story 2 — Pages publiques et pages d'authentification (Priority: P1)

**Goal**: layouts `public` et `auth` distincts, sans chrome PME.

**Independent Test**: visiter `/login` (split-screen) et `/verify/{id}` (header minimal), vérifier l'absence de sidebar/cloche (S-001 du quickstart).

### Tests for User Story 2

- [X] T025 [P] [US2] `frontend/tests/unit/shell/auth-layout.spec.ts` : monte le layout, vérifie présence d'une zone illustration ≥ 1024 px et bascule full-width < 1024 px (mock `matchMedia`).
- [X] T026 [P] [US2] `frontend/tests/unit/shell/public-layout.spec.ts` : header minimal (logo seulement), footer mentions légales, absence de sidebar/cloche.

### Implementation for User Story 2

- [X] T027 [P] [US2] Créer `frontend/app/layouts/public.vue` : header ≤ 56 px contenant le logo (composant inline ou `<NuxtLink to="/">`), `<main><slot/></main>`, footer fixe avec liens « Mentions légales », « Confidentialité », « Contact » (URLs placeholder). Aucun appel store, aucun guard.
- [X] T028 [P] [US2] Créer `frontend/app/layouts/auth.vue` : grille 2 colonnes ≥ 1024 px (`grid-cols-2`), colonne gauche `<aside>` avec gradient + citation FR + logo, colonne droite `<main><slot/></main>`. Sous 1024 px : colonne gauche masquée (`hidden lg:block`), main pleine largeur. Aucun guard.
- [X] T029 [US2] Mettre à jour les 4 pages auth existantes (`pages/login.vue`, `pages/register.vue`, `pages/forgot-password.vue`, `pages/reset-password.vue`) pour ajouter `definePageMeta({ layout: 'auth', public: true, title: '...' })`.
- [X] T030 [US2] Mettre à jour `pages/index.vue` pour `definePageMeta({ layout: 'public', public: true, title: 'Accueil' })`.
- [X] T031 [US2] Créer `frontend/app/pages/verify/[id].vue` (stub) avec `definePageMeta({ layout: 'public', public: true, title: 'Vérification d\'attestation' })` et un `<h1>` FR placeholder pointant vers F30.

**Checkpoint US2**: pages publiques et auth se rendent dans leurs layouts respectifs sans chrome PME.

---

## Phase 5: User Story 3 — Navigation principale + palette de commandes (Priority: P1)

**Goal**: palette `Cmd/Ctrl+K` opérationnelle, registre d'actions, navigation rapide.

**Independent Test**: ouvrir la palette, taper « scoring », ↵, arriver sur `/scoring` (S-003 du quickstart).

### Tests for User Story 3

- [X] T032 [P] [US3] `frontend/tests/unit/composables/useCommandPalette.spec.ts` : registre, dédoublonnage par id, filtre fuzzy accents-tolérant, plafond 20 résultats, tri préfixe > substring.
- [X] T033 [P] [US3] `frontend/tests/unit/shell/TheCommandPalette.spec.ts` : `Cmd+K` ouvre, `Esc` ferme, `↵` exécute (run ou navigateTo), navigation clavier ↑/↓.

### Implementation for User Story 3

- [X] T034 [P] [US3] Créer `frontend/app/composables/useCommandPalette.ts` : singleton via `useState`, état `{isOpen, query, actions: Map<id, Action>}`, fonctions `open/close/toggle/registerActions/unregisterActions`, computed `results` (filtre + tri + plafond 20), normalisation NFD pour accents.
- [X] T035 [US3] Créer `frontend/app/components/shell/TheCommandPalette.vue` : modal centré (réutilise `<UiModal>` F37 ou conteneur custom), input recherche en focus à l'ouverture, liste résultats groupée par `group`, sélection clavier, gestion `Esc`/`↵`. Animation gsap 120 ms, désactivée sous `prefers-reduced-motion`. Lazy via `defineAsyncComponent` côté layout.
- [X] T036 [US3] Enregistrer dans `useCommandPalette()` (dans le setup de `layouts/default.vue`) le registre par défaut listé en `contracts/shell-components.md` (11 actions navigation + 2 actions + 1 aide).
- [X] T037 [US3] Brancher l'écoute clavier globale dans `TheCommandPalette.vue` ou un composable utilitaire : `Cmd+K` (Mac), `Ctrl+K` (Win/Linux), `/` (alias). Détection `navigator.platform`. Encapsulé dans `onMounted`/`onBeforeUnmount`.
- [X] T038 [US3] Monter `<TheCommandPalette />` dans `layouts/default.vue` (lazy) ; vérifier qu'il n'est pas dans `public.vue` ou `auth.vue` (palette = feature PME authentifiée).

**Checkpoint US3**: palette ouverte → recherche → navigation OK sur ≥ 5 pages stubs.

---

## Phase 6: User Story 4 — Responsive mobile : drawer + bottom nav (Priority: P1)

**Goal**: bascule sidebar → drawer + bottom-nav sous 1024 px.

**Independent Test**: redimensionner à 360 × 640, vérifier hamburger + bottom-nav 4 cibles ≥ 48 × 48 px (S-004 du quickstart).

### Tests for User Story 4

- [X] T039 [P] [US4] `frontend/tests/unit/shell/TheBottomNav.spec.ts` : 4 items rendus, taille minimum 48 px (lecture style inline), item actif depuis `route.path`, non rendu si viewport ≥ 1024 (assert via classes Tailwind `lg:hidden`).
- [X] T040 [P] [US4] `frontend/tests/unit/shell/drawer.spec.ts` : montage du drawer dans `layouts/default.vue`, ouverture sur `toggle-drawer`, fermeture sur clic overlay, `Esc`, ou `route` change.

### Implementation for User Story 4

- [X] T041 [P] [US4] Créer `frontend/app/components/shell/TheBottomNav.vue` : 4 cibles (Chat → `/chat`, Tableau de bord → `/dashboard`, Profil → `/profil`, Plus → ouvre sheet). Hauteur 56 px + safe-area (`pb-[env(safe-area-inset-bottom)]`). Cibles 48×48. `nav[aria-label="Navigation rapide"]`. Visible uniquement < 1024 px (`lg:hidden`).
- [X] T042 [US4] Étendre `layouts/default.vue` : ajouter un drawer mobile (élément aside slide-in 280 px + overlay) animé gsap, ouvert via state local + écoute `@toggle-drawer` du `TheHeader`. Fermer sur changement de route. Ajouter `<TheBottomNav />` (visible < 1024 px). Respecter `prefers-reduced-motion`.
- [X] T043 [US4] Implémenter le sheet « Plus » du bottom-nav : composant `TheBottomNavMore.vue` (ou réutilisation `<UiModal>` F37) listant les 8 rubriques absentes (Projets, Scoring, Carbone, Crédit, Candidatures, Rapports, Bibliothèque, Paramètres). Ferme sur clic item ou backdrop.

**Checkpoint US4**: à 360 px de large, sidebar invisible, hamburger ouvre drawer, bottom-nav visible, « Plus » liste les rubriques restantes.

---

## Phase 7: User Story 5 — Routes protégées et redirections (Priority: P1)

**Goal**: guards d'authentification + séparation PME/Admin.

**Independent Test**: accès `/dashboard` sans session → `/login?redirect=/dashboard` ; PME tente `/admin` → redirect ; admin tente `/scoring` → redirect (S-005).

### Tests for User Story 5

- [X] T044 [P] [US5] `frontend/tests/unit/middleware/auth.global.spec.ts` : (a) anonyme + route privée → navigateTo `/login?redirect=…` ; (b) anonyme + `meta.public=true` → laisse passer ; (c) authentifié + `/login` → navigateTo `/dashboard` ; (d) authentifié + route privée → laisse passer.
- [X] T045 [P] [US5] `frontend/tests/unit/middleware/admin.spec.ts` (mise à jour si test existant minimal) : PME → redirect, admin → laisse passer.

### Implementation for User Story 5

- [X] T046 [US5] Étendre `frontend/app/middleware/auth.global.ts` pour : (1) lire la session SSR-safe via `useAuthStore()` (déjà hydratée par `useAuth`) ; (2) check `to.meta.public === true` → laisse passer ; (3) si pas de user → `navigateTo({path:'/login', query:{redirect: to.fullPath}})` ; (4) si user et to ∈ {`/login`,`/register`} → `navigateTo('/dashboard')` ; (5) intercepter une réponse 401 globale en s'abonnant à un événement `auth:unauthorized` (à émettre depuis le client `$fetch` via plugin Nuxt à créer si absent — voir T047).
- [X] T047 [US5] Créer un plugin Nuxt `frontend/app/plugins/auth-unauthorized.ts` qui enveloppe `$fetch` ou `useFetch` (via `useNuxtApp()`) pour détecter les 401 et déclencher `useAuthStore().logout()` propre puis `navigateTo('/login?expired=1')`.
- [X] T048 [US5] Mettre à jour `pages/login.vue` pour lire `route.query.redirect` après login réussi et rediriger vers cette destination (fallback `/dashboard`).
- [X] T049 [US5] Vérifier que toutes les pages PME stubs (T017) ont `middleware: ['pme-only']` ; vérifier que toutes les pages `/admin/*` existantes ont `middleware: ['admin']`. Si lacunes, corriger.

**Checkpoint US5**: tentatives d'accès directes (5 routes privées + 5 publiques) se comportent comme attendu.

---

## Phase 8: User Story 6 — États globaux (Priority: P1)

**Goal**: toasts, bannière offline, ErrorBoundary, cloche notifications temps réel via SSE + fallback polling, barre de progression.

**Independent Test**: INSERT manuel d'une notification en SQL → badge mis à jour < 2 s (S-006) ; offline → bannière (S-007) ; erreur forcée → page de repli (S-008) ; route change → barre brand-500 (S-002).

### Tests for User Story 6

- [X] T050 [P] [US6] `backend/tests/notifications/test_stream.py` : `GET /me/events` sans cookie → 401 ; avec cookie → 200, content-type `text/event-stream`, premier `event: ping` reçu < 35 s (utiliser `httpx.AsyncClient` + `aiter_text`).
- [X] T051 [P] [US6] `frontend/tests/unit/composables/useNotificationsStream.spec.ts` : démarrage SSE, fallback polling sur erreur, reconnexion exponentielle, stop libère ressources (mock `EventSource` + `setInterval`).
- [X] T052 [P] [US6] `frontend/tests/unit/shell/TheNotificationsBell.spec.ts` : badge = unreadCount, popover ouvert au clic, click notif → markRead + navigateTo, fermé par `Esc`.
- [X] T053 [P] [US6] `frontend/tests/unit/shell/TheOfflineBanner.spec.ts` : visible si `isOnline=false`, masqué sinon, `role="status"`, `aria-live="polite"`.
- [X] T054 [P] [US6] `frontend/tests/unit/shell/TheErrorBoundary.spec.ts` : reçoit prop `error`, affiche message FR, bouton « Recharger » émet `reload`.
- [X] T055 [P] [US6] `frontend/tests/unit/shell/TheRouteProgress.spec.ts` : visible entre `page:start` et `page:finish` (mocks Nuxt hooks), `prefers-reduced-motion` désactive l'animation slide.

### Implementation for User Story 6

- [X] T056 [P] [US6] Créer `backend/app/notifications/stream.py` : `APIRouter(prefix="/me", tags=["notifications-stream"])`, endpoint `GET /events` protégé par `Depends(get_current_user)`, retourne `EventSourceResponse` avec async generator qui yield `{"event":"ping","data": iso_timestamp}` toutes les 30 s. Conforme à `contracts/sse-events.md`.
- [X] T057 [US6] Patcher `backend/app/main.py` pour `from app.notifications.stream import router as notifications_stream_router` puis `app.include_router(notifications_stream_router)`. Vérifier ordre des middlewares (RequestId → AuthSession → CORS) inchangé.
- [X] T058 [P] [US6] Créer `frontend/app/composables/useNotificationsStream.ts` : conforme `data-model.md §2.3`. SSR no-op. Reconnexion exponentielle 1s/2s/4s/8s/30s plafond. Fallback polling 60 s sur erreur. `start()`/`stop()`.
- [X] T059 [P] [US6] Créer `frontend/app/components/shell/TheNotificationsBell.vue` : bouton icône cloche (`<UiButton variant="ghost">`), badge `<UiBadge>` si `unreadCount > 0`, `<UiPopover>` ancré au clic listant `latestUnread` (max 5) + lien « Voir toutes » → `/notifications`. Click notif : `markRead(id)` puis `navigateTo(notif.link)` si présent.
- [X] T060 [P] [US6] Créer `frontend/app/components/shell/TheOfflineBanner.vue` : `<div role="status" aria-live="polite" v-if="!isOnline">…</div>`, bandeau fixe top-0 28 px fond `--color-warning-100`, libellé FR figé.
- [X] T061 [P] [US6] Créer `frontend/app/components/shell/TheErrorBoundary.vue` : props `{error: Error}`, emit `reload`, rend message FR + `<UiButton @click="$emit('reload')">Recharger</UiButton>`. En `import.meta.dev`, affiche stack.
- [X] T062 [P] [US6] Créer `frontend/app/components/shell/TheRouteProgress.vue` : barre fixed top z-9999 2px brand-500. Hooks Nuxt `useNuxtApp().hook('page:start' / 'page:finish')`. Animation gsap (translateX + opacity). Désactivée si `prefers-reduced-motion` (juste apparition/disparition).
- [X] T063 [US6] Mettre à jour `layouts/default.vue` : monter `<TheNotificationsBell />` dans `<TheHeader />` (slot ou directement) et appeler `useNotificationsStream().start()` en `onMounted` côté client. `useNotificationsStream().stop()` en `onBeforeUnmount`.
- [X] T064 [US6] Mettre à jour `app.vue` : monter `<TheRouteProgress />` et `<TheOfflineBanner />` au niveau racine (au-dessus de `<NuxtLayout>`). `<UiToastHost />` également si pas déjà.
- [X] T065 [US6] Mettre à jour `layouts/default.vue` et `layouts/public.vue` : envelopper `<slot/>` dans `<NuxtErrorBoundary>` qui rend `<TheErrorBoundary :error="error" @reload="clearError({redirect: $route.fullPath})" />` en cas d'erreur.

**Checkpoint US6**: notifications temps réel via stub SSE, badge mis à jour, bannière offline, page de repli, barre de progression, toasts opérationnels.

---

## Phase 9: User Story 7 — Breadcrumbs automatiques (Priority: P2)

**Goal**: fil d'Ariane rendu depuis `route.meta.breadcrumb`.

**Independent Test**: page imbriquée affiche breadcrumb hiérarchique, dernier segment non cliquable (S-002 + spec US7).

### Tests for User Story 7

- [X] T066 [P] [US7] `frontend/tests/unit/shell/TheBreadcrumbs.spec.ts` : meta tableau → segments rendus avec liens sauf dernier, meta absent → fallback « Accueil », troncature > 40 caractères.

### Implementation for User Story 7

- [X] T067 [US7] Créer `frontend/app/components/shell/TheBreadcrumbs.vue` : utilise `useBreadcrumbs()`, rend `<nav aria-label="Fil d'Ariane">` avec `<NuxtLink>` pour les segments intermédiaires et `<span aria-current="page">` pour le dernier. Séparateur `/` `aria-hidden`. CSS truncate.
- [X] T068 [US7] Monter `<TheBreadcrumbs />` dans `TheHeader.vue` (à gauche du bloc cloche/avatar). Vérifier que les 6 pages stubs PME (T017) déclarent un breadcrumb cohérent.

**Checkpoint US7**: navigation imbriquée affiche un breadcrumb correct.

---

## Phase 10: User Story 8 — Sélecteur de langue placeholder (Priority: P2)

**Goal**: menu avatar avec FR actif / EN désactivé.

**Independent Test**: ouvrir menu avatar → voir « Langue : FR » actif, EN grisé non cliquable.

### Tests for User Story 8

- [X] T069 [P] [US8] `frontend/tests/unit/shell/TheAvatarMenu.spec.ts` : popover ouvert au clic, items présents (Mon compte, Paramètres, Déconnexion), sélecteur EN avec `disabled`, click logout déclenche store.logout.

### Implementation for User Story 8

- [X] T070 [US8] Créer `frontend/app/components/shell/TheAvatarMenu.vue` : `<UiAvatar>` initiales depuis `user.email`, `<UiPopover>` au clic contenant : en-tête (raison sociale + email), `<select disabled>` (FR sélectionné, EN désactivé), liens « Mon compte » → `/parametres`, « Paramètres » → `/parametres`, séparateur, bouton « Déconnexion » → `useAuthStore().logout()`. Libellés FR figés (réutilisables via constantes `SHELL_LABELS_FR`).
- [X] T071 [US8] Monter `<TheAvatarMenu />` dans `TheHeader.vue`.

**Checkpoint US8**: menu avatar accessible, déconnexion opérationnelle, EN visible mais inactif.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: finalisation, audits, performance, validation manuelle.

- [X] T072 [P] Lancer `pnpm vitest run --coverage` côté frontend ; viser ≥ 80 % sur `app/components/shell`, `app/composables`, `app/stores/notifications.ts`, `app/middleware`. Compléter les tests manquants si gap. — _62 fichiers / 302 tests passent ; couverture globale 92 %_
- [X] T073 [P] Lancer `pytest backend/tests/notifications --cov=app.notifications.stream` ; viser ≥ 80 %. — _100 % (test générateur ajouté)_
- [X] T074 [P] Audit a11y : exécuter `axe-core` sur les 3 layouts (test unitaire `frontend/tests/unit/shell/a11y.spec.ts`) ; corriger les violations level A/AA. Vérifier focus visible et focus-trap dans drawer + palette + popovers. — _3/3 layouts sans violation WCAG 2 A/AA (color-contrast et region désactivés car hors contexte jsdom)_
- [ ] T075 [P] Mesure bundle : `pnpm nuxi build && pnpm nuxi analyze` ; vérifier que l'overhead shell sur la route `/dashboard` reste ≤ 35 kB gzipped vs `/login`. — _à exécuter manuellement (build complet hors session)_
- [X] T076 [P] Passe ESLint (`make lint`) + Ruff (backend) ; corriger les warnings. — _Ruff clean (6 warnings UP017/UP012 auto-fixés). ESLint : config flat ESLint v9 absente (pré-existant, hors scope F38)_
- [X] T077 Extraire les libellés FR du shell vers `frontend/app/utils/shell-labels-fr.ts` (préparation i18n future, R-018).
- [ ] T078 Exécuter `quickstart.md` S-001 → S-009 manuellement et cocher chaque smoke-test ; capturer une screenshot par layout pour le « 0 régression visuelle » SC-010 (référence dans `specs/038-app-shell-navigation/screenshots/`). — _validation manuelle utilisateur requise_
- [X] T079 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F38 `done` + dater.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : aucune dépendance — démarre immédiatement.
- **Foundational (Phase 2)** : dépend de Phase 1 — BLOQUE toutes les US.
- **US1 / US2 / US5** : peuvent démarrer en parallèle dès la fin de Phase 2 (un dev par US).
- **US3** : dépend de US1 (le `TheCommandPalette` se monte dans `layouts/default.vue`).
- **US4** : dépend de US1 (drawer modifie `layouts/default.vue`).
- **US6** : dépend de US1 (cloche dans header) ; le backend stub (T056-T057) peut être livré en parallèle dès Phase 2.
- **US7 / US8** : dépendent de US1 (composants montés dans `TheHeader.vue`) — peuvent démarrer en parallèle après US1.
- **Polish (Phase 11)** : dépend de toutes les US ciblées.

### Within Each User Story

- Tests (TDD) écrits avant l'implémentation — vérifier qu'ils ÉCHOUENT, puis implémenter, puis vérifier qu'ils PASSENT.
- Composables/stores avant composants qui les consomment.
- Layouts après les composants `The*` qu'ils montent (sauf stubs vides intermédiaires).

### Parallel Opportunities

- T002, T003, T004, T005 : tous [P] (créations de répertoires indépendants).
- T007/T008, T009/T010, T012, T014, T016 : tests Foundational [P].
- T018/T019, T020/T021 : composants US1 [P] (fichiers distincts).
- T025/T026, T027/T028 : layouts US2 [P] (fichiers distincts).
- T032/T033 : tests US3 [P].
- T039/T040, T041 : tests + composant US4 [P].
- T044/T045, T050-T055 : tests US5 + tests US6 [P].
- T056, T058-T062 : composants US6 [P] (chacun son fichier).
- US7, US8 : démarrent en parallèle dès la fin de US1.

---

## Parallel Example: kick-off post-Foundational

```bash
# Dev A — US1 (squelette PME)
Task: T020 TheSidebar.vue + T018 spec
Task: T021 TheHeader.vue + T019 spec
Task: T022 layouts/default.vue
Task: T024 default-layout.spec

# Dev B — US2 (public + auth)
Task: T027 layouts/public.vue + T026 spec
Task: T028 layouts/auth.vue + T025 spec
Task: T029 + T030 + T031 routage meta

# Dev C — US5 (routes protégées)
Task: T044 + T046 auth.global.ts
Task: T045 admin.ts (audit)
Task: T047 plugin auth-unauthorized
Task: T048 + T049

# Dev D — US6 backend stub (peut démarrer dès Phase 2)
Task: T050 test_stream.py
Task: T056 stream.py
Task: T057 patch main.py
```

---

## Implementation Strategy

### MVP First (US1 + US5 + minimum US6)

1. Phase 1 : Setup (T001-T005)
2. Phase 2 : Foundational (T006-T017)
3. Phase 3 : US1 — Squelette PME (T018-T024)
4. Phase 7 : US5 — Routes protégées (T044-T049)
5. Phase 8 : US6 minimum — `TheRouteProgress` + `TheOfflineBanner` + `TheErrorBoundary` + toasts (T053-T055, T060-T062, T064-T065)
6. **STOP & DEMO** : un user PME peut se connecter, naviguer 5 rubriques, voir progression et états globaux.

### Incremental Delivery

7. + US2 (T025-T031) — ouvre l'inscription publique + verify
8. + US3 (T032-T038) — palette Cmd+K
9. + US4 (T039-T043) — mobile drawer + bottom-nav
10. + US6 cloche+SSE (T050-T052, T056-T059, T063) — notifications temps réel
11. + US7 (T066-T068) — breadcrumbs
12. + US8 (T069-T071) — menu avatar / langue
13. Phase 11 (T072-T079) — polish, audits, screenshot SC-010

### Parallel Team Strategy

Avec 4 développeurs après Foundational :
- Dev A : US1 → US3 → US7
- Dev B : US2 → US8
- Dev C : US5 → US4
- Dev D : US6 (backend SSE + tests + composants)

Soudure finale : Polish (T072-T079) en commun.

---

## Notes

- 79 tâches au total, organisées en 11 phases.
- 8 user stories : 6 P1 (US1-US6) + 2 P2 (US7-US8).
- TDD respecté : tests écrits avant chaque composant/composable/store/middleware.
- Aucun bypass de la constitution :
  - P2 (RLS) : aucune nouvelle table, lectures via endpoints F02/F34 déjà gardés.
  - P3 (audit) : `markRead` délègue à F34 qui journalise.
  - P7 : seuls `PME` et `Admin` reconnus.
- Chemins absolus, fichiers distincts maximisés pour la parallélisation.
- Polish phase couvre coverage 80 %, a11y axe-core, bundle budget, lint, et validation manuelle quickstart S-001 → S-009.
