<script setup lang="ts">
// F49 T029/T030/T031 — Modale de génération d'un rapport avec progression SSE.
import { computed, ref, watch } from "vue"
import { useReportsStore } from "~/stores/reports"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useReportGenerationStream } from "~/composables/useReportGenerationStream"
import { reportsApi } from "~/services/api/reports"
import type { Rapport, RapportType } from "~/types/reports"

interface Props {
  open: boolean
  prefill?: Partial<Rapport> | null
}
const props = withDefaults(defineProps<Props>(), { prefill: null })
const emit = defineEmits<{ (e: "close"): void }>()

const store = useReportsStore()
const ent = useEntrepriseStore()

const REPORT_TYPES: ReadonlyArray<{ code: RapportType; label: string }> = [
  { code: "conformite", label: "Conformité ESG" },
  { code: "carbone", label: "Bilan carbone" },
  { code: "candidature", label: "Dossier candidature" },
] as const

const REFERENTIELS: ReadonlyArray<{ code: string; label: string }> = [
  { code: "ESG_MEFALI", label: "ESG Mefali (par défaut)" },
  { code: "BOAD", label: "BOAD" },
  { code: "BCEAO", label: "BCEAO" },
] as const

const type = ref<RapportType>("conformite")
const referentielCode = ref<string>("ESG_MEFALI")
const periodFrom = ref<string>("")
const periodTo = ref<string>("")
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const generationId = ref<string | null>(null)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      type.value = (props.prefill?.type as RapportType) ?? "conformite"
      referentielCode.value =
        props.prefill?.referentiel_id ??
        props.prefill?.referentiels?.[0] ??
        "ESG_MEFALI"
      periodFrom.value = props.prefill?.period_from ?? defaultFromDate()
      periodTo.value = props.prefill?.period_to ?? defaultToDate()
      submitting.value = false
      errorMessage.value = null
      generationId.value = null
    }
  },
  { immediate: true },
)

function defaultFromDate(): string {
  const d = new Date()
  return `${d.getFullYear() - 1}-01-01`
}
function defaultToDate(): string {
  const d = new Date()
  return `${d.getFullYear() - 1}-12-31`
}

const valid = computed(() => {
  return (
    !!type.value &&
    !!referentielCode.value &&
    !!periodFrom.value &&
    !!periodTo.value &&
    periodFrom.value <= periodTo.value
  )
})

const currentState = computed(() =>
  generationId.value ? store.pending[generationId.value] : null,
)

const downloadHref = computed(() => {
  const s = currentState.value
  if (!s || s.phase !== "ready" || !s.rapport_id) return null
  return reportsApi.buildDownloadUrl(s.rapport_id)
})

async function submit() {
  if (!valid.value || submitting.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    const entityId = ent.data?.id ?? props.prefill?.entity_id
    if (!entityId) {
      throw new Error(
        "Profil entreprise indisponible : impossible de générer le rapport.",
      )
    }
    const id = await store.generate({
      type: type.value,
      referentiel_id: referentielCode.value,
      period_from: periodFrom.value,
      period_to: periodTo.value,
      entity_type: "entreprise",
      entity_id: entityId,
      referentiels: [referentielCode.value],
      language: "fr",
    })
    generationId.value = id
    // Cas backend asynchrone : si la phase n'est pas déjà `ready`, on
    // ouvre le SSE. Cas backend synchrone (état actuel F24) : `generate`
    // a déjà transitionné en `ready`, le composable est un no-op.
    const cur = store.pending[id]
    if (cur && cur.phase !== "ready") {
      useReportGenerationStream(id)
    } else {
      // Rafraîchit la liste pour refléter la nouvelle entrée
      await store.fetchAll()
    }
  } catch (err: unknown) {
    errorMessage.value =
      err instanceof Error
        ? err.message
        : "Une erreur est survenue lors de la génération."
  } finally {
    submitting.value = false
  }
}

function close() {
  if (generationId.value) {
    // Cleanup local de l'entrée pending pour ne pas la conserver indéfiniment
    store.cancelStream(generationId.value)
  }
  emit("close")
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generate-modal-title"
        data-testid="generate-modal"
        @click.self="close"
      >
        <div
          class="w-full max-w-lg rounded-lg bg-white shadow-xl"
          @click.stop
        >
          <header class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <h2 id="generate-modal-title" class="text-base font-semibold">
              Générer un nouveau rapport
            </h2>
            <button
              type="button"
              class="rounded p-1 text-gray-500 hover:bg-gray-100"
              aria-label="Fermer"
              @click="close"
            >
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <form
            v-if="!currentState || currentState.phase === 'pending'"
            class="space-y-4 p-4"
            @submit.prevent="submit"
          >
            <div>
              <label class="mb-1 block text-sm font-medium" for="gen-type">Type</label>
              <select
                id="gen-type"
                v-model="type"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                data-testid="select-type"
              >
                <option v-for="t in REPORT_TYPES" :key="t.code" :value="t.code">
                  {{ t.label }}
                </option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium" for="gen-ref">Référentiel</label>
              <select
                id="gen-ref"
                v-model="referentielCode"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                data-testid="select-ref"
              >
                <option v-for="r in REFERENTIELS" :key="r.code" :value="r.code">
                  {{ r.label }}
                </option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-sm font-medium" for="gen-from">
                  Période — début
                </label>
                <input
                  id="gen-from"
                  v-model="periodFrom"
                  type="date"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  data-testid="input-from"
                  required
                />
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium" for="gen-to">
                  Période — fin
                </label>
                <input
                  id="gen-to"
                  v-model="periodTo"
                  type="date"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  data-testid="input-to"
                  required
                />
              </div>
            </div>
            <p
              v-if="errorMessage"
              class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
              data-testid="error-msg"
            >
              {{ errorMessage }}
            </p>
            <footer class="flex justify-end gap-2 pt-2">
              <button
                type="button"
                class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                @click="close"
              >
                Annuler
              </button>
              <button
                type="submit"
                class="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!valid || submitting"
                data-testid="submit-btn"
              >
                {{ submitting ? "Envoi…" : "Lancer la génération" }}
              </button>
            </footer>
          </form>

          <div v-else class="space-y-4 p-4 text-sm" data-testid="progress-view">
            <p class="font-medium">
              <template v-if="currentState.phase === 'running'">
                Génération en cours…
              </template>
              <template v-else-if="currentState.phase === 'ready'">
                Rapport prêt ✓
              </template>
              <template v-else-if="currentState.phase === 'failed'">
                Échec de la génération
              </template>
            </p>
            <div
              class="h-2 w-full overflow-hidden rounded-full bg-gray-200"
              role="progressbar"
              :aria-valuenow="currentState.percent"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div
                class="h-full bg-brand-600 transition-all"
                :style="{ width: `${currentState.percent}%` }"
              />
            </div>
            <p v-if="currentState.step" class="text-xs text-gray-600">
              Étape : {{ currentState.step }}
            </p>
            <p
              v-if="currentState.error"
              class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-700"
              role="alert"
            >
              {{ currentState.error }}
            </p>
            <footer class="flex justify-end gap-2 pt-2">
              <a
                v-if="downloadHref"
                :href="downloadHref"
                target="_blank"
                rel="noopener"
                class="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                data-testid="download-btn"
              >
                Télécharger
              </a>
              <button
                type="button"
                class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                @click="close"
              >
                Fermer
              </button>
            </footer>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
