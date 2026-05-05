<!--
  F50 T013 — DocumentEmptyState (FR-007b / FR-008b).
  Illustration sobre + titre + corps + CTA primaire.
  Variante "projet" : titre cite explicitement le nom du projet.
-->
<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  context: 'entreprise' | 'projet'
  projetName?: string | null
}

const props = withDefaults(defineProps<Props>(), { projetName: null })

const emit = defineEmits<{
  (e: 'cta-click'): void
}>()

const title = computed(() => {
  if (props.context === 'projet') {
    return props.projetName
      ? `Aucun document pour « ${props.projetName} »`
      : 'Aucun document pour ce projet'
  }
  return 'Aucun document pour le moment'
})

const description = computed(() => {
  if (props.context === 'projet') {
    return 'Déposez les pièces du projet (statuts, devis, factures) ou liez un document de votre entreprise déjà téléversé.'
  }
  return 'Déposez vos statuts, factures, contrats — l\'IA les classera et extraira les données clés automatiquement.'
})

const ctaLabel = computed(() =>
  props.context === 'projet' ? 'Ajouter au projet' : 'Téléverser un document',
)

function onCta(): void {
  emit('cta-click')
}
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-6 py-12 text-center"
    role="region"
    aria-label="Aucun document"
  >
    <svg
      class="h-20 w-20 text-gray-400"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
      />
    </svg>
    <h2 class="text-lg font-semibold text-gray-900">{{ title }}</h2>
    <p class="max-w-md text-sm text-gray-600">{{ description }}</p>
    <button
      type="button"
      class="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
      @click="onCta"
    >
      {{ ctaLabel }}
    </button>
  </div>
</template>
