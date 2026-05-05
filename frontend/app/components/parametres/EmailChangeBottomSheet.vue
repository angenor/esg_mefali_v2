<script setup lang="ts">
// F52 US2 — Bottom-sheet changement d'e-mail (P10).
import { ref, computed } from 'vue'
import { useEmailChangeFlow } from '~/composables/useEmailChangeFlow'

interface Props {
  modelValue: boolean
  currentEmail: string
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', open: boolean): void
  (e: 'sent', newEmail: string): void
}>()

const flow = useEmailChangeFlow()
const newEmail = ref('')
const password = ref('')
const submitting = ref(false)

const canSubmit = computed(
  () => newEmail.value.includes('@') && password.value.length > 0 && !submitting.value
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    await flow.requestChange({
      new_email: newEmail.value.trim(),
      current_password: password.value,
    })
    emit('sent', newEmail.value.trim())
    newEmail.value = ''
    password.value = ''
    close()
  } catch {
    // flow.state.error renseigné — affiché sous le formulaire.
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
        aria-label="Modifier l'e-mail"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="email-change-sheet"
      >
        <header class="mb-3 flex items-start justify-between gap-3">
          <h2 class="text-base font-semibold text-gray-900">Modifier l'e-mail</h2>
          <button class="text-gray-400" aria-label="Fermer" @click="close">×</button>
        </header>
        <p class="text-xs text-gray-500">
          E-mail actuel : <span class="font-mono">{{ currentEmail }}</span>
        </p>
        <form class="mt-4 space-y-3" @submit.prevent="submit">
          <label class="block text-sm">
            <span class="block text-gray-700">Nouvel e-mail</span>
            <input
              v-model="newEmail"
              type="email"
              required
              class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              data-testid="email-change-new"
            />
          </label>
          <label class="block text-sm">
            <span class="block text-gray-700">Mot de passe actuel</span>
            <input
              v-model="password"
              type="password"
              required
              class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              data-testid="email-change-password"
            />
          </label>
          <p
            v-if="flow.state.value.error"
            class="text-xs text-red-700"
            data-testid="email-change-error"
          >
            {{ flow.state.value.error === 'invalid_password'
              ? 'Mot de passe incorrect.'
              : flow.state.value.error === 'email_already_used'
                ? 'Cette adresse est déjà utilisée.'
                : 'Échec de la demande, réessayez.' }}
          </p>
          <div class="flex justify-end gap-2 pt-2">
            <button
              type="button"
              class="rounded border border-gray-200 bg-white px-3 py-1.5 text-sm"
              @click="close"
            >
              Annuler
            </button>
            <button
              type="submit"
              :disabled="!canSubmit"
              class="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              data-testid="email-change-submit"
            >
              Vérifier l'e-mail
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
