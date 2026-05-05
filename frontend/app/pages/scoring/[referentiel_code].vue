<script setup lang="ts">
// F46 T032 [US1] — Page scoring d'un référentiel précis (squelette US1).
// Drilldown, historique, comparaison et snapshot sont ajoutés dans les phases suivantes.
import { computed, onMounted, ref, watch } from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import ScoreOverview from "~/components/scoring/ScoreOverview.vue"
import EmptyNoCalculation from "~/components/scoring/EmptyNoCalculation.vue"
import ReferentielTabs from "~/components/scoring/ReferentielTabs.vue"
import CompareButton from "~/components/scoring/CompareButton.vue"
import PillarAccordion from "~/components/scoring/PillarAccordion.vue"
import IndicateurDrawer from "~/components/scoring/IndicateurDrawer.vue"
import MissingIndicatorsList from "~/components/scoring/MissingIndicatorsList.vue"
import RecalcButton from "~/components/scoring/RecalcButton.vue"
import HistoryChart from "~/components/scoring/HistoryChart.vue"
import SnapshotToggle from "~/components/scoring/SnapshotToggle.vue"
import ExportPdfButton from "~/components/scoring/ExportPdfButton.vue"
import { useIndicateurEdit } from "~/composables/useIndicateurEdit"
import type { PillarRowVM } from "~/types/scoring"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Scoring ESG" }],
  title: "Scoring ESG",
})

const route = useRoute()
const router = useRouter()
const store = useScoringStore()
const entreprise = useEntrepriseStore()
const toast = useToast()
const { t } = useT()
const indicateurEdit = useIndicateurEdit()

const refCode = computed<string>(() => String(route.params.referentiel_code))

const ready = ref<boolean>(false)
const recomputing = ref<boolean>(false)
const openedIndicateur = ref<PillarRowVM | null>(null)
const drawerOpen = ref<boolean>(false)

const summary = computed(() => store.summariesByRef[refCode.value] ?? null)
const hasSummary = computed<boolean>(() => summary.value !== null)
const isSnapshot = computed<boolean>(() => store.isSnapshot)
const loading = computed<boolean>(
  () => store.loadingByRef[refCode.value] === "loading",
)
const availableCodes = computed<string[]>(() =>
  Object.keys(store.summariesByRef),
)
const tabsDisabled = computed<boolean>(
  () => isSnapshot.value || recomputing.value,
)

async function onSelectRef(code: string): Promise<void> {
  if (code === refCode.value) return
  await router.push(`/scoring/${code}`)
}

async function ensureLoaded(): Promise<void> {
  try {
    if (!entreprise.data) {
      await entreprise.loadAll()
    }
    const id = entreprise.data?.id
    if (!id) return
    store.setEntity("entreprise", id)
    if (Object.keys(store.summariesByRef).length === 0) {
      await store.loadSummaries()
    }
    const available = Object.keys(store.summariesByRef)
    if (available.length > 0 && !store.summariesByRef[refCode.value]) {
      toast.push({
        severity: "warning",
        message: t("scoring.errors.unknownReferentiel"),
        duration: 4000,
      })
      await router.replace("/scoring")
      return
    }
    await store.setCurrentReferentiel(refCode.value)
    // US7 T081 — assure l'historique chargé (idempotent grâce au cache TTL).
    await store.loadHistory(refCode.value, 12).catch(() => {
      /* erreur silencieuse — toast géré par useScoringHistory si visible */
    })
  } catch {
    toast.push({
      severity: "error",
      message: t("scoring.errors.loadFailed"),
      duration: 4000,
    })
  } finally {
    ready.value = true
  }
}

onMounted(() => {
  void ensureLoaded()
})

watch(refCode, () => {
  ready.value = false
  void ensureLoaded()
})

function onOpenIndicateur(row: PillarRowVM): void {
  openedIndicateur.value = row
  drawerOpen.value = true
}

function onCloseDrawer(): void {
  drawerOpen.value = false
}

