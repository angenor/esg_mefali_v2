<script setup lang="ts">
// F51 T066 — Modale double-confirmation soumission (alertdialog).
import { ref, watch } from "vue"
import { useFocusTrap } from "~/composables/useFocusTrap"

interface Props {
  open: boolean
  expectedVersion: number
  inFlight?: boolean
  errorMessage?: string | null
}
const props = withDefaults(defineProps<Props>(), {
  inFlight: false,
  errorMessage: null,
})

const emit = defineEmits<{
  (e: "confirmed", expectedVersion: number): void
  (e: "cancel"): void
}>()

const ack = ref(false)
const dialogRef = ref<HTMLElement | null>(null)
useFocusTrap(dialogRef as unknown as ReturnType<typeof ref<HTMLElement | null>>)

watch(
  () => props.open,
  (v) => {
    if (!v) ack.value = false
  },
)
</script>

<template>
  <transition name="fade">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="submit-title"
    >
      <div ref="dialogRef" class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 id="submit-title" class="text-lg font-bold">
          Confirmer la soumission
        </h2>
        <p class="mt-3 text-sm text-gray-700">
          Une candidature soumise est <strong>figée</strong> et ne peut plus
          être modifiée. Voulez-vous continuer ?
        </p>

        <label class="mt-4 flex items-start gap-3">
          <input v-model="ack" type="checkbox" class="mt-1" />
          <span class="text-sm">
            Je confirme avoir relu mon dossier et accepte qu'il soit figé.
          </span>
        </label>

        <p
          v-if="errorMessage"
          class="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ errorMessage }}
        </p>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="rounded px-4 py-2 text-sm hover:bg-gray-100"
            :disabled="inFlight"
            @click="emit('cancel')"
          >
            Annuler
          </button>
          <button
            type="button"
            class="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-emerald-700 disabled:opacity-40"
            :disabled="!ack || inFlight"
            @click="emit('confirmed', expectedVersion)"
          >
            {{ inFlight ? "Envoi…" : "Soumettre" }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
