// F38 T034 — useCommandPalette (singleton, registre d'actions, filtre fuzzy)
import { computed, ref, type ComputedRef, type Ref } from 'vue'

export interface CommandAction {
  id: string
  label: string
  description?: string
  icon?: string
  route?: string
  run?: () => void | Promise<void>
  keywords?: string[]
  group?: 'Navigation' | 'Actions' | 'Aide'
}

const MAX_RESULTS = 20

function normalize(text: string): string {
  return text
    .toLocaleLowerCase('fr-FR')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .trim()
}

function matchScore(action: CommandAction, q: string): number {
  if (!q) return 1
  const haystack = normalize(action.label)
  const kw = (action.keywords ?? []).map(normalize).join(' ')
  if (haystack.startsWith(q)) return 3
  if (haystack.includes(q)) return 2
  if (kw.includes(q)) return 1
  return 0
}

let singleton: {
  isOpen: Ref<boolean>
  query: Ref<string>
  actions: Ref<Map<string, CommandAction>>
  results: ComputedRef<CommandAction[]>
  open: () => void
  close: () => void
  toggle: () => void
  registerActions: (actions: CommandAction[]) => void
  unregisterActions: (ids: string[]) => void
} | null = null

export function useCommandPalette() {
  if (singleton) return singleton

  const isOpen = ref(false)
  const query = ref('')
  const actions = ref<Map<string, CommandAction>>(new Map())

  const results = computed<CommandAction[]>(() => {
    const q = normalize(query.value)
    const list = Array.from(actions.value.values())
      .map((a) => ({ a, s: matchScore(a, q) }))
      .filter((x) => x.s > 0)
    list.sort((x, y) => {
      if (y.s !== x.s) return y.s - x.s
      return x.a.label.localeCompare(y.a.label, 'fr')
    })
    return list.slice(0, MAX_RESULTS).map((x) => x.a)
  })

  function open(): void {
    isOpen.value = true
  }
  function close(): void {
    isOpen.value = false
    query.value = ''
  }
  function toggle(): void {
    if (isOpen.value) close()
    else open()
  }

  function registerActions(list: CommandAction[]): void {
    const next = new Map(actions.value)
    for (const a of list) next.set(a.id, a)
    actions.value = next
  }
  function unregisterActions(ids: string[]): void {
    const next = new Map(actions.value)
    for (const id of ids) next.delete(id)
    actions.value = next
  }

  singleton = {
    isOpen,
    query,
    actions,
    results,
    open,
    close,
    toggle,
    registerActions,
    unregisterActions,
  }
  return singleton
}

// Test-only helper to reset the singleton between tests.
export function __resetCommandPalette(): void {
  singleton = null
}
