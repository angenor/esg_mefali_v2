# Phase 1 — Data Model: App Shell, Layout & Navigation (F38)

F38 n'introduit **aucune nouvelle table SQL**. Ce document décrit les
**modèles d'état côté frontend** (stores Pinia, composables, métadonnées de
route) et les **DTO** consommés par le shell, ainsi que les transitions
d'état applicatives.

## 1. Stores Pinia

### 1.1 `useAuthStore` (existant — déjà fourni par F02)

État réutilisé tel quel. Champs consommés par F38 :

| Champ | Type | Notes |
|---|---|---|
| `user` | `null \| { user_id, account_id, role: 'pme' \| 'admin', email, raison_sociale? }` | Source pour la garde et l'affichage du menu avatar. Hydratée au SSR via cookie de session. |
| `isAuthenticated` | `ComputedRef<boolean>` | `!!user.value` |
| `logout()` | `() => Promise<void>` | Appelle `POST /auth/logout`, vide le store, vide `useNotificationsStore`, redirige `/login`. |

### 1.2 `useNotificationsStore` (NEW)

Pinia store SSR-safe (`defineStore('notifications', ...)`).

**State** :

```ts
{
  items: Notification[],          // dernières notifications connues (max 50)
  isStreamConnected: boolean,     // true si SSE actif, false si polling actif
  lastSyncedAt: Date | null,
  loadError: Error | null,
}
```

**Notification (DTO)** — miroir de la réponse `GET /me/notifications` (F34) :

```ts
type Notification = {
  id: string                     // UUID
  kind: 'system' | 'candidature' | 'scoring' | 'attestation' | 'plan_action' | 'admin'
  title: string                  // libellé court FR
  body?: string                  // optionnel, FR
  link?: string                  // route interne ex: '/candidatures/abc'
  created_at: string             // ISO 8601
  read_at: string | null
}
```

**Getters** :

| Getter | Signature | Description |
|---|---|---|
| `unreadCount` | `ComputedRef<number>` | `items.filter(n => !n.read_at).length`, capped à 99+ pour l'affichage. |
| `latestUnread` | `ComputedRef<Notification[]>` | 5 dernières non lues (tri `created_at DESC`). |

**Actions** :

| Action | Signature | Effets |
|---|---|---|
| `loadInitial()` | `() => Promise<void>` | `GET /me/notifications` → remplit `items`. Idempotent. |
| `pushFromStream(evt)` | `(evt: StreamEvent) => void` | Insère ou met à jour un item. Appelée par `useNotificationsStream`. |
| `markRead(id)` | `(id: string) => Promise<void>` | `PATCH /me/notifications/{id}/read` puis met à jour `read_at` localement. |
| `markAllRead()` | `() => Promise<void>` | itère sur `latestUnread`, `Promise.all` des PATCH. |
| `reset()` | `() => void` | vide tout (appelée par `logout()`). |

**Invariants** :

- `items` ne dépasse jamais 50 (FIFO sur `created_at`).
- `markRead` est idempotent (réappel sur un déjà-lu = no-op réseau, pas d'erreur).
- Le store n'est jamais appelé côté SSR (toutes les actions sont gardées par `import.meta.client` ou retournées tôt).

## 2. Composables

### 2.1 `useBreadcrumbs()` (NEW)

```ts
type Crumb = { label: string; to?: string }
function useBreadcrumbs(): ComputedRef<Crumb[]>
```

**Comportement** :

- Lit `useRoute().meta.breadcrumb` (déclaré via `definePageMeta`).
- Format métadonnée : `Crumb[]` ou `(route: RouteLocation) => Crumb[]` (résolveur).
- Si la métadonnée est absente, retourne `[{ label: 'Accueil', to: '/dashboard' }]` par défaut sur les routes PME, `[]` ailleurs.
- Le **dernier segment** est rendu non cliquable (le shell ignore son `to`).

### 2.2 `useCommandPalette()` (NEW)

```ts
type Action = {
  id: string
  label: string                  // FR, ex: 'Aller au scoring ESG'
  description?: string
  icon?: string                  // nom Heroicons
  route?: string                 // si navigation simple
  run?: () => void | Promise<void>  // si action custom
  keywords?: string[]
  group?: 'Navigation' | 'Actions' | 'Aide'
}

function useCommandPalette(): {
  isOpen: Ref<boolean>
  open: () => void
  close: () => void
  toggle: () => void
  query: Ref<string>
  results: ComputedRef<Action[]>
  registerActions: (actions: Action[]) => void
  unregisterActions: (ids: string[]) => void
}
```

**Invariants** :

- Singleton (instance partagée — pattern `useState`/state factory Nuxt).
- Le filtre est insensible à la casse, accents-tolérant (`String.prototype.normalize('NFD').replace(/\p{Diacritic}/gu, '')`).
- Tri : 1) match préfixe label, 2) match substring label, 3) match keywords.
- `results` plafonné à 20 entrées.

