// F38 T009 — useBreadcrumbs (lit route.meta.breadcrumb)
import { computed, type ComputedRef } from 'vue'
import { useRoute, type RouteLocationNormalized } from 'vue-router'
import type { Crumb } from '~/types/route-meta'

const PUBLIC_FALLBACK_LAYOUTS = new Set(['public', 'auth'])

export function useBreadcrumbs(): ComputedRef<Crumb[]> {
  const route = useRoute()

  return computed<Crumb[]>(() => {
    const meta = route.meta as RouteLocationNormalized['meta'] & {
      breadcrumb?: Crumb[] | ((r: RouteLocationNormalized) => Crumb[])
      layout?: string
    }
    const raw = meta.breadcrumb

    if (typeof raw === 'function') {
      try {
        const result = raw(route)
        return Array.isArray(result) ? result : []
      } catch {
        return []
      }
    }
    if (Array.isArray(raw)) {
      return raw
    }
    if (PUBLIC_FALLBACK_LAYOUTS.has(meta.layout ?? 'default')) {
      return []
    }
    return [{ label: 'Accueil', to: '/dashboard' }]
  })
}
