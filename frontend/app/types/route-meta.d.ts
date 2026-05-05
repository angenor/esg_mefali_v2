// F38 T006 — Extension des métadonnées de route pour le shell
import 'vue-router'
import type { RouteLocationNormalized } from 'vue-router'

export type Crumb = { label: string; to?: string }

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'default' | 'public' | 'auth'
    public?: boolean
    pmeOnly?: boolean
    adminOnly?: boolean
    breadcrumb?: Crumb[] | ((route: RouteLocationNormalized) => Crumb[])
    title?: string
  }
}

export {}
