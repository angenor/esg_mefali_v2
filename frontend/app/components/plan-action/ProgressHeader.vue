<script setup lang="ts">
// F45 T039 — En-tête de progression du plan d'action.
import { computed } from "vue"
import { useT } from "~/composables/useT"
import type { CompletionStats } from "~/types/actionPlan"

interface Props {
  stats: CompletionStats
  version: number
}

const props = defineProps<Props>()
const { t } = useT()

const percentLabel = computed(() =>
  props.stats.hasData ? t("planAction.progress.percent", { percent: props.stats.percent }) : "—",
)

const unitsLabel = computed(() =>
  t("planAction.progress.units", {
    done: props.stats.doneVisible,
    total: props.stats.totalVisible,
  }),
)

const ariaValue = computed(() => (props.stats.hasData ? props.stats.percent : 0))
</script>

<template>
  <header class="pa-progress" :data-empty="!stats.hasData || undefined">
    <div class="pa-progress__row">
      <h2 class="pa-progress__label">{{ t("planAction.progress.label") }}</h2>
      <span class="pa-progress__version">{{ t("planAction.version", { n: version }) }}</span>
    </div>
    <p class="pa-progress__units">{{ unitsLabel }}</p>
    <div
      class="pa-progress__bar"
      role="progressbar"
      :aria-valuenow="ariaValue"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuetext="percentLabel"
    >
      <div
        class="pa-progress__bar-fill"
        :style="{ width: stats.hasData ? `${stats.percent}%` : '0%' }"
      />
    </div>
    <p class="pa-progress__percent">{{ percentLabel }}</p>
  </header>
</template>

<style scoped>
.pa-progress {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-lg, 12px);
  background: var(--color-surface, white);
}
.pa-progress__row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-3);
}
.pa-progress__label {
  margin: 0;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
}
.pa-progress__version {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary, #6b7280);
}
.pa-progress__units {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary, #4b5563);
}
.pa-progress__bar {
  position: relative;
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: var(--color-surface-subtle, #f3f4f6);
  overflow: hidden;
}
.pa-progress__bar-fill {
  height: 100%;
  background: var(--color-primary-500, #3b82f6);
  transition: width 200ms ease-out;
}
.pa-progress__percent {
  margin: 0;
  align-self: flex-end;
  font-weight: var(--font-weight-medium);
}
</style>
