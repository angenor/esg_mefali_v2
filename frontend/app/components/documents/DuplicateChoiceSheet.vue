<!--
  F50 T027 — DuplicateChoiceSheet (bottom sheet F39 — FR-006b).
  3 actions : Réutiliser / Forcer un nouvel envoi / Annuler.
-->
<script setup lang="ts">
import { computed } from 'vue'
import type { DocumentDetail } from '~/types/documents'

interface Props {
  open: boolean
  filename: string
  existing: DocumentDetail | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'reuse', existingId: string): void
  (e: 'force-new'): void
  (e: 'cancel'): void
}>()

const formattedDate = computed(() => {
  if (!props.existing) return ''
  try {
    return new Date(props.existing.created_at).toLocaleString('fr-FR')
  } catch {
    return props.existing.created_at
  }
})
</script>

<template>
  <transition name="sheet">
    <div
      v-if="open"
      class="fixed inset-0 z-40 flex items-end justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label="Document déjà connu"
      @click.self="emit('cancel')"
    >
      <div class="w-full max-w-lg rounded-t-3xl bg-white p-6 shadow-xl sm:rounded-3xl">
        <h2 class="text-lg font-semibold text-gray-900">
          Document déjà connu
        </h2>
        <p class="mt-1 text-sm text-gray-600">
          Le fichier « {{ filename }} » correspond à un document déjà téléversé.
        </p>

        <div
          v-if="existing"
          class="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm"
        >
          <p class="font-medium text-gray-900">{{ existing.name }}</p>
          <p class="text-xs text-gray-500">
            Téléversé le {{ formattedDate }} · statut OCR : {{ existing.ocr_status }}
          </p>
        </div>

        <div class="mt-5 flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            class="flex-1 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700"
            @click="existing && emit('reuse', existing.id)"
          >
            Réutiliser le document existant
          </button>
          <button
            type="button"
            class="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-900 hover:bg-gray-50"
            @click="emit('force-new')"
          >
            Forcer un nouvel envoi
          </button>
        </div>
        <button
          type="button"
          class="mt-2 w-full rounded-xl px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
          @click="emit('cancel')"
        >
          Annuler
        </button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
</style>
