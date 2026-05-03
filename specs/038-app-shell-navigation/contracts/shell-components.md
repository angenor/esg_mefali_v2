# Contract — Shell Components (F38)

API publique des composants `components/shell/The*.vue`. Tous les composants
sont **singletons** (montés une seule fois dans un layout) et utilisent le
préfixe `The` selon la convention Vue.

> Conventions générales : Composition API + `<script setup>` ; props typées via
> `defineProps<...>()` ; events via `defineEmits<...>()` ; toutes les chaînes
> en français ; SSR-safe (pas d'accès `window`/`document` au top-level).

---

## TheSidebar

**Localisation** : `components/shell/TheSidebar.vue`
**Monté par** : `layouts/default.vue` (desktop ≥ 1024 px)

### Props

| Prop | Type | Défaut | Notes |
|---|---|---|---|
| `collapsed` | `boolean` | `false` | rail compact 64 px si true ; déplié 256 px sinon. |

### Events

| Event | Payload | Quand |
|---|---|---|
| `update:collapsed` | `boolean` | toggle utilisateur (chevron) |

### Slots

Aucun slot exposé (la liste des rubriques est interne, dérivée du registre `useNavRegistry`).

### Comportement

- Liste fixe de 11 rubriques (Tableau de bord, Profil entreprise, Projets, Plan d'action, Scoring ESG, Empreinte carbone, Score crédit, Candidatures, Rapports & attestations, Bibliothèque, Paramètres).
- Met l'item correspondant à `route.path` en état `active`.
- Affiche le `unreadCount` du store sur l'item « Notifications » via `<UiBadge>`.
- En mode `collapsed`, libellés masqués + tooltip au hover via `<UiTooltip>`.
- A11y : `nav[aria-label="Navigation principale"]`, items en `<a>` (router-link), focus visible.

---

## TheHeader

**Localisation** : `components/shell/TheHeader.vue`
**Monté par** : `layouts/default.vue`

### Props

Aucune.

### Events

| Event | Payload | Quand |
|---|---|---|
| `toggle-drawer` | — | bouton hamburger cliqué (mobile uniquement) |

### Comportement

- Affiche : raison sociale (depuis `useAuthStore().user.raison_sociale` — fallback email), `<TheBreadcrumbs />`, `<TheNotificationsBell />`, `<TheAvatarMenu />`.
- En < 1024 px : ajoute un bouton hamburger à gauche (émet `toggle-drawer`).
- Hauteur fixe : 56 px.

---

## TheBottomNav

**Localisation** : `components/shell/TheBottomNav.vue`
**Monté par** : `layouts/default.vue` (uniquement < 1024 px via `<ClientOnly>` + media query CSS)

### Props

Aucune.

### Comportement

- 4 cibles : Chat (`/chat` — placeholder vers F12), Tableau de bord (`/dashboard`), Profil (`/profil`), Plus (ouvre un sheet).
- Cibles ≥ 48 × 48 px.
- Item actif marqué via `route.path`.
- A11y : `nav[aria-label="Navigation rapide"]`.

---

## TheCommandPalette

**Localisation** : `components/shell/TheCommandPalette.vue`
**Monté par** : `layouts/default.vue` (chargé en lazy via `defineAsyncComponent`)

### Props

Aucune.

### Comportement

- État ouvert/fermé géré par `useCommandPalette()`.
- Raccourcis : `Cmd+K`, `Ctrl+K`, `/`. Fermeture : `Esc`.
- Affiche `<input>` recherche + liste filtrée (max 20).
- Navigation clavier : ↑/↓ pour sélectionner, ↵ pour exécuter, ↵ ferme la palette.
- Animation entrée/sortie : 120 ms (gsap), désactivée si `prefers-reduced-motion`.

### Registre d'actions par défaut (livré par F38)

```ts
[
  // Navigation (1 par rubrique sidebar)
  { id: 'nav.dashboard', label: 'Aller au tableau de bord', route: '/dashboard', group: 'Navigation' },
  { id: 'nav.profil', label: 'Aller au profil entreprise', route: '/profil', group: 'Navigation' },
  // … 9 autres
  // Actions
  { id: 'action.logout', label: 'Se déconnecter', run: () => useAuthStore().logout(), group: 'Actions' },
  { id: 'action.toggle-sidebar', label: 'Afficher / masquer la sidebar', run: () => toggleSidebar(), group: 'Actions' },
  // Aide
  { id: 'help.shortcuts', label: 'Voir les raccourcis clavier', route: '/parametres#raccourcis', group: 'Aide' },
]
```

---

## TheBreadcrumbs

**Localisation** : `components/shell/TheBreadcrumbs.vue`
**Monté par** : `TheHeader.vue`

### Props

Aucune (lit `useBreadcrumbs()`).

### Comportement

- Rend `Crumb[]` séparés par `/` (caractère + `aria-hidden`).
- Tous les segments sauf le dernier sont des `<NuxtLink :to="to">`.
- Le dernier segment est un `<span aria-current="page">`.
- Tronque les libellés > 40 caractères avec ellipsis CSS.

---

## TheNotificationsBell

**Localisation** : `components/shell/TheNotificationsBell.vue`
**Monté par** : `TheHeader.vue`

### Props

Aucune.

### Comportement

- Bouton icône cloche + badge `unreadCount` (depuis `useNotificationsStore`).
- Click → ouvre un `<UiPopover>` ancré sous l'icône.
- Popover contient : titre « Notifications », liste `latestUnread` (max 5), lien « Voir toutes » → `/notifications`.
- Click sur une notif : `markRead(id)` puis `navigateTo(notif.link)` si `link` présent.
- A11y : `aria-label="Notifications, X non lues"`, `aria-expanded`, focus retourne au bouton à la fermeture.

---

## TheAvatarMenu

**Localisation** : `components/shell/TheAvatarMenu.vue`
**Monté par** : `TheHeader.vue`

### Props

Aucune.

### Comportement

- Bouton avec `<UiAvatar>` (initiales depuis `user.email`).
- Click → `<UiPopover>` avec :
  - en-tête : `user.raison_sociale` (ou email) + `user.email` en sous-titre ;
  - sélecteur langue (FR actif, EN désactivé) ;
  - lien « Mon compte » → `/parametres`.
  - lien « Paramètres » → `/parametres`.
  - séparateur ;
  - bouton « Déconnexion » → `useAuthStore().logout()`.

---

## TheRouteProgress

**Localisation** : `components/shell/TheRouteProgress.vue`
**Monté par** : `app.vue` (visible sur tous layouts)

### Props

Aucune.

### Comportement

- Barre 2 px, `position: fixed; top: 0; left: 0; right: 0; z-index: 9999;`.
- Visible entre `page:start` et `page:finish` (hooks Nuxt).
- Animation gsap : translateX 0 → 80 % en 400 ms, puis 80 % → 100 % à `page:finish` + fade-out 200 ms.
- Si `prefers-reduced-motion` : opacity-only (pas de slide).

---

## TheOfflineBanner

**Localisation** : `components/shell/TheOfflineBanner.vue`
**Monté par** : `app.vue`

### Props

Aucune.

### Comportement

- Visible si `useOnlineStatus().isOnline.value === false`.
- Bandeau fixe `top-0`, hauteur 28 px, fond `--color-warning-100`, texte FR « Connexion perdue. Vos modifications ne seront pas enregistrées tant que la connexion n'est pas rétablie. ».
- A11y : `role="status"`, `aria-live="polite"`.

---

## TheErrorBoundary

**Localisation** : `components/shell/TheErrorBoundary.vue`
**Monté par** : `layouts/default.vue` et `layouts/public.vue` (via `<NuxtErrorBoundary>` natif).

### Props

| Prop | Type | Notes |
|---|---|---|
| `error` | `Error` | erreur capturée par `<NuxtErrorBoundary>` |

### Events

| Event | Payload | Quand |
|---|---|---|
| `reload` | — | bouton « Recharger » cliqué |

### Comportement

- Affiche : titre « Une erreur est survenue », sous-titre FR, bouton primary « Recharger ».
- En mode dev (`import.meta.dev`), affiche le `error.message` + stack ; sinon, masqué.
- A11y : `role="alert"`.

---

## Tests d'acceptation par composant

| Composant | Test minimal |
|---|---|
| TheSidebar | item actif reflète route ; collapse toggle ; badge unreadCount présent |
| TheHeader | hamburger émet `toggle-drawer` < 1024 px ; raison sociale affichée |
| TheBottomNav | non rendu ≥ 1024 px ; 4 cibles ≥ 48 × 48 px |
| TheCommandPalette | `Cmd+K` ouvre ; tape "scoring" + Enter → navigateTo `/scoring` |
| TheBreadcrumbs | dernier segment non cliquable ; vide → fallback "Accueil" |
| TheNotificationsBell | badge = unreadCount ; click ouvre popover ; click notif → markRead + nav |
| TheAvatarMenu | logout déclenche store.logout ; EN désactivé |
| TheRouteProgress | apparaît sur `page:start`, disparaît sur `page:finish` |
| TheOfflineBanner | apparaît offline, disparaît online |
| TheErrorBoundary | montrer message FR, bouton émet `reload` |
