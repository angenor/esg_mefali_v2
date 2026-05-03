# Phase 0 — Research: App Shell, Layout & Navigation (F38)

> Toutes les NEEDS CLARIFICATION du Technical Context du `plan.md` ont été
> résolues. Ce document trace les décisions techniques et leurs alternatives
> rejetées.

## R-001 — Stratégie de layouts Nuxt 4

- **Decision** : utiliser le mécanisme natif `definePageMeta({ layout: 'default' | 'public' | 'auth' })` page par page, avec `default` comme valeur par défaut. Les pages publiques et auth déclarent explicitement leur layout. Aucune logique de switch dans `app.vue`.
- **Rationale** : c'est le mécanisme de premier ordre supporté par Nuxt 4, SSR-safe, sans coût runtime, et il garantit que le bundle d'une page publique n'embarque pas le code de la sidebar PME.
- **Alternatives rejetées** : (a) calculer le layout via `route.path.startsWith('/auth')` dans `app.vue` — fragile et invisible au routeur ; (b) un seul layout conditionnel — explose le bundle initial.

## R-002 — Garde d'authentification SSR-safe

- **Decision** : étendre `middleware/auth.global.ts` pour : (1) lire le cookie de session via `useRequestEvent()` (SSR) ou `document.cookie` (client) — l'existant utilise déjà la composable `useAuth().user` hydratée ; (2) si `route.meta.public === true` → laisser passer ; (3) sinon, redirect `/login?redirect=<encoded path>` ; (4) si déjà authentifié et la route est `/login` ou `/register` → redirect `/dashboard`.
- **Rationale** : un middleware global garantit qu'aucune nouvelle page ne peut être ajoutée sans gard, conforme P2 (défense par défaut). La preservation de la destination dans `?redirect=` est l'usage standard et sans état serveur.
- **Alternatives rejetées** : (a) middleware named appliqué case par case — risque d'oubli ; (b) stockage de la destination en sessionStorage — non SSR-safe.

## R-003 — Séparation PME / Admin

- **Decision** : créer `middleware/pme-only.ts` (named) appliqué via `definePageMeta({ middleware: ['pme-only'] })` sur les pages PME, en parallèle du `admin.ts` existant (déjà appliqué aux routes `/admin/*`). Le middleware lit `useAuth().user.role` et redirect vers `/dashboard` (admin → PME-only) ou `/admin` (PME → admin).
- **Rationale** : `admin.ts` existe déjà ; symétrie par named middleware ≥ middleware global multi-rôles. Évite de coupler le middleware global à toute la matrice de rôles.
- **Alternatives rejetées** : combiner tout dans `auth.global.ts` — viole le principe de responsabilité unique ; rendre le middleware par défaut sur tous les pages — Nuxt 4 ne permet pas un default named middleware.

## R-004 — Notifications temps réel — SSE vs WebSocket vs polling

- **Decision** : SSE (`text/event-stream`) sur `GET /me/events`, fallback polling `GET /me/notifications?since=<ts>` toutes les 60 s en cas d'erreur de stream ou d'absence de support (`EventSource` indisponible). Le stub livré dans F38 émet uniquement un keepalive `:ping` toutes les 30 s ; les vrais événements `notification.created` viendront de F41.
- **Rationale** : SSE est unidirectionnel serveur → client (parfait pour push de notifications), simple à proxifier, supporté nativement par tous les navigateurs evergreen, sans handshake spécifique. Le polling 60 s est dégradé mais acceptable et garantit la non-régression hors-ligne.
- **Alternatives rejetées** : (a) WebSocket — overkill, requiert proxy spécifique en prod ; (b) polling seul — coût serveur et latence > 2 s en moyenne, viole SC-007.

## R-005 — Stub SSE backend — `sse-starlette` vs implémentation manuelle

- **Decision** : ajouter `sse-starlette` (déjà compatible FastAPI) en dépendance backend. Endpoint stub : `GET /me/events` retourne un `EventSourceResponse` qui émet un keepalive `:ping` toutes les 30 s tant que la connexion reste ouverte ; aucun événement métier (à compléter par F41).
- **Rationale** : `sse-starlette` gère la déconnexion client, les keepalives et le formatage SSE conformes ; ~250 lignes économisées vs implémentation manuelle. Maintenue, MIT, publiée sur PyPI.
- **Alternatives rejetées** : implémentation manuelle avec `StreamingResponse` — bug-prone (gestion fine du flush), tests plus lourds.

## R-006 — Palette de commandes — moteur de recherche

