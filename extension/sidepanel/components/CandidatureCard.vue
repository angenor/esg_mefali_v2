<script setup lang="ts">
// F52 US4 — Carte compacte d'une candidature active.
import type { SidepanelCandidatureItem } from "../lib/api"

interface Props {
  item: SidepanelCandidatureItem
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "open", id: string): void
}>()

function deadlineLabel(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const days = Math.ceil((d.getTime() - now.getTime()) / 86_400_000)
  if (days <= 0) return "Échéance dépassée"
  if (days === 1) return "Demain"
  return `${days} jours restants`
}
</script>

<template>
  <article
    class="rounded border border-slate-200 bg-white p-3 text-sm shadow-sm"
    :data-testid="`candidature-${props.item.id}`"
  >
    <header class="mb-1 flex items-start justify-between gap-2">
      <h3 class="text-sm font-semibold text-slate-900">
        {{ props.item.offer_label }}
      </h3>
      <span class="text-xs font-medium text-emerald-700">
        {{ props.item.completion_pct }}%
      </span>
    </header>
    <p class="text-xs text-slate-500">{{ deadlineLabel(props.item.deadline_at) }}</p>
    <button
      type="button"
      class="mt-2 inline-block rounded bg-emerald-600 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-700"
      :data-testid="`candidature-resume-${props.item.id}`"
      @click="emit('open', props.item.id)"
    >
      Reprendre
    </button>
  </article>
</template>