### 2.3 `useNotificationsStream()` (NEW)

```ts
function useNotificationsStream(): {
  start: () => void
  stop: () => void
  isConnected: Readonly<Ref<boolean>>
}
```

**Comportement** :

- `start()` ouvre une `EventSource('/me/events')`. À la réception d'un événement `notification.created` (JSON dans `data`), appelle `useNotificationsStore().pushFromStream(...)`.
- En cas d'erreur ou si `EventSource` est indisponible : démarre un polling `setInterval` toutes les 60 s qui appelle `loadInitial()`.
- `stop()` ferme la connexion / clear l'interval. Appelé sur `onBeforeUnmount` et par `logout()`.
- Reconnexion automatique : si l'EventSource ferme involontairement, retry exponentiel (1 s, 2 s, 4 s, 8 s, plafond 30 s).

### 2.4 `useOnlineStatus()` (NEW)

```ts
function useOnlineStatus(): { isOnline: Readonly<Ref<boolean>> }
```

**Comportement** : SSR retourne `true` ; côté client, écoute `online`/`offline` sur `window`.

## 3. Métadonnées de route

### 3.1 Extension de `RouteMeta` (`types/route-meta.d.ts`)

```ts
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'default' | 'public' | 'auth'
    public?: boolean                         // si true, auth.global.ts laisse passer sans session
    pmeOnly?: boolean                        // appliqué via middleware named pme-only
    adminOnly?: boolean                      // appliqué via middleware named admin
    breadcrumb?: Crumb[] | ((route: RouteLocation) => Crumb[])
    title?: string                           // FR — titre <title> et raison sociale par défaut
  }
}
```

**Convention par défaut** :

- Toute page **sans** `meta.public` est considérée privée → `auth.global.ts` impose une session.
- Toute page sous `/admin/*` doit déclarer `middleware: ['admin']` (existant F02).
- Toute page PME doit déclarer `middleware: ['pme-only']` (NEW F38).

## 4. Contrat SSE `/me/events`

Voir `contracts/sse-events.md`. Le **stub F38** émet uniquement :

```text
event: ping
data: 2026-05-03T10:00:00Z
```

toutes les 30 s. Le **contrat F41** ajoutera ultérieurement (sans rupture pour le shell) :

```text
event: notification.created
data: {"id":"...", "kind":"...", "title":"...", "created_at":"...", "link":"..."}
```

## 5. Transitions d'état

### 5.1 Authentification

```text
[Anonyme]
  ↓ POST /auth/login OK
[Authentifié PME]
  ↓ navigation interne
[Authentifié PME]
  ↓ logout() → POST /auth/logout
[Anonyme]

[Anonyme] tentative route privée
  → redirect /login?redirect=<path>
[Authentifié] tentative /login
  → redirect /dashboard

[Authentifié PME] tentative /admin/*
  → middleware admin → 404 + redirect /dashboard
[Authentifié Admin] tentative route PME-only
  → middleware pme-only → redirect /admin
```

### 5.2 Notifications (cycle)

```text
[Mount layout default]
  ↓ useNotificationsStore.loadInitial()
  ↓ useNotificationsStream.start()
[Stream connecté] — événements push → store.pushFromStream
[Stream KO]
  ↓ démarrage polling 60 s
[Polling] — boucle store.loadInitial()
[Reconnexion stream OK] → polling stoppé

[Click cloche] → popover ouvert → liste latestUnread
[Click notification] → markRead(id) puis navigateTo(link)

[Logout]
  ↓ store.reset() + stream.stop()
```

### 5.3 Connexion réseau

```text
[Online] navigator.onLine=true → bannière masquée
[event 'offline'] → isOnline=false → TheOfflineBanner visible
[event 'online'] → isOnline=true → bannière masquée
```

## 6. Validation

| Champ | Règle |
|---|---|
| `Notification.kind` | enum fermé (5 valeurs ci-dessus) — toute autre valeur → notif ignorée + log dev. |
| `Notification.link` | doit commencer par `/` (route interne) — si protocole externe, log dev + lien ouvert dans `_blank rel='noopener'`. |
| `RouteMeta.layout` | enum `'default' \| 'public' \| 'auth'` — si invalide, fallback `'default'` + warn. |
| `Action.id` | unique au niveau registre — collision = remplacement avec warn. |

Aucune validation côté serveur n'est introduite par F38 (les endpoints consommés sont validés côté F02/F34).
