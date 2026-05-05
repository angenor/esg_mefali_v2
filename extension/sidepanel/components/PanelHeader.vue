<script setup lang="ts">
// F52 US4 — En-tête du sidepanel avec navigation entre les vues.
import { computed } from "vue"

interface Props {
  currentRoute: string
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "navigate", route: string): void
}>()

const tabs = [
  { id: "candidatures", label: "Candidatures" },
  { id: "offers", label: "Offres" },
  { id: "chat", label: "Chat" },
]

const isActive = (id: string): boolean => props.currentRoute === id
const ariaCurrent = (id: string): "page" | undefined =>
  isActive(id) ? "page" : undefined

const headerTitle = computed(() => "ESG Mefali")
</script>

<template>
  <header class="border-b border-slate-200 bg-white px-4 py-3">
    <h1 class="text-base font-semibold text-emerald-700">{{ headerTitle }}</h1>
    <p class="text-xs text-slate-500">Panneau d'aide à la candidature</p>
    <nav class="mt-2 flex gap-3 text-xs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="rounded px-2 py-1 transition"
        :class="
          isActive(tab.id)
            ? 'bg-emerald-100 text-emerald-800 font-medium'
            : 'text-slate-600 hover:bg-slate-100'
        "
        :aria-current="ariaCurrent(tab.id)"
        :data-testid="`tab-${tab.id}`"
        @click="emit('navigate', tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>
  </header>
</template>
