<script setup lang="ts">
// F47 T037 [US1] / T046 [US2] — Page /carbone (synthèse + drilldown).

import { computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import CarbonOverview from "~/components/carbone/CarbonOverview.vue"
import ScopeDonut from "~/components/carbone/ScopeDonut.vue"
import LowCoverageBanner from "~/components/carbone/LowCoverageBanner.vue"
import ScopeAccordion from "~/components/carbone/ScopeAccordion.vue"
import EditLineDrawer from "~/components/carbone/EditLineDrawer.vue"
import EvolutionLineChart from "~/components/carbone/EvolutionLineChart.vue"
import RecalcStrip from "~/components/carbone/RecalcStrip.vue"
import EmptyStateWizard from "~/components/carbone/EmptyStateWizard.vue"
import FactorReferentielSwitch from "~/components/carbone/FactorReferentielSwitch.vue"
import ExportPdfButton from "~/components/carbone/ExportPdfButton.vue"
import UiSelect from "~/components/ui/UiSelect.vue"
import { useCarbon } from "~/composables/useCarbon"
import { useT } from "~/composables/useT"
import type { Scope } from "~/types/carbon"

definePageMeta({ middleware: ["pme-only"] })

const { t } = useT()
const carbon = useCarbon()
const route = useRoute()
const router = useRouter()

// Sync ?year=YYYY <-> selectedYear
const initialYear = Number(route.query.year)
if (Number.isInteger(initialYear) && initialYear >= 2000 && initialYear <= 2100) {
  carbon.setSelectedYear(initialYear)
}

watch(
  () => carbon.selectedYear.value,
  (year) => {
    void router.replace({ query: { ...route.query, year: String(year) } })
    void carbon.refresh()
    // pré-charger N-1 pour delta
    // (la route n'écoute pas N-1 explicitement ; le store met en cache)
  },
)

const yearOptions = computed(() => {
  const y = carbon.selectedYear.value
  return [y - 2, y - 1, y, y + 1].map((v) => ({
    value: String(v),
    label: String(v),
  }))
})

const scopes: Scope[] = ["1", "2", "3"]

function onYearChange(value: string | number) {
  const year = Number(value)
  if (Number.isInteger(year)) carbon.setSelectedYear(year)
}

async function onRecompute(): Promise<void> {
  await carbon.recompute(carbon.selectedYear.value)
}

function onCoverageComplete() {
  // Hook futur : ouvrir drawer "ajouter un poste". Pour l'US1 MVP, on
  // se contente de scroller jusqu'au premier scope incomplet.
  if (typeof document !== "undefined") {
    const el = document.getElementById("carbon-scopes")
    el?.scrollIntoView({ behavior: "smooth", block: "start" })
  }
}
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 lg:px-8">
    <header class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold text-neutral-900">
          {{ t("carbon.pageTitle") }}
        </h1>
        <p class="text-neutral-600 mt-1">{{ t("carbon.subtitle") }}</p>
      </div>
      <div class="flex items-center gap-2">
        <label
          for="carbon-year-select"
          class="text-sm font-medium text-neutral-700"
        >
          {{ t("carbon.yearLabel") }}
        </label>
        <UiSelect
          id="carbon-year-select"
          :model-value="String(carbon.selectedYear.value)"
          :options="yearOptions"
          @update:model-value="onYearChange"
        />
      </div>
    </header>

    <div v-if="carbon.loadingFootprint.value && !carbon.currentFootprint.value">
      <div class="h-32 animate-pulse rounded-2xl bg-neutral-100" />
    </div>

    <EmptyStateWizard
      v-else-if="!carbon.currentFootprint.value"
      :year="carbon.selectedYear.value"
    />

    <template v-else>
      <RecalcStrip
        :year="carbon.selectedYear.value"
        :last-computed-at="carbon.currentFootprint.value?.computed_at ?? null"
        :loading="carbon.loadingRecompute.value"
        class="mb-4"
        @recompute="onRecompute"
      />

      <LowCoverageBanner
        :coverage="carbon.coverage.value"
        class="mb-4"
        @complete="onCoverageComplete"
      />

      <section
        class="mb-8 grid gap-4 lg:grid-cols-3"
        aria-label="Synthèse de l'empreinte carbone"
      >
        <CarbonOverview
          :footprint="carbon.currentFootprint.value"
          :previous-year-footprint="carbon.previousYearFootprint.value"
          :coverage="carbon.coverage.value"
          :loading="carbon.loadingFootprint.value"
        />
        <ScopeDonut
          :by-scope="carbon.currentFootprint.value?.by_scope_kgco2e"
          :loading="carbon.loadingFootprint.value"
        />
        <EvolutionLineChart />
      </section>

      <FactorReferentielSwitch class="mb-4" />

      <section id="carbon-scopes" class="grid gap-4">
        <ScopeAccordion
          v-for="scope in scopes"
          :key="scope"
          :scope="scope"
          :breakdown="carbon.groupedBreakdown.value?.[scope] ?? null"
          :year="carbon.selectedYear.value"
        />
      </section>

      <div class="mt-6 flex justify-end">
        <ExportPdfButton :year="carbon.selectedYear.value" />
      </div>

      <EditLineDrawer />
    </template>
  </main>
</template>
