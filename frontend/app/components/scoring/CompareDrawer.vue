<script setup lang="ts">
// F46 T042 [US2] — Drawer de comparaison N référentiels côte à côte.
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §CompareDrawer.
import { computed, ref, watch } from "vue"
import UiModal from "~/components/ui/UiModal.vue"
import VizBarChart from "~/components/viz/VizBarChart.vue"
import { useT } from "~/composables/useT"
import { useToast } from "~/composables/useToast"
import { PILLAR_LABELS_FR } from "~/lib/mapIndicateursByPillar"
import { SCORING_COMPARE_MAX } from "~/composables/useScoringCompare"
import type { PillarCode, ScoreSummaryVM } from "~/types/scoring"

interface Props {
  availableSummaries: ScoreSummaryVM[]
  defaultSelected?: string[]
  open?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  defaultSelected: () => [],
  open: false,
})

const emit = defineEmits<{
  (e: "close"): void
}>()

const { t } = useT()
const toast = useToast()

const selectedRefs = ref<string[]>([...props.defaultSelected])

watch(
  () => props.defaultSelected,
  (next) => {
    selectedRefs.value = [...next]
  },
  { deep: true },
)

function isSelected(code: string): boolean {
  return selectedRefs.value.includes(code)
}

function onToggle(code: string, checked: boolean): void {
  if (checked) {
    if (selectedRefs.value.includes(code)) return
    if (selectedRefs.value.length >= SCORING_COMPARE_MAX) {
      toast.push({
        severity: "warning",
        message: t("scoring.errors.tooManyCompared"),
        duration: 4000,
      })
      return
    }
    selectedRefs.value = [...selectedRefs.value, code]
  } else {
    selectedRefs.value = selectedRefs.value.filter((c) => c !== code)
  }
}

const dataset = computed(() => {
  const series = props.availableSummaries.filter((s) =>
    selectedRefs.value.includes(s.referentielCode),
  )
  const pillars: PillarCode[] = []
  const seen = new Set<PillarCode>()
  for (const s of series) {
    for (const p of Object.keys(s.scoresByPillar)) {
      if (!seen.has(p)) {
        seen.add(p)
        pillars.push(p)
      }
    }
  }
  return { series, pillars }
})

const barSeries = computed(() => ({
  labels: dataset.value.pillars.map((p) => PILLAR_LABELS_FR[p] ?? p),
  datasets: dataset.value.series.map((s) => ({
    label: s.referentielCode,
    data: dataset.value.pillars.map((p) => s.scoresByPillar[p] ?? 0),
  })),
}))

function onClose(): void {
  emit("close")
}
</script>

<template>
  <UiModal :model-value="open" size="xl" @close="onClose">
    <template #header>
      <h2 class="cd__title">{{ t("scoring.compare.title") }}</h2>
    </template>

    <div class="cd" data-testid="compare-drawer">
      <p class="cd__hint">{{ t("scoring.compare.selectHint") }}</p>

      <fieldset class="cd__list">
        <legend class="cd__legend-label">{{ t("scoring.tabs.label") }}</legend>
        <label
          v-for="s in availableSummaries"
          :key="s.referentielCode"
          class="cd__item"
        >
          <input
            type="checkbox"
            :value="s.referentielCode"
            :checked="isSelected(s.referentielCode)"
            @change="
              (e) => onToggle(s.referentielCode, (e.target as HTMLInputElement).checked)
            "
          />
          <span class="cd__item-code">{{ s.referentielCode }}</span>
          <span class="cd__item-version">v.{{ s.referentielVersion }}</span>
        </label>
      </fieldset>

      <div class="cd__chart" v-if="dataset.series.length > 0">
        <VizBarChart
          :series="barSeries"
          :title="t('scoring.compare.title')"
          size="md"
        />
      </div>

      <ul class="cd__legend" data-testid="compare-drawer-legend">
        <li v-for="s in dataset.series" :key="s.referentielCode">
          <strong>{{ s.referentielCode }}</strong>
          <span>{{ t("scoring.compare.legendVersion", { version: s.referentielVersion }) }}</span>
        </li>
      </ul>
    </div>

    <template #footer>
      <button
        type="button"
        class="cd__close"
        data-testid="compare-drawer-close"
        @click="onClose"
      >
        {{ t("scoring.buttons.close") }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.cd { display: flex; flex-direction: column; gap: var(--space-3, 0.75rem); min-width: min(720px, 90vw); }
.cd__title { margin: 0; font-size: var(--font-size-lg, 1.125rem); font-weight: 600; }
.cd__hint { color: var(--color-text-muted, #6b7280); font-size: var(--font-size-sm, 0.875rem); margin: 0; }
.cd__list { border: 0; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: var(--space-2, 0.5rem); }
.cd__legend-label { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: var(--space-1, 0.25rem); }
.cd__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  padding: var(--space-1, 0.25rem) var(--space-2, 0.5rem);
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: var(--font-size-sm, 0.875rem);
}
.cd__item-version { color: var(--color-text-muted, #6b7280); font-size: var(--font-size-xs, 0.75rem); }
.cd__chart { min-height: 16rem; }
.cd__legend { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: var(--space-3, 0.75rem); font-size: var(--font-size-sm); }
.cd__legend li { display: inline-flex; gap: var(--space-1, 0.25rem); align-items: baseline; }
.cd__legend strong { font-weight: 600; }
.cd__close {
  font-family: inherit;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  background: var(--color-surface, #fff);
  cursor: pointer;
}
</style>
