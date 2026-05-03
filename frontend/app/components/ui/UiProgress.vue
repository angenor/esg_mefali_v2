<script setup lang="ts">
import { computed } from 'vue'
import type { UiSize } from '~/types/ui'

interface Props {
  modelValue?: number
  variant?: 'bar' | 'circular'
  indeterminate?: boolean
  size?: UiSize
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 0,
  variant: 'bar',
  indeterminate: false,
  size: 'md',
  ariaLabel: 'Progression',
})

const value = computed(() => Math.max(0, Math.min(100, props.modelValue ?? 0)))
</script>

<template>
  <div
    class="ui-progress"
    :data-variant="variant"
    :data-size="size"
    :data-indeterminate="indeterminate || undefined"
    role="progressbar"
    :aria-label="ariaLabel"
    :aria-valuemin="0"
    :aria-valuemax="100"
    :aria-valuenow="indeterminate ? undefined : value"
  >
    <span v-if="variant === 'bar'" class="ui-progress__track">
      <span
        class="ui-progress__fill"
        :style="indeterminate ? undefined : { width: `${value}%` }"
      />
    </span>
    <span v-else class="ui-progress__circle" :data-pct="value">
      <span class="ui-progress__circle-fill" />
    </span>
  </div>
</template>

<style scoped>
.ui-progress {
  display: block;
  font-family: var(--font-sans);
}
.ui-progress[data-variant='bar'] .ui-progress__track {
  display: block;
  width: 100%;
  height: 6px;
  background: var(--color-surface-muted);
  border-radius: 999px;
  overflow: hidden;
}
.ui-progress[data-variant='bar'] .ui-progress__fill {
  display: block;
  height: 100%;
  background: var(--color-brand-500);
  transition: width var(--duration-fast) var(--ease-out);
}
.ui-progress[data-indeterminate] .ui-progress__fill {
  width: 35%;
  animation: ui-progress-slide 1.4s ease-in-out infinite;
}
.ui-progress[data-variant='circular'] .ui-progress__circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid var(--color-surface-muted);
  border-top-color: var(--color-brand-500);
  display: inline-block;
  animation: ui-progress-rot 1s linear infinite;
}
@keyframes ui-progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(300%); }
}
@keyframes ui-progress-rot {
  to { transform: rotate(360deg); }
}
@media (prefers-reduced-motion: reduce) {
  .ui-progress__fill,
  .ui-progress__circle {
    animation-duration: 4s;
    transition: none;
  }
}
</style>
