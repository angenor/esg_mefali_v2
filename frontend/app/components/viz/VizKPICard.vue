<!-- F40 T018-T019 — VizKPICard : valeur tabular-nums + delta + source pin. -->
<script setup lang="ts">
import { computed } from 'vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import type { KPICardProps } from '~/types/viz/chart'

const props = withDefaults(defineProps<KPICardProps>(), {
  size: 'md',
  loading: false,
  empty: false,
})

const sizeClass = computed(() => `viz-kpi--${props.size}`)

const deltaState = computed<'up' | 'down' | 'flat'>(() => {
  if (props.delta === undefined || props.delta === null) return 'flat'
  if (props.delta > 0) return 'up'
  if (props.delta < 0) return 'down'
  return 'flat'
})

const deltaSymbol = computed(() => ({ up: '↑', down: '↓', flat: '=' })[deltaState.value])
const deltaSign = computed(() => {
  if (props.delta === undefined || props.delta === null) return ''
  if (props.delta > 0) return '+'
  if (props.delta < 0) return ''
  return ''
})

const ariaLabelComputed = computed<string>(() => {
  if (props.ariaLabel) return props.ariaLabel
  const parts = [props.label, `valeur ${props.value}${props.unit ?? ''}`]
  if (props.delta !== undefined && props.delta !== null) {
    parts.push(`variation ${deltaSign.value}${props.delta}${props.deltaUnit ?? ''}`)
  }
  return parts.join(', ')
})
</script>

<template>
  <article
    class="viz-kpi"
    :class="sizeClass"
    role="figure"
    :aria-label="ariaLabelComputed"
  >
    <header class="viz-kpi__head">
      <span class="viz-kpi__label">{{ props.label }}</span>
      <VizSourcePin v-if="props.source_id" :source_id="props.source_id" />
    </header>

    <VizLoadingState v-if="props.loading" height="3rem" :aria-label="`Chargement ${props.label}`" />
    <VizEmptyState v-else-if="props.empty" height="3rem" />
    <template v-else>
      <p class="viz-kpi__value">
        <span class="viz-kpi__number">{{ props.value }}</span>
        <span v-if="props.unit" class="viz-kpi__unit">{{ props.unit }}</span>
      </p>
      <p
        v-if="props.delta !== undefined && props.delta !== null"
        class="viz-kpi__delta"
        :class="`viz-kpi__delta--${deltaState}`"
      >
        <span aria-hidden="true">{{ deltaSymbol }}</span>
        <span>{{ deltaSign }}{{ props.delta }}{{ props.deltaUnit ?? '' }}</span>
      </p>
    </template>

    <p v-if="props.longDescription" class="sr-only">{{ props.longDescription }}</p>
  </article>
</template>

<style scoped>
.viz-kpi {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.875rem 1rem;
  background: var(--color-neutral-50, #ffffff);
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.75rem;
}
.viz-kpi--sm { padding: 0.5rem 0.75rem; }
.viz-kpi--lg { padding: 1.25rem 1.5rem; }

.viz-kpi__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.viz-kpi__label {
  color: var(--color-neutral-600, #525252);
  font-size: 0.85rem;
  font-weight: 500;
}
.viz-kpi__value {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
  margin: 0;
}
.viz-kpi__number {
  font-variant-numeric: tabular-nums;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--color-neutral-900, #171717);
}
.viz-kpi--sm .viz-kpi__number { font-size: 1.25rem; }
.viz-kpi--lg .viz-kpi__number { font-size: 2.25rem; }
.viz-kpi__unit {
  font-size: 0.85rem;
  color: var(--color-neutral-500, #737373);
}
.viz-kpi__delta {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin: 0;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}
.viz-kpi__delta--up { color: var(--color-success-700, #15803d); }
.viz-kpi__delta--down { color: var(--color-danger-700, #b91c1c); }
.viz-kpi__delta--flat { color: var(--color-neutral-500, #737373); }
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
