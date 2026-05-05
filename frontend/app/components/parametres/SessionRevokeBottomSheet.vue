<script setup lang="ts">
// F52 US2 — Bottom-sheet de confirmation de révocation de session.
import { ref, watch } from 'vue'
import { useSessionsStore } from '~/stores/sessions'

interface Props { sessionId: string | null }
const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'close'): void }>()

const store = useSessionsStore()
const submitting = ref(false)

watch(() => props.sessionId, () => {
  submitting.value = false
})

async function confirm() {
  if (!props.sessionId) return
  submitting.value = true
  try {
    await store.revoke(props.sessionId)
    emit('close')
  } catch {
    // store.error
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <section
        v-if="sessionId"
        role="dialog"
        aria-label="Révoquer la session"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="session-revoke-sheet"
      >
        <h2 class="text-base font-semibold text-gray-900">Déconnecter cette session ?</h2>
        <p class="mt-2 text-sm text-gray-600">
          L'utilisateur sera déconnecté de cet appareil à la prochaine requête.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <button type="button" class="rounded border px-3 py-1.5 text-sm" @click="emit('close')">
            Annuler
          </button>
          <button
            type="button"
            class="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white"
            :disabled="submitting"
            data-testid="session-revoke-confirm"
            @click="confirm"
          >
            Révoquer
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
