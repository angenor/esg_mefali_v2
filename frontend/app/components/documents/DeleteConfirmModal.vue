<!--
  F50 T073 — DeleteConfirmModal (focus trap, ARIA dialog).
  Confirme la suppression d'un document avant soft-delete + purge 30 j.
-->
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

interface Props {
  open: boolean
  documentName: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'confirm'): void
}>()

const cancelBtn = ref<HTMLButtonElement | null>(null)
const submitting = ref(false)

watch(
  () => props.open,
  async (open) => {
    if (open) {
      submitting.value = false
      await nextTick()
      cancelBtn.value?.focus()
    }
  },
)

async function onConfirm(): Promise<void> {
  submitting.value = true
  try {
    emit('confirm')
  } finally {
    submitting.value = false
  }
}

function onKeydown(e: KeyboardEvent): void {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('cancel')
  }
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    role="dialog"
    aria-modal="true"
    aria-labelledby="delete-modal-title"
    @keydown="onKeydown"
  >
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <h2 id="delete-modal-title" class="text-lg font-semibold text-gray-900">
        Supprimer ce document ?
      </h2>
      <p class="mt-2 text-sm text-gray-700">
        <span class="font-medium">{{ documentName }}</span>
        sera retiré immédiatement et définitivement supprimé après 30 jours.
        Cette action est réversible pendant cette période en contactant l'administrateur.
      </p>
      <div class="mt-6 flex justify-end gap-2">
        <button
          ref="cancelBtn"
          type="button"
          class="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50"
          @click="emit('cancel')"
        >Annuler</button>
        <button
          type="button"
          class="rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          :disabled="submitting"
          @click="onConfirm"
        >Supprimer</button>
      </div>
    </div>
  </div>
</template>
