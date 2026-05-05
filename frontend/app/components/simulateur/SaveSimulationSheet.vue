<script setup lang="ts">
// F51 T087 — Bottom sheet pour saisir un label et sauvegarder.
import { ref, watch } from "vue"

interface Props {
  open: boolean
}
const props = defineProps<Props>()

const emit = defineEmits<{
  (e: "save", label: string): void
  (e: "cancel"): void
}>()

const label = ref("")
const error = ref<string | null>(null)

watch(
  () => props.open,
  (v) => {
    if (v) {
      label.value = `Simulation ${new Date().toLocaleDateString("fr-FR")}`
      error.value = null
    }
  },
)

function submit(): void {
  const v = label.value.trim()
  if (v.length < 1 || v.length > 120) {
    error.value = "Le label doit faire entre 1 et 120 caractères."
    return
  }
  emit("save", v)
}
</script>

<template>
  <transition name="slide-up">
    <div
      v-if="open"
      class="fixed inset-x-0 bottom-0 z-40 rounded-t-2xl border-t border-gray-200 bg-white p-6 shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-sim-title"
    >
      <h2 id="save-sim-title" class="text-lg font-bold">Sauvegarder la simulation</h2>
      <p class="mt-1 text-sm text-gray-600">
        Donnez un nom à votre simulation pour la retrouver dans l'historique.
      </p>

      <label class="mt-4 block">
        <span class="text-sm font-medium">Nom</span>
        <input
          v-model="label"
          type="text"
          maxlength="120"
          class="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          placeholder="Ex. Solaire 150k 60 mois"
        />
      </label>

      <p v-if="error" class="mt-2 rounded bg-red-50 px-3 py-1.5 text-sm text-red-700">
        {{ error }}
      </p>

      <div class="mt-6 flex justify-end gap-3">
        <button
          type="button"
          class="rounded px-4 py-2 text-sm hover:bg-gray-100"
          @click="emit('cancel')"
        >
          Annuler
        </button>
        <button
          type="button"
          class="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-emerald-700"
          @click="submit"
        >
          Sauvegarder
        </button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
