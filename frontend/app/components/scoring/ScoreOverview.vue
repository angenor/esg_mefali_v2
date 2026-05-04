<script setup lang="ts">
// F46 T030 [US1] — Vue d'ensemble du scoring (score global + radar/bar + sources).
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §ScoreOverview.
import { computed } from "vue"
import VizRadarChart from "~/components/viz/VizRadarChart.vue"
import VizBarChart from "~/components/viz/VizBarChart.vue"
import UiSkeleton from "~/components/ui/UiSkeleton.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import { useT } from "~/composables/useT"
import { PILLAR_LABELS_FR } from "~/lib/mapIndicateursByPillar"
import type { PillarCode, ScoreSummaryVM } from "~/types/scoring"

interface Props {
  summary: ScoreSummaryVM | null
  loading?: boolean
  isSnapshot?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  isSnapshot: false,
})

const { t } = useT()

interface PillarEntry {
  code: PillarCode
  label: string
  score: number | null
}

const pillars = computed<PillarEntry[]>(() => {
  const map = props.summary?.scoresByPillar ?? {}
  return Object.entries(map)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([code, score]) => ({
      code,
      label: PILLAR_LABELS_FR[code] ?? code,
      score: score as number | null,
    }))
})

const pillarsCount = computed<number>(() => pillars.value.length)

const useBarChart = computed<boolean>(() => pillarsCount.value > 6)

const radarSeries = computed(() => ({
  axes: pillars.value.map((p) => p.label),
  datasets: [
    {
      label: t("scoring.overview.scoreGlobal"),
      data: pillars.value.map((p) => p.score ?? 0),
    },
  ],
}))

const barSeries = computed(() => ({
  labels: pillars.value.map((p) => p.label),
  datasets: [
    {
      label: t("scoring.overview.scoreGlobal"),
      data: pillars.value.map((p) => p.score ?? 0),
    },
  ],
}))

const scoreText = computed<string>(() => {
  const v = props.summary?.scoreGlobal
  if (v === null || v === undefined) return "—"
  return v.toFixed(0)
})

const coverageText = computed<string>(() => {
  const r = props.summary?.coverageRatio
  if (r === null || r === undefined) return "—"
  const percent = Math.round(r * 100)
  return t("scoring.overview.coverage", { percent })
})

const dateText = computed<string>(() => {
  const iso = props.summary?.computedAt
  if (!iso) return "—"
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const fmt = new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(d)
    return t("scoring.overview.computedAt", { date: fmt })
  } catch {
    return iso
  }
})

const versionText = computed<string>(() => {
  const v = props.summary?.referentielVersion
  if (v === undefined || v === null) return ""
  return t("scoring.overview.version", { version: v })
})

const snapshotBannerText = computed<string>(() => {
  const iso = props.summary?.computedAt
  const version = props.summary?.referentielVersion ?? 0
  if (!iso) return ""
  const d = new Date(iso)
  const fmt = Number.isNaN(d.getTime())
    ? iso
    : new Intl.DateTimeFormat("fr-FR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      }).format(d)
  return t("scoring.snapshot.title", { date: fmt, version })
})
</script>

<template>
  <section
    class="score-overview"
    :aria-busy="loading || !summary"
    data-testid="score-overview"
  >
    <UiSkeleton v-if="!summary" data-testid="score-overview-skeleton" />

    <template v-else>
      <div
        v-if="isSnapshot"
        class="score-overview__snapshot-banner"
        role="status"
        data-testid="score-overview-snapshot-banner"
      >
        {{ snapshotBannerText }}
      </div>

      <header class="score-overview__header">
        <div class="score-overview__title">
          <h2 class="score-overview__heading">
            {{ t("scoring.overview.scoreGlobal") }}
          </h2>
          <span
            class="score-overview__score tabular-nums"
            data-testid="score-overview-score"
          >
            {{ scoreText }}
          </span>
          <UiBadge
            v-if="versionText"
            severity="info"
            variant="subtle"
            data-testid="score-overview-version"
          >
            {{ versionText }}
          </UiBadge>
        </div>
        <div class="score-overview__meta">
          <span data-testid="score-overview-coverage">{{ coverageText }}</span>
          <span data-testid="score-overview-date">{{ dateText }}</span>
        </div>
        <div v-if="$slots.extra" class="score-overview__extra">
          <slot name="extra" />
        </div>
      </header>

      <div class="score-overview__chart">
        <VizBarChart
          v-if="useBarChart"
          data-testid="score-overview-bar"
          :series="barSeries"
          :title="t('scoring.overview.scoreGlobal')"
          size="md"
        />
        <VizRadarChart
          v-else
          data-testid="score-overview-radar"
          :series="radarSeries"
          :title="t('scoring.overview.scoreGlobal')"
          size="md"
        />
      </div>

      <table
        class="sr-only"
        data-testid="score-overview-sr-table"
        aria-label="Détail des scores par pilier"
      >
        <caption>{{ t("scoring.overview.scoreGlobal") }}</caption>
        <thead>
          <tr>
            <th scope="col">Pilier</th>
            <th scope="col">Score</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pillars" :key="p.code">
            <th scope="row">{{ p.label }}</th>
            <td>{{ p.score ?? "—" }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<style scoped>
.score-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 1rem);
  padding: var(--space-4, 1rem);
  background: var(--color-surface, #fff);
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--color-neutral-200, #e5e5e5);
}
.score-overview__snapshot-banner {
  background: var(--color-warning-50, #fffbeb);
  color: var(--color-warning-800, #92400e);
  border: 1px solid var(--color-warning-200, #fde68a);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  font-weight: 500;
}
.score-overview__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}
.score-overview__title {
  display: flex;
  align-items: baseline;
  gap: var(--space-3, 0.75rem);
  flex-wrap: wrap;
}
.score-overview__heading {
  margin: 0;
  font-size: var(--font-size-md, 1rem);
  font-weight: 600;
  color: var(--color-text-muted, #6b7280);
}
.score-overview__score {
  font-size: var(--font-size-3xl, 2.5rem);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-text, #111827);
}
.tabular-nums { font-variant-numeric: tabular-nums; }
.score-overview__meta {
  display: flex;
  gap: var(--space-4, 1rem);
  font-size: var(--font-size-sm, 0.875rem);
  color: var(--color-text-muted, #6b7280);
  flex-wrap: wrap;
}
.score-overview__extra {
  display: flex;
  gap: var(--space-2, 0.5rem);
  flex-wrap: wrap;
}
.score-overview__chart { min-height: 16rem; }
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
