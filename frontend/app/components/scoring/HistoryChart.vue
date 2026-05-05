<script setup lang="ts">
// F46 T079 [US7] — Graphique historique des scores (12 derniers calculs).
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §HistoryChart.
import { computed } from "vue"
import VizLineChart from "~/components/viz/VizLineChart.vue"
import { useT } from "~/composables/useT"
import type { ScoreHistoryEntryVM } from "~/types/scoring"

interface Props {
  entries: ScoreHistoryEntryVM[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const emit = defineEmits<{
  (e: "select", entry: ScoreHistoryEntryVM): void
}>()

const { t } = useT()

const isEmpty = computed<boolean>(() => props.entries.length === 0)

const sortedAsc = computed<ScoreHistoryEntryVM[]>(() =>
  [...props.entries].sort((a, b) => a.computedAt.localeCompare(b.computedAt)),
)

const series = computed(() => [
  {
    label: t("scoring.history.title"),
    points: sortedAsc.value.map((e) => ({
      x: e.computedAt,
      y: e.scoreGlobal ?? 0,
    })),
  },
])

function fmtDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function onSelectEntry(e: ScoreHistoryEntryVM): void {
  emit("select", e)
}
</script>

<template>
  <section
    class="history-chart"
    data-testid="history-chart"
    :aria-label="t('scoring.history.title')"
  >
    <header class="history-chart__header">
      <h2 class="history-chart__title">{{ t("scoring.history.title") }}</h2>
    </header>
    <p
      v-if="isEmpty && !loading"
      class="history-chart__empty"
      data-testid="history-chart-empty"
    >
      {{ t("scoring.empty.noHistory") }}
    </p>
    <VizLineChart
      v-else
      :series="series"
      :loading="loading"
      :empty="isEmpty"
      size="md"
      :title="t('scoring.history.title')"
      data-testid="history-chart-canvas"
    />
    <ul v-if="!isEmpty" class="history-chart__points sr-only">
      <li v-for="e in sortedAsc" :key="e.scoreCalculationId">
        <button
          type="button"
          @click="onSelectEntry(e)"
        >
          {{
            t("scoring.history.tooltipFormat", {
              date: fmtDate(e.computedAt),
              score: e.scoreGlobal ?? 0,
              version: e.referentielVersion,
            })
          }}
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.history-chart {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-4, 1rem);
}
.history-chart__header { margin-bottom: var(--space-3, 0.75rem); }
.history-chart__title {
  font-size: var(--font-size-lg, 1.125rem);
  font-weight: 600;
  margin: 0;
}
.history-chart__empty {
  color: var(--color-text-muted, #6b7280);
  font-size: var(--font-size-sm, 0.875rem);
  margin: 0;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
