<script setup lang="ts">
// F52 US2 — Bottom-sheet de confirmation de retrait d'un consentement.
import { ref, watch } from 'vue'
import { useConsentsStore } from '~/stores/consents'

interface Props {
  consentId: string | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'close'): void }>()

const store = useConsentsStore()
const submitting = ref(false)

watch(() => props.consentId, () => {
  submitting.value = false
})

async function confirm() {
  if (!props.consentId) return
  submitting.value = true
  try {
    await store.withdraw(props.consentId)
    emit('close')
  } catch {
    // erreur affichée via store.error
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <section
        v-if="consentId"
        role="dialog"
        aria-label="Retirer le consentement"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="consent-withdraw-sheet"
      >
        <h2 class="text-base font-semibold text-gray-900">Retirer le consentement ?</h2>
        <p class="mt-2 text-sm text-gray-600">
          Cette action est tracée dans votre historique RGPD et un e-mail de confirmation
          vous sera envoyé.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <button type="button" class="rounded border px-3 py-1.5 text-sm" @click="emit('close')">
            Annuler
          </button>
          <button
            type="button"
            class="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white"
            :disabled="submitting"
            data-testid="consent-withdraw-confirm"
            @click="confirm"
          >
            Confirmer le retrait
          </button>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: transform 220ms ease;
}
.sheet-enter-from,
.sheet-leave-to {
  transform: translateY(100%);
}
</style>
