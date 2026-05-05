<script setup lang="ts">
// F52 US2 — Bottom-sheet de confirmation de suppression de compte.
// Saisie de la raison sociale exacte = preuve d'intention.
import { ref, computed } from 'vue'
import { useAccountDeletion } from '~/composables/useAccountDeletion'

interface Props { modelValue: boolean }
defineProps<Props>()
const emit = defineEmits<{ (e: 'update:modelValue', open: boolean): void }>()

const { store, create } = useAccountDeletion()
const confirmation = ref('')
const motif = ref('')
const submitting = ref(false)
const errorCode = ref<string | null>(null)

const canSubmit = computed(() => confirmation.value.trim().length > 0 && !submitting.value)

function close() {
  emit('update:modelValue', false)
  errorCode.value = null
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  errorCode.value = null
  try {
    await create({
      confirmation_text: confirmation.value.trim(),
      reason_motif: motif.value.trim() || null,
    })
    confirmation.value = ''
    motif.value = ''
    close()
  } catch (err: unknown) {
    const e = err as { data?: { detail?: { code?: string } } }
    errorCode.value = e?.data?.detail?.code ?? 'create_failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <section
        v-if="modelValue"
        role="dialog"
        aria-label="Suppression du compte"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="deletion-sheet"
      >
        <header class="flex items-start justify-between">
          <h2 class="text-base font-semibold text-red-900">Confirmer la suppression</h2>
          <button class="text-gray-400" @click="close">×</button>
        </header>
        <p class="mt-2 text-sm text-gray-700">
          Saisissez la <strong>raison sociale exacte</strong> de votre entreprise pour confirmer.
          La suppression sera planifiée 30 jours après cette confirmation.
        </p>
        <form class="mt-4 space-y-3" @submit.prevent="submit">
          <label class="block text-sm">
            <span>Raison sociale</span>
            <input
              v-model="confirmation"
              type="text"
              required
              class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              data-testid="deletion-confirmation"
            />
          </label>
          <label class="block text-sm">
            <span>Motif (optionnel)</span>
            <textarea
              v-model="motif"
              rows="2"
              class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              data-testid="deletion-motif"
            />
          </label>
          <p v-if="errorCode === 'confirmation_mismatch'" class="text-xs text-red-700" data-testid="deletion-mismatch">
            Le texte saisi ne correspond pas à la raison sociale enregistrée.
          </p>
          <p v-else-if="errorCode === 'already_pending'" class="text-xs text-amber-700">
            Une demande est déjà en cours.
          </p>
          <p v-else-if="errorCode" class="text-xs text-red-700">Échec : {{ errorCode }}</p>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="rounded border px-3 py-1.5 text-sm" @click="close">Annuler</button>
            <button
              type="submit"
              :disabled="!canSubmit"
              class="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              data-testid="deletion-submit"
            >
              Confirmer la suppression
            </button>
          </div>
        </form>
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
