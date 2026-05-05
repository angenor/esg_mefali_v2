<script setup lang="ts">
// F52 US4 — Vue principale : candidatures actives sur l'URL courante.
import CandidatureCard from "../components/CandidatureCard.vue"
import type { SidepanelCandidatureItem } from "../lib/api"

interface Props {
  items: SidepanelCandidatureItem[]
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "open", id: string): void
}>()
</script>

<template>
  <section class="space-y-2 px-3 py-2" data-testid="active-candidatures-view">
    <div
      v-if="props.items.length === 0"
      class="rounded border border-dashed border-slate-200 p-3 text-xs text-slate-500"
      data-testid="candidatures-empty"
    >
      Aucune candidature active pour cette page.
    </div>
    <CandidatureCard
      v-for="item in props.items"
      :key="item.id"
      :item="item"
      @open="(id) => emit('open', id)"
    />
  </section>
</template>
