<!--
  F50 T038 — OcrSummarySheet (réutilise F39 ShowSummaryCard).
  Bottom sheet d'édition + validation des champs extraits par OCR.
  Bouton "Répondre librement" (P10) obligatoire.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDocumentsStore } from '~/stores/documents'
import { documentsApi } from '~/services/api/documents'
import { isLowConfidence } from '~/utils/ocrStatusUi'
import type {
  DocumentDetail,
  ExtractedFieldValue,
  ValidateExtractionFieldIn,
} from '~/types/documents'

interface Props {
  open: boolean
  docId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'free-response'): void
}>()

const store = useDocumentsStore()
const doc = ref<DocumentDetail | null>(null)
const editedValues = ref<Record<string, ExtractedFieldValue>>({})
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

const isAlreadyValidated = computed(
  () => Boolean(doc.value?.extraction_validated_at),
)

watch(
  () => [props.open, props.docId],
  async ([open]) => {
    if (!open) return
    errorMessage.value = null
    try {
      const fresh = await documentsApi.getDocument(props.docId)
      doc.value = fresh
      editedValues.value = Object.fromEntries(
        (fresh.extraction_payload?.fields ?? []).map((f) => [f.key, f.value]),
      )
    } catch (e) {
      errorMessage.value = (e as Error).message ?? 'load_failed'
    }
  },
  { immediate: true },
)

const fields = computed(() => doc.value?.extraction_payload?.fields ?? [])

function setValue(key: string, value: string): void {
  editedValues.value = { ...editedValues.value, [key]: value }
}

function valueAsString(v: ExtractedFieldValue): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'object' && 'amount' in v) return String(v.amount)
  return String(v)
}

async function onValidate(): Promise<void> {
  if (!doc.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    const payloadFields: ValidateExtractionFieldIn[] = fields.value.map((f) => ({
      key: f.key,
      value: editedValues.value[f.key] ?? f.value,
    }))
    await store.validateExtraction(doc.value.id, {
      fields: payloadFields,
      propagate_to: doc.value.entreprise_id
        ? [{ entity: 'entreprise', id: doc.value.entreprise_id }]
        : [],
    })
    emit('close')
  } catch (e) {
    errorMessage.value = (e as Error).message ?? 'validate_failed'
  } finally {
    submitting.value = false
  }
}

async function onRelaunch(): Promise<void> {
  if (!doc.value) return
  if (
    isAlreadyValidated.value &&
    !window.confirm(
      'Ce document est déjà validé. Relancer l\'extraction invalidera la validation. Continuer ?',
    )
  ) {
    return
  }
  await store.relaunchOcr(doc.value.id, {
    invalidateValidation: isAlreadyValidated.value,
  })
  emit('close')
}
</script>

<template>
  <transition name="sheet">
    <div
      v-if="open"
      class="fixed inset-0 z-40 flex items-end justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label="Fiche d'extraction OCR"
    >
      <div
        class="w-full max-w-2xl rounded-t-3xl bg-white shadow-xl sm:rounded-3xl"
      >
        <header class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 class="text-lg font-semibold text-gray-900">
            Vérifier les données extraites
          </h2>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              @click="emit('free-response')"
            >
              Répondre librement
            </button>
            <button
              type="button"
              class="rounded-lg p-1 text-gray-400 hover:text-gray-600"
              aria-label="Fermer"
              @click="emit('close')"
            >
              ✕
            </button>
          </div>
        </header>

        <div class="max-h-[70vh] overflow-y-auto p-6">
          <p
            v-if="errorMessage"
            role="alert"
            class="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {{ errorMessage }}
          </p>

          <p
            v-if="isAlreadyValidated"
            class="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
          >
            Document déjà validé le
            {{ new Date(doc!.extraction_validated_at!).toLocaleString('fr-FR') }}.
            Vous pouvez relancer l'extraction pour obtenir une nouvelle proposition.
          </p>

          <div v-if="fields.length === 0" class="text-sm text-gray-500">
            Aucun champ extrait pour le moment.
          </div>

          <ul v-else class="space-y-4">
            <li
              v-for="f in fields"
              :key="f.key"
              class="rounded-xl border border-gray-200 p-3"
            >
              <label class="flex items-center justify-between text-sm font-medium text-gray-900">
                <span>{{ f.label ?? f.key }}</span>
                <span
                  class="rounded-full px-2 py-0.5 text-xs"
                  :class="isLowConfidence(f.confidence)
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'"
                >
                  Confiance {{ Math.round(f.confidence * 100) }}%
                  <span v-if="isLowConfidence(f.confidence)"> · faible</span>
                </span>
              </label>
              <input
                type="text"
                class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                :value="valueAsString(editedValues[f.key] ?? f.value)"
                @input="setValue(f.key, ($event.target as HTMLInputElement).value)"
              >
            </li>
          </ul>
        </div>

        <footer class="flex flex-wrap justify-end gap-2 border-t border-gray-200 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50"
            @click="onRelaunch"
          >
            Relancer extraction
          </button>
          <button
            type="button"
            class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="submitting || isAlreadyValidated"
            @click="onValidate"
          >
            {{ submitting ? 'Validation…' : 'Valider' }}
          </button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
</style>
