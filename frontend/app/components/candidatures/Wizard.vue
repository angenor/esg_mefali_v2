<script setup lang="ts">
// F51 T067 — Wizard parent : enchaîne les 5 étapes + autosave + soumission.
import { computed, ref, watch } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import { useWizardAutosave } from "~/composables/useWizardAutosave"
import { useWizardNavigation } from "~/composables/useWizardNavigation"
import WizardStepIndicator from "~/components/candidatures/WizardStepIndicator.vue"
import StepOffreProjet from "~/components/candidatures/StepOffreProjet.vue"
import StepDataSnapshot from "~/components/candidatures/StepDataSnapshot.vue"
import StepDocuments from "~/components/candidatures/StepDocuments.vue"
import StepReponsesLibres from "~/components/candidatures/StepReponsesLibres.vue"
import StepRecap from "~/components/candidatures/StepRecap.vue"
import SubmissionModal from "~/components/candidatures/SubmissionModal.vue"
import type { WizardStepKey } from "~/types/candidatures"

interface Props {
  candidatureId: string
}
const props = defineProps<Props>()

const store = useCandidaturesStore()
const detail = computed(() => store.detail)
const autosave = useWizardAutosave()

const nav = useWizardNavigation({
  initialStep: 1,
  validators: {
    1: () =>
      detail.value?.draft_snapshot_json?.step1?.offre_id &&
      detail.value?.draft_snapshot_json?.step1?.projet_id
        ? true
        : "Offre ou projet manquant.",
  },
  onChange: (step) => {
    if (!detail.value) return
    autosave.flushNow(props.candidatureId, {
      step_courant: step,
      expected_version: detail.value.version,
    }).catch(() => {
      /* géré dans le store */
    })
  },
})

watch(
  () => detail.value?.step_courant,
  (s) => {
    if (s && s !== nav.current.value) {
      void nav.goTo(s as WizardStepKey)
    }
  },
  { immediate: true },
)

function patchStep4(reponses: { question: string; reponse: string; asked_at: string }[]) {
  if (!detail.value) return
  autosave.schedule(props.candidatureId, {
    expected_version: detail.value.version,
    draft_snapshot_json: { step4: { reponses_libres: reponses } },
  })
}

const ackChecked = ref(false)
const submitOpen = ref(false)
const submitInFlight = ref(false)
const submitError = ref<string | null>(null)

function onAck(v: boolean): void {
  ackChecked.value = v
  if (!detail.value) return
  autosave.schedule(props.candidatureId, {
    expected_version: detail.value.version,
    draft_snapshot_json: {
      step5: {
        user_acknowledged_intangible: v,
        user_confirmed_at: v ? new Date().toISOString() : undefined,
      },
    },
  })
}

function openSubmit(): void {
  submitError.value = null
  submitOpen.value = true
}

async function confirmSubmit(expectedVersion: number): Promise<void> {
  submitInFlight.value = true
  submitError.value = null
  const ok = await store.submit(props.candidatureId, {
    confirmed: true as const,
    expected_version: expectedVersion,
    user_acknowledged_intangible: true as const,
  })
  submitInFlight.value = false
  if (ok) {
    submitOpen.value = false
    if (typeof window !== "undefined") {
      window.location.assign(`/candidatures/${props.candidatureId}`)
    }
  } else {
    submitError.value = store.error ?? "Erreur lors de la soumission."
  }
}
</script>

<template>
  <div v-if="detail" class="space-y-6">
    <WizardStepIndicator
      :current="nav.current.value"
      :progression-pct="detail.progression_pct"
      @go-to="(s) => nav.goTo(s)"
    />

    <p
      v-if="store.saveStatus !== 'idle'"
      class="rounded bg-gray-50 px-3 py-1.5 text-xs text-gray-600"
    >
      <span v-if="store.saveStatus === 'saving'">Enregistrement…</span>
      <span v-else-if="store.saveStatus === 'saved'" class="text-emerald-700"
        >Brouillon enregistré ✓</span
      >
      <span v-else-if="store.saveStatus === 'offline'" class="text-amber-700"
        >Hors ligne — vos modifications seront synchronisées au retour</span
      >
      <span v-else-if="store.saveStatus === 'error'" class="text-red-700"
        >Erreur : {{ store.saveError }}</span
      >
    </p>

    <p v-if="nav.error.value" class="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ nav.error.value }}
    </p>

    <div class="wizard-step-active">
      <StepOffreProjet v-if="nav.current.value === 1" />
      <StepDataSnapshot v-else-if="nav.current.value === 2" />
      <StepDocuments v-else-if="nav.current.value === 3" />
      <StepReponsesLibres
        v-else-if="nav.current.value === 4"
        @update="patchStep4"
      />
      <StepRecap
        v-else-if="nav.current.value === 5"
        @ack="onAck"
        @submit="openSubmit"
      />
    </div>

    <footer class="flex items-center justify-between border-t border-gray-200 pt-4">
      <button
        type="button"
        class="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-40"
        :disabled="nav.current.value === 1"
        @click="nav.goPrev"
      >
        ← Précédent
      </button>
      <button
        v-if="nav.current.value < 5"
        type="button"
        class="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-emerald-700"
        @click="nav.goNext"
      >
        Suivant →
      </button>
    </footer>

    <SubmissionModal
      :open="submitOpen"
      :expected-version="detail.version"
      :in-flight="submitInFlight"
      :error-message="submitError"
      @confirmed="confirmSubmit"
      @cancel="submitOpen = false"
    />
  </div>
  <p v-else class="text-sm text-gray-500">Chargement de la candidature…</p>
</template>
