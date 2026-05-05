<script setup lang="ts">
// F52 US6 — Vue : 3 offres recommandées max.
import OfferCard from "../components/OfferCard.vue"
import type { SidepanelOfferItem } from "../lib/api"

interface Props {
  items: SidepanelOfferItem[]
}
const props = defineProps<Props>()

function openMatching(item: SidepanelOfferItem): void {
  // Ouvre dans un nouvel onglet via chrome.tabs si disponible.
  const url = item.matching_url
  const c = (globalThis as unknown as {
    chrome?: { tabs?: { create?: (opts: { url: string }) => void } }
  }).chrome
  if (c?.tabs?.create) {
    c.tabs.create({ url })
  } else {
    window.open(url, "_blank", "noopener")
  }
}
</script>

<template>
  <section class="space-y-2 px-3 py-2" data-testid="recommended-offers-view">
    <div
      v-if="props.items.length === 0"
      class="rounded border border-dashed border-slate-200 p-3 text-xs text-slate-500"
      data-testid="offers-empty"
    >
      Aucune offre recommandée pour le moment.
    </div>
    <OfferCard
      v-for="item in props.items.slice(0, 3)"
      :key="item.id"
      :item="item"
      @open="() => openMatching(item)"
    />
  </section>
</template>
