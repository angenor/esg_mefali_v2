<script setup lang="ts">
// F38 T017 — page stub PME
// F41 T032 — listener EventBus pour sync bidirectionnelle (P8) — refresh
//           déclenché si l'entité `entreprise` est mutée par le LLM.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useChatEventBus } from '~/composables/useChatEventBus'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Profil entreprise' }],
  title: 'Profil entreprise',
})

const lastUpdate = ref<string | null>(null)
const bus = useChatEventBus()
let off: (() => void) | null = null

function refreshIfMatches(): void {
  // Placeholder F08 : marque l'instant de mise à jour. Quand l'éditeur
  // arrivera, remplacer par un appel `await loadEntreprise()`.
  lastUpdate.value = new Date().toISOString()
}

onMounted(() => {
  off = bus.on('entity_updated', (evt) => {
    if (evt.entityType === 'entreprise') refreshIfMatches()
  })
})

onBeforeUnmount(() => {
  off?.()
})
</script>

<template>
  <section class="p-6">
    <h1 class="text-2xl font-bold">Profil entreprise</h1>
    <p class="mt-2 text-gray-600">Page placeholder — éditeur livré par F08.</p>
    <p v-if="lastUpdate" class="mt-2 text-sm text-gray-500">
      Dernière mise à jour reçue : {{ new Date(lastUpdate).toLocaleString('fr-FR') }}
    </p>
  </section>
</template>
