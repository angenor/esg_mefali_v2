// F52 US1 — Composable de gestion des filtres /notifications.
// Sync optionnelle vers la query string de l'URL.
import { computed, watch } from 'vue'
import {
  useNotificationsStore,
  type NotificationFilters,
  type NotificationKind,
} from '~/stores/notifications'

const VALID_KINDS: ReadonlySet<NotificationKind> = new Set([
  'deadline_j_minus_30',
  'deadline_j_minus_7',
  'deadline_j_minus_1',
  'candidature_inactive',
  'offre_recommandee',
  'system',
])

function parseKindList(raw: unknown): NotificationKind[] {
  if (typeof raw === 'string') return raw.split(',').filter((k): k is NotificationKind => VALID_KINDS.has(k as NotificationKind))
  if (Array.isArray(raw)) return raw.filter((k): k is NotificationKind => typeof k === 'string' && VALID_KINDS.has(k as NotificationKind))
  return []
}

export function useNotificationsFilters(syncToQuery: boolean = true) {
  const store = useNotificationsStore()
  const route = useRoute()
  const router = useRouter()

  const filters = computed<NotificationFilters>({
    get: () => store.filters,
    set: (v) => store.setFilters(v),
  })

  function fromQuery() {
    const q = route.query
    store.setFilters({
      unreadOnly: q.unread === '1' || q.unread === 'true',
      kinds: parseKindList(q.kind),
      from: typeof q.from === 'string' ? q.from : null,
      to: typeof q.to === 'string' ? q.to : null,
    })
  }

  function toQuery() {
    if (!syncToQuery) return
    const f = store.filters
    const q: Record<string, string | undefined> = {}
    if (f.unreadOnly) q.unread = '1'
    if (f.kinds.length > 0) q.kind = f.kinds.join(',')
    if (f.from) q.from = f.from
    if (f.to) q.to = f.to
    void router.replace({ path: route.path, query: q as Record<string, string> })
  }

  function setUnreadOnly(value: boolean) {
    store.setFilters({ unreadOnly: value })
    toQuery()
  }

  function toggleKind(kind: NotificationKind) {
    const set = new Set(store.filters.kinds)
    if (set.has(kind)) set.delete(kind)
    else set.add(kind)
    store.setFilters({ kinds: [...set] })
    toQuery()
  }

  function reset() {
    store.resetFilters()
    toQuery()
  }

  watch(
    () => route.query,
    () => {
      if (syncToQuery) fromQuery()
    },
    { immediate: true }
  )

  return {
    filters,
    setUnreadOnly,
    toggleKind,
    reset,
    fromQuery,
    toQuery,
  }
}