- **Decision** : registre statique d'actions (objets `{id, label, description?, icon?, route?, run?, keywords?}`) maintenu dans `useCommandPalette()`. Filtre via match fuzzy simple en JS pur (lowercase + substring + score sur correspondance préfixe). Pas de bibliothèque externe.
- **Rationale** : la palette MVP cible 11 routes + ~10 actions ; un fuzzy maison < 30 LOC est suffisant et zéro-dépendance. Évite Fuse.js (~10 kB gzipped).
- **Alternatives rejetées** : Fuse.js — bibliothèque puissante mais surdimensionnée ; Algolia / Meili — incompatible avec « actions/pages locales uniquement » au MVP.

## R-007 — Raccourcis clavier de la palette

- **Decision** : écouter `keydown` au niveau `window` dans `useCommandPalette()` (encapsulé dans `onMounted`/`onBeforeUnmount`). Combinaisons supportées : `Cmd+K` (macOS), `Ctrl+K` (Windows/Linux), `/` comme alias texte. Détection plateforme via `navigator.platform` (best-effort, pas de garantie).
- **Rationale** : `Cmd/Ctrl+K` est le standard de facto (Linear, GitHub, Vercel). `/` couvre les cas où la combinaison est interceptée par l'OS. Aucune dépendance.
- **Alternatives rejetées** : `mousetrap` ou `@vueuse/core useMagicKeys` — utile mais ajoute une dépendance pour 30 LOC.

## R-008 — Breadcrumbs — métadonnées de route

- **Decision** : chaque page déclare ses fils d'Ariane via `definePageMeta({ breadcrumb: [{ label: 'Projets', to: '/projets' }, { label: ':projetName' }] })`. Les segments dynamiques sont marqués par préfixe `:` et résolus à l'exécution par `useBreadcrumbs()` à partir de `route.params` ou via un slot/résolveur enregistré par la page elle-même.
- **Rationale** : déclaratif, SSR-safe, n'embarque aucune logique côté shell. Permet à chaque page de contrôler son fil sans toucher au shell.
- **Alternatives rejetées** : (a) construire le breadcrumb depuis `route.matched` — fragile pour les noms dynamiques ; (b) stocker dans Pinia — couplage inutile.

## R-009 — File de toasts globale

- **Decision** : réutiliser le composable `useToast()` et le composant `<UiToastHost />` livrés par F37. Le shell se contente de monter `<UiToastHost />` une seule fois dans `app.vue`.
- **Rationale** : pas de duplication ; le contrat F37 est déjà couvert par tests.
- **Alternatives rejetées** : créer un système parallèle — viole DRY.

## R-010 — Bannière hors-ligne

- **Decision** : composable `useOnlineStatus()` qui écoute `online`/`offline` events sur `window` (encapsulé `onMounted`). Composant `TheOfflineBanner.vue` (bannière fixe `top-0`, hauteur 28 px, fond `--color-warning-100`) affiché quand `!isOnline.value`.
- **Rationale** : API navigateur native, zéro dépendance, suffisant pour SC initial.
- **Alternatives rejetées** : ping périodique vers un endpoint backend — coûteux et faux positif si le serveur tombe ≠ connexion utilisateur.

## R-011 — ErrorBoundary

- **Decision** : utiliser `<NuxtErrorBoundary>` natif de Nuxt 4 pour envelopper le slot par défaut dans `layouts/default.vue` et `layouts/public.vue` ; en cas d'erreur, rendre `<TheErrorBoundary :error="..." @reload="...">` qui affiche un message FR + bouton « Recharger » qui appelle `clearError({ redirect: route.fullPath })`.
- **Rationale** : le composant natif Nuxt gère déjà la capture d'erreur ; rien à réinventer.
- **Alternatives rejetées** : `try/catch` global manuel — manque les erreurs async sans `await` exposé ; bibliothèque tierce — superflue.

## R-012 — Barre de progression de transition de route

- **Decision** : `TheRouteProgress.vue` utilise les hooks Nuxt `app:beforeRouteUpdate` et `page:finish` (via `useNuxtApp().hook(...)`) pour afficher une barre 2 px brand-500 animée par `gsap` (translateX + opacity). Si `prefers-reduced-motion` → animation désactivée, juste l'apparition/disparition.
- **Rationale** : pas de polling ni de plugin tiers (`vue-progressbar`, `nprogress`) ; intégration native Nuxt.
- **Alternatives rejetées** : `nprogress` — ajoute ~5 kB et un système de styles parallèle.

## R-013 — Sidebar collapse / drawer mobile

