<template>
  <div class="confirmation-sheet flex flex-col gap-4 p-4">
    <header>
      <h2 class="text-lg font-semibold text-gray-900">{{ question }}</h2>
      <p v-if="contextSummary" class="text-sm text-gray-600 mt-1">{{ contextSummary }}</p>
    </header>

    <div class="flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
      <button
        type="button"
        class="px-4 py-2 rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
        :aria-label="cancelLabel"
        @click="onCancel"
      >
        {{ cancelLabel }}
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700"
        :aria-label="confirmLabel"
        @click="onConfirm"
      >
        {{ confirmLabel }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * BottomSheetConfirmation — template P10-compliant pour confirmer une mutation
 * destructive (US3, F55). Émet `confirm` ou `cancel` au parent.
 */
import { computed } from 'vue'

interface Props {
  question?: string
  context?: Record<string, unknown> | null
  confirmLabel?: string
  cancelLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  question: "Confirmer l'opération ?",
  context: () => null,
  confirmLabel: 'Oui, confirmer',
  cancelLabel: 'Non, annuler',
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const contextSummary = computed<string>(() => {
  const ctx = props.context
  if (!ctx) return ''
  // Affiche un résumé sobre des arguments du tool d'origine
  return Object.entries(ctx)
    .filter(([k]) => k !== 'confirm')
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join(' · ')
})

function onConfirm(): void {
  emit('confirm')
}

function onCancel(): void {
  emit('cancel')
}
</script>
