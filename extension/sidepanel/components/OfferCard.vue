<script setup lang="ts">
// F52 US6 — Carte d'offre recommandée.
import type { SidepanelOfferItem } from "../lib/api"

interface Props {
  item: SidepanelOfferItem
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "open", offerId: string): void
}>()

function scorePercent(s: number): number {
  return Math.round(Math.max(0, Math.min(1, s)) * 100)
}
</script>

<template>
  <article
    class="rounded border border-slate-200 bg-white p-3 text-sm shadow-sm"
    :data-testid="`offer-${props.item.id}`"
  >
    <header class="mb-1 flex items-start justify-between gap-2">
      <h3 class="text-sm font-semibold text-slate-900">
        {{ props.item.label }}
      </h3>
      <span class="text-xs font-medium text-blue-700">
        {{ scorePercent(props.item.match_score) }}% match
      </span>
    </header>
    <button
      type="button"
      class="mt-2 inline-block rounded border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800 hover:bg-blue-100"
      :data-testid="`offer-open-${props.item.id}`"
      @click="emit('open', props.item.id)"
    >
      Voir le matching
    </button>
  </article>
</template>
