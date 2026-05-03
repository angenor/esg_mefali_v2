# Contract — Route Meta (F38)

Toutes les pages consommées par le shell DOIVENT déclarer leurs métadonnées
de route via `definePageMeta(...)`. Le shell se base **exclusivement** sur ces
métadonnées (pas de logique conditionnelle hardcodée par chemin).

## Schéma

```ts
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'default' | 'public' | 'auth'      // défaut: 'default'
    public?: boolean                            // défaut: false
    pmeOnly?: boolean                           // défaut: false (utiliser middleware 'pme-only')
    adminOnly?: boolean                         // défaut: false (utiliser middleware 'admin')
    breadcrumb?: Crumb[] | ((route: RouteLocation) => Crumb[])
    title?: string                              // titre <title> (FR)
  }
}

type Crumb = { label: string; to?: string }
```

## Règles d'application

### R-MR-001 — Layout par défaut

Toute page sans `meta.layout` est rendue avec le layout `default`.

### R-MR-002 — Pages publiques

Une page MUST déclarer `public: true` ET `layout: 'public'` pour être :
1. accessible sans session valide (le middleware `auth.global.ts` la laisse passer) ;
2. rendue sans sidebar/top-bar/cloche.

```ts
// pages/verify/[id].vue
definePageMeta({
  layout: 'public',
  public: true,
  title: 'Vérification d\'attestation',
})
```

### R-MR-003 — Pages d'authentification

Une page MUST déclarer `public: true` ET `layout: 'auth'` :

```ts
// pages/login.vue
definePageMeta({
  layout: 'auth',
  public: true,
  title: 'Connexion',
})
```

### R-MR-004 — Pages PME

Une page DOIT être protégée et appliquer le middleware `pme-only` (interdit aux admins) :

```ts
// pages/dashboard.vue
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Tableau de bord' }],
  title: 'Tableau de bord',
})
```

### R-MR-005 — Pages admin

Une page DOIT appliquer le middleware `admin` (existant) :

```ts
// pages/admin/sources/index.vue
definePageMeta({
  layout: 'default',
  middleware: ['admin'],
  breadcrumb: [{ label: 'Admin', to: '/admin' }, { label: 'Sources' }],
  title: 'Sources',
})
```

### R-MR-006 — Breadcrumb dynamique

Pour des segments dynamiques, fournir un résolveur ; il a accès à `route` :

```ts
// pages/projets/[id]/index.vue
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: (route) => [
    { label: 'Projets', to: '/projets' },
    { label: route.params.id as string }, // remplacé en runtime par le titre du projet
  ],
})
```

> Note : pour afficher le **nom** du projet plutôt que son ID, la page peut
> appeler `useBreadcrumbs().setLast({ label: project.value.name })` après
> chargement (mécanisme d'override en runtime, dépendant de la donnée
> chargée).

### R-MR-007 — Titre de page

Le shell met à jour `<title>` avec :

```text
{meta.title ?? 'ESG Mefali'} — ESG Mefali
```

via `useHead({ title: ... })` posé dans `layouts/default.vue` (et adapté pour
les autres layouts).

## Matrice de validation

| Chemin | layout | public | middleware | Comportement attendu |
|---|---|---|---|---|
| `/` (index) | public | true | — | Accueil marketing public |
| `/login` | auth | true | — | Formulaire connexion |
| `/register` | auth | true | — | Formulaire inscription |
| `/forgot-password` | auth | true | — | Demande réinit. |
| `/reset-password` | auth | true | — | Réinit. mdp |
| `/verify/[id]` | public | true | — | Vérification publique attestation |
| `/dashboard` | default | false | `pme-only` | Dashboard PME |
| `/profil` | default | false | `pme-only` | Profil PME |
| `/projets` | default | false | `pme-only` | Liste projets |
| `/scoring` | default | false | `pme-only` | Scoring ESG |
| `/notifications` | default | false | `pme-only` | Centre notifications |
| `/parametres` | default | false | `pme-only` | Paramètres compte |
| `/admin/*` | default | false | `admin` | Console admin |

## Cas d'erreur

- **layout invalide** : log warn + fallback `'default'`.
- **`public: true` sans `layout: 'public' \| 'auth'`** : log warn ; le middleware laisse passer mais la page sera rendue dans `default` (incohérent — à corriger côté page).
- **`middleware: ['pme-only', 'admin']`** simultanés : configuration interdite — la première règle qui rejette gagne, log error en dev.
