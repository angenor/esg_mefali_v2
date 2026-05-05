<script setup lang="ts">
// F52 US3 — Bottom sheet de création d'un nouvel export (P10 — saisie hors bulle LLM).
import { ref, computed } from 'vue'
import type { ExportType, ExportFormat, ExportCreateInput } from '~/stores/exports'

interface Props {
  modelValue: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', open: boolean): void
  (e: 'submit', payload: ExportCreateInput): void
}>()

const selectedType = ref<ExportType>('rgpd_full')
const submitting = ref(false)

const TYPE_OPTIONS: ReadonlyArray<{ value: ExportType; label: string; format: ExportFormat }> = [
  { value: 'rgpd_full', label: 'Export RGPD complet (JSON)', format: 'json' },
]

const formatForType = computed<ExportFormat>(() => {
  const found = TYPE_OPTIONS.find((opt) => opt.value === selectedType.value)
  return found ? found.format : 'json'
})

function close() {
  emit('update:modelValue', false)
}

function submit() {
  if (submitting.value) return
  submitting.value = true
  emit('submit', { type: selectedType.value, format: formatForType.value })
  submitting.value = false
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <section
        v-if="props.modelValue"
        role="dialog"
        aria-label="Nouvel export"
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-5 shadow-2xl"
        data-testid="new-export-sheet"
      >
        <header class="mb-3 flex items-start justify-between gap-3">
          <h2 class="text-base font-semibold text-gray-900">Nouvel export</h2>
          <button class="text-gray-400" aria-label="Fermer" @click="close">×</button>
        </header>
        <form class="space-y-3" @submit.prevent="submit">
          <fieldset>
            <legend class="block text-sm text-gray-700">
              Choisir un type d'export
            </legend>
            <div class="mt-2 space-y-2">
              <label
                v-for="opt in TYPE_OPTIONS"
                :key="opt.value"
                class="flex cursor-pointer items-start gap-2 rounded border border-gray-200 p-2 text-sm hover:bg-gray-50"
              >
                <input
                  v-model="selectedType"
                  type="radio"
                  :value="opt.value"
                  class="mt-1"
                  :data-testid="`new-export-type-${opt.value}`"
                />
                <span>{{ opt.label }}</span>
              </label>
            </div>
            <p class="mt-2 text-xs text-gray-500">
              Format : <span class="uppercase">{{ formatForType }}</span>. Les
              exports volumineux (&gt; 100 Mo) sont livrés par e-mail.
            </p>
          </fieldset>
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
              :disabled="submitting"
              class="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              data-testid="new-export-submit"
            >
              Lancer la génération
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
