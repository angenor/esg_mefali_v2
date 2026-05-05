<script setup lang="ts">
// F52 US2 — Zone dangereuse : suppression compte J+30 + annulation.
import { onMounted, ref } from 'vue'
import { useAccountDeletion } from '~/composables/useAccountDeletion'
import AccountDeletionBottomSheet from './AccountDeletionBottomSheet.vue'

const { store, scheduledDate, load, cancel } = useAccountDeletion()
const sheetOpen = ref(false)

onMounted(async () => {
  await load()
})

async function onCancel() {
  try {
    await cancel()
  } catch {
    // store.error
  }
}
</script>

<template>
  <section class="rounded-lg border border-red-200 bg-red-50/30 p-4">
    <h2 class="text-lg font-semibold text-red-900">Zone dangereuse</h2>
    <p class="mt-1 text-xs text-red-800">
      La suppression du compte intervient 30 jours après votre demande. Vous pouvez
      annuler à tout moment pendant ce délai.
    </p>
    <div v-if="store.isPending" class="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" data-testid="deletion-pending">
      <p>Suppression planifiée pour le <strong>{{ scheduledDate }}</strong>.</p>
      <button
        type="button"
        class="mt-2 rounded border border-amber-300 bg-white px-3 py-1.5 text-xs text-amber-900"
        :disabled="store.saving"
        data-testid="deletion-cancel"
        @click="onCancel"
      >
        Annuler la suppression
      </button>
    </div>
    <button
      v-else
      type="button"
      class="mt-3 rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white"
      data-testid="deletion-open"
      @click="sheetOpen = true"
    >
      Demander la suppression du compte
    </button>
    <AccountDeletionBottomSheet v-model="sheetOpen" />
  </section>
</template>