async function onEditIndicateur(row: PillarRowVM): Promise<void> {
  await indicateurEdit.openFor(row, refCode.value)
  // Le drawer reste ouvert ; le sheet superpose. Sera fermé après submit.
}

async function onCompleteMissing(indicateurCode: string): Promise<void> {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("open_chat_for_indicateur", {
        detail: {
          indicateur_code: indicateurCode,
          referentiel_code: refCode.value,
          source: "scoring_page",
        },
      }),
    )
  }
}

function onSnapshotEnter(calcId: string): void {
  void store.enterSnapshot(calcId)
}

function onSnapshotExit(): void {
  store.exitSnapshot()
}

async function onStart(): Promise<void> {
  if (recomputing.value) return
  if (!entreprise.data?.id) return
  recomputing.value = true
  try {
    await store.recompute(refCode.value)
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : "unknown"
    toast.push({
      severity: "error",
      message: t("scoring.errors.recomputeFailed", { reason }),
      duration: 5000,
    })
  } finally {
    recomputing.value = false
  }
}
</script>

<template>
  <section
    class="scoring-page"
    data-testid="scoring-referentiel-page"
    :data-referentiel="refCode"
    :aria-busy="!ready"
  >
    <header class="scoring-page__header">
      <h1 class="scoring-page__title">{{ t("scoring.pageTitle") }}</h1>
      <span class="scoring-page__ref" data-testid="scoring-current-ref">{{ refCode }}</span>
    </header>

    <ReferentielTabs
      v-if="availableCodes.length > 0"
      :available-codes="availableCodes"
      :current-code="refCode"
      :disabled="tabsDisabled"
      @select="onSelectRef"
    />

    <EmptyNoCalculation
      v-if="ready && !hasSummary"
      :referentiel-code="refCode"
      :loading="recomputing"
      @start="onStart"
    />

    <template v-else>
      <ScoreOverview
        :summary="summary"
        :loading="loading"
        :is-snapshot="isSnapshot"
      >
        <template #extra>
          <RecalcButton :referentiel-code="refCode" :disabled="isSnapshot" />
          <CompareButton :disabled="isSnapshot" />
          <ExportPdfButton
            :referentiel-code="refCode"
            :frozen-calculation-id="store.snapshot.frozenCalculationId"
          />
        </template>
      </ScoreOverview>

      <SnapshotToggle
        :entries="store.currentHistory"
        :active="store.snapshot.active"
        :frozen-calculation-id="store.snapshot.frozenCalculationId"
        @enter="onSnapshotEnter"
        @exit="onSnapshotExit"
      />

      <MissingIndicatorsList
        v-if="store.currentDetail"
        :missing="store.currentDetail.indicateursManquants"
        :referentiel-code="refCode"
        @complete="onCompleteMissing"
      />

      <PillarAccordion
        :buckets="store.pillarsBuckets"
        :disable-edit="isSnapshot"
        @open-indicateur="onOpenIndicateur"
      />

      <HistoryChart
        v-if="store.currentHistory.length > 0"
        :entries="store.currentHistory"
        :loading="loading"
      />

      <IndicateurDrawer
        :row="openedIndicateur"
        :referentiel-code="refCode"
        :open="drawerOpen"
        :disable-edit="isSnapshot"
        @close="onCloseDrawer"
        @edit="onEditIndicateur"
      />
    </template>
  </section>
</template>

<style scoped>
.scoring-page {
  padding: var(--space-6, 1.5rem);
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 1rem);
}
.scoring-page__header {
  display: flex;
  align-items: baseline;
  gap: var(--space-3, 0.75rem);
}
.scoring-page__title {
  font-size: var(--font-size-2xl, 1.5rem);
  font-weight: 700;
  margin: 0;
}
.scoring-page__ref {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  padding: 2px 8px;
  background: var(--color-neutral-100, #f5f5f5);
  border-radius: var(--radius-sm);
}
</style>
