<script setup lang="ts">
// F38 T043 — Sheet « Plus » du bottom-nav
import { onMounted, onBeforeUnmount } from 'vue'

const emit = defineEmits<{ close: [] }>()

interface SheetItem {
  id: string
  label: string
  to: string
}

const ITEMS: ReadonlyArray<SheetItem> = [
  { id: 'projets', label: 'Projets', to: '/profil/projets' },
  { id: 'scoring', label: 'Scoring ESG', to: '/scoring' },
  { id: 'carbone', label: 'Empreinte carbone', to: '/carbone' },
  { id: 'credit', label: 'Score crédit', to: '/credit' },
  { id: 'candidatures', label: 'Candidatures', to: '/candidatures' },
  { id: 'rapports', label: 'Rapports & attestations', to: '/rapports' },
  { id: 'bibliotheque', label: 'Bibliothèque', to: '/bibliotheque' },
  { id: 'parametres', label: 'Paramètres', to: '/parametres' },
]

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  if (typeof document !== 'undefined') document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  if (typeof document !== 'undefined') document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-40 flex items-end lg:hidden"
      data-testid="bottom-nav-more"
      @click.self="emit('close')"
    >
      <div class="absolute inset-0 bg-black/40" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Plus de rubriques"
        class="relative w-full max-h-[80vh] overflow-y-auto rounded-t-xl bg-white p-4 shadow-2xl"
      >
        <div class="mx-auto mb-3 h-1 w-10 rounded-full bg-gray-300" aria-hidden="true" />
        <h2 class="mb-3 text-base font-semibold text-gray-900">Plus de rubriques</h2>
        <ul class="space-y-1">
          <li v-for="item in ITEMS" :key="item.id">
            <NuxtLink
              :to="item.to"
              class="flex items-center rounded-md px-3 py-3 text-sm text-gray-800 hover:bg-gray-50"
              @click="emit('close')"
            >
              {{ item.label }}
            </NuxtLink>
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
</template>
