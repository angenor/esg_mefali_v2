<script setup lang="ts">
// F52 US2 — Bottom-sheet de changement de mot de passe.
// Réutilise l'endpoint existant POST /auth/change-password (F02/F42) si présent.
import { ref, computed } from 'vue'

interface Props {
  modelValue: boolean
}
defineProps<Props>()
const emit = defineEmits<{ (e: 'update:modelValue', open: boolean): void }>()

const current = ref('')
const next = ref('')
const confirm = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

const canSubmit = computed(
  () => current.value && next.value && next.value === confirm.value && !submitting.value
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = null
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string
    const { withCsrf } = useCsrf()
    await $fetch(`${apiBase}/auth/change-password`, {
      method: 'POST',
      credentials: 'include',
      headers: withCsrf(),
      body: { current_password: current.value, new_password: next.value },
    })
    current.value = ''
    next.value = ''
    confirm.value = ''
    close()
  } catch (err: unknown) {
    const e = err as { data?: { detail?: { code?: string } } }
    error.value = e?.data?.detail?.code ?? 'change_failed'
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
        aria-label="Changer le mot de passe"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="pwd-change-sheet"
      >
        <header class="mb-3 flex items-start justify-between">
          <h2 class="text-base font-semibold text-gray-900">Changer le mot de passe</h2>
          <button class="text-gray-400" @click="close">×</button>
        </header>
        <form class="space-y-3" @submit.prevent="submit">
          <label class="block text-sm">
            <span>Mot de passe actuel</span>
            <input v-model="current" type="password" required class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label class="block text-sm">
            <span>Nouveau mot de passe</span>
            <input v-model="next" type="password" required class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label class="block text-sm">
            <span>Confirmer</span>
            <input v-model="confirm" type="password" required class="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <p v-if="error" class="text-xs text-red-700">Échec : {{ error }}</p>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="rounded border px-3 py-1.5 text-sm" @click="close">Annuler</button>
            <button :disabled="!canSubmit" type="submit" class="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
              Enregistrer
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
