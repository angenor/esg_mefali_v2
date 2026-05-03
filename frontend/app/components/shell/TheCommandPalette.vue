<script setup lang="ts">
// F38 T035 — TheCommandPalette (Cmd/Ctrl+K, fuzzy search, navigation clavier)
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCommandPalette, type CommandAction } from '~/composables/useCommandPalette'
import { useReducedMotion } from '~/composables/useReducedMotion'

const palette = useCommandPalette()
const reduced = useReducedMotion()

const inputRef = ref<HTMLInputElement | null>(null)
const dialogRef = ref<HTMLElement | null>(null)
const activeIndex = ref(0)

const groupedResults = computed(() => {
  const groups: Record<string, CommandAction[]> = {}
  for (const a of palette.results.value) {
    const g = a.group ?? 'Actions'
    if (!groups[g]) groups[g] = []
    groups[g].push(a)
  }
  return groups
})

const flatResults = computed(() => palette.results.value)

watch(
  () => palette.query.value,
  () => {
    activeIndex.value = 0
  }
)

watch(
  () => palette.isOpen.value,
  async (open) => {
    if (open) {
      activeIndex.value = 0
      await nextTick()
      inputRef.value?.focus()
      if (!reduced.value && dialogRef.value) {
        try {
          const { gsap } = await import('gsap')
          gsap.fromTo(
            dialogRef.value,
            { opacity: 0, y: -8 },
            { opacity: 1, y: 0, duration: 0.12, ease: 'power1.out' }
          )
        } catch {
          // gsap absent en test : pas grave, transition CSS prendra le relais
        }
      }
    }
  }
)

function isMac(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Mac|iPod|iPhone|iPad/.test(navigator.platform)
}

function onKeydownGlobal(e: KeyboardEvent): void {
  // Ouverture : Cmd+K (mac) / Ctrl+K (autres) / "/"
  const opensPalette =
    (e.key === 'k' || e.key === 'K') && (isMac() ? e.metaKey : e.ctrlKey)
  if (opensPalette) {
    e.preventDefault()
    palette.toggle()
    return
  }
  if (e.key === '/' && !palette.isOpen.value) {
    const target = e.target as HTMLElement | null
    const tag = target?.tagName.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return
    e.preventDefault()
    palette.open()
    return
  }
  if (!palette.isOpen.value) return
  if (e.key === 'Escape') {
    e.preventDefault()
    palette.close()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    const max = flatResults.value.length
    if (max === 0) return
    activeIndex.value = (activeIndex.value + 1) % max
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    const max = flatResults.value.length
    if (max === 0) return
    activeIndex.value = (activeIndex.value - 1 + max) % max
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    const action = flatResults.value[activeIndex.value]
    if (action) void execute(action)
  }
}

async function execute(action: CommandAction): Promise<void> {
  try {
    if (action.run) {
      await action.run()
    } else if (action.route) {
      await navigateTo(action.route)
    }
  } finally {
    palette.close()
  }
}

function isActive(action: CommandAction): boolean {
  return flatResults.value[activeIndex.value]?.id === action.id
}

onMounted(() => {
  if (typeof document === 'undefined') return
  document.addEventListener('keydown', onKeydownGlobal, true)
})

onBeforeUnmount(() => {
  if (typeof document === 'undefined') return
  document.removeEventListener('keydown', onKeydownGlobal, true)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="palette.isOpen.value"
      class="fixed inset-0 z-[1000] flex items-start justify-center bg-black/40 px-4 pt-24"
      data-testid="command-palette-backdrop"
      @click.self="palette.close()"
    >
      <div
        ref="dialogRef"
        role="dialog"
        aria-modal="true"
        aria-label="Palette de commandes"
        class="w-full max-w-xl overflow-hidden rounded-lg bg-white shadow-2xl"
        data-testid="command-palette"
      >
        <div class="border-b border-gray-200 p-3">
          <input
            ref="inputRef"
            v-model="palette.query.value"
            type="text"
            placeholder="Rechercher une page, une action…"
            aria-label="Recherche dans la palette de commandes"
            class="w-full bg-transparent text-base outline-none placeholder:text-gray-400"
            data-testid="command-palette-input"
          />
        </div>
        <div class="max-h-80 overflow-y-auto" role="listbox">
          <p
            v-if="flatResults.length === 0"
            class="px-4 py-6 text-center text-sm text-gray-500"
            data-testid="command-palette-empty"
          >
            Aucun résultat.
          </p>
          <template v-else>
            <div v-for="(items, group) in groupedResults" :key="group" class="py-1">
              <div
                class="px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400"
              >
                {{ group }}
              </div>
              <button
                v-for="action in items"
                :key="action.id"
                type="button"
                role="option"
                :aria-selected="isActive(action)"
                :data-active="isActive(action) ? 'true' : 'false'"
                :class="[
                  'flex w-full items-center gap-3 px-3 py-2 text-left text-sm focus:outline-none',
                  isActive(action) ? 'bg-brand-50 text-brand-700' : 'text-gray-800 hover:bg-gray-50',
                ]"
                :data-testid="`command-action-${action.id}`"
                @click="execute(action)"
                @mouseenter="
                  activeIndex = flatResults.findIndex((a) => a.id === action.id)
                "
              >
                <span class="flex-1 truncate">{{ action.label }}</span>
                <span
                  v-if="action.description"
                  class="truncate text-xs text-gray-500"
                >{{ action.description }}</span>
              </button>
            </div>
          </template>
        </div>
        <div
          class="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-3 py-2 text-[11px] text-gray-500"
        >
          <span>↑ ↓ pour naviguer · ↵ pour valider · Échap pour fermer</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