- **Decision** : breakpoint à 1024 px (Tailwind `lg`). Au-dessus : sidebar fixe 256 px (état déplié) ou 64 px (rail compact, toggle utilisateur persistant en `localStorage` côté client). En-dessous : la sidebar disparaît, un bouton hamburger dans `TheHeader` ouvre un drawer (overlay + slide-in 280 px) animé gsap. La bottom-nav apparaît également.
- **Rationale** : 1024 px est le seuil mentionné par le brouillon F38 et concorde avec Tailwind. La persistance localStorage du rail/déplié améliore l'UX power user sans coupler au backend.
- **Alternatives rejetées** : drawer permanent même desktop — perte d'espace écran ; pas de rail compact — 256 px imposés sur petits laptops trop large.

## R-014 — Bottom nav mobile

- **Decision** : 4 cibles fixes (Chat, Tableau de bord, Profil, Plus). « Plus » ouvre un drawer/sheet listant les rubriques absentes (Projets, Scoring, Carbone, Crédit, Candidatures, Rapports, Bibliothèque, Paramètres). Hauteur 56 px + safe area iOS via `env(safe-area-inset-bottom)`. Cibles tactiles ≥ 48 × 48 px.
- **Rationale** : dispositions standard mobile (Material/HIG). « Chat » est inclus en anticipation de F12 (interface conversationnelle).
- **Alternatives rejetées** : 5 icônes — encombre ; FAB central — réservé à une action future.

## R-015 — Sélecteur de langue placeholder

- **Decision** : composant `<select>` natif désactivé pour EN (`disabled`) avec FR sélectionné. Pas d'intégration `@nuxtjs/i18n` au MVP de F38 (introduite plus tard quand les contenus EN seront prêts).
- **Rationale** : minimise la surface, évite d'ajouter un module Nuxt entier pour un placeholder. Le composant peut être remplacé sans rupture API.
- **Alternatives rejetées** : intégrer `@nuxtjs/i18n` dès maintenant — surdimensionné, retarde le MVP.

## R-016 — Format des réponses notifications (consommation F34)

- **Decision** : le store consomme `GET /me/notifications` (existant F34) qui retourne `[{id, kind, title, body, created_at, read_at, link}]`. Le compteur non-lu se calcule côté client (`notifs.filter(n => !n.read_at).length`). « Marquer comme lu » appelle `PATCH /me/notifications/{id}/read`.
- **Rationale** : aucune nouvelle route nécessaire ; F34 est en place.
- **Alternatives rejetées** : ajouter `GET /me/notifications/unread-count` — endpoint dérivable côté client, gain marginal.

## R-017 — Tests SSR pour les middlewares

- **Decision** : tests vitest unitaires des middlewares en mode pur (mocking `useAuth`, `navigateTo`, `useRequestEvent`) ; pas de test e2e SSR dans F38 (couvert plus tard par Playwright en F35).
- **Rationale** : couverture rapide, suffisante pour valider la logique de gard.
- **Alternatives rejetées** : Playwright SSR dès F38 — délai supplémentaire ; outils Nuxt expérimentaux (`@nuxt/test-utils` end-to-end) — fragiles et lents.

## R-018 — Stratégie d'i18n future (post-MVP)

- **Decision** : noter dans la doc que l'introduction d'`@nuxtjs/i18n` se fera après F38 sans rupture du shell : `useT()` sera substitué aux libellés en dur. F38 isole les libellés FR dans des constantes (`SHELL_LABELS_FR`) pour faciliter cette migration.
- **Rationale** : prépare la migration sans la coûter aujourd'hui.

## R-019 — Audit accessibilité shell

- **Decision** : lancer `axe-core` (déjà en devDependencies) sur les 3 layouts en mode test unitaire (jsdom suffit pour les règles statiques). Pas d'audit clavier complet automatisé au MVP — vérifié manuellement via la matrice de tests dans `quickstart.md`.
- **Rationale** : couverture statique > 0, manuel pour le clavier (gestes complexes).

## R-020 — Performance bundle

- **Decision** : viser ≤ 35 kB gzipped d'overhead shell sur le bundle initial PME. Atteint par : (a) lazy-loading de `TheCommandPalette.vue` (`defineAsyncComponent`) — chargé uniquement au premier `Cmd+K` ; (b) pas d'icônes inutilisées (Heroicons tree-shaké) ; (c) pas de bibliothèque CSS externe.
- **Rationale** : tient sous le budget perçu par utilisateur sur 4G ouest-africaine.

---

**Résolution** : toutes les inconnues techniques sont levées. Aucun blocage pour passer à la Phase 1.
