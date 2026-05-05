<script setup lang="ts">
interface Props {
  shape?: 'line' | 'rect' | 'circle'
  lines?: number
  width?: string
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  shape: 'line',
  lines: 1,
  width: undefined,
  height: undefined,
})
</script>

<template>
  <span
    v-if="shape !== 'line' || lines === 1"
    class="ui-skeleton"
    :data-shape="shape"
    :style="{ width, height }"
    aria-hidden="true"
  />
  <span v-else class="ui-skeleton-group" aria-hidden="true">
    <span
      v-for="i in lines"
      :key="i"
      class="ui-skeleton"
      data-shape="line"
      :style="{ width: i === lines ? '70%' : width || '100%' }"
    />
  </span>
</template>

<style scoped>
.ui-skeleton {
  display: inline-block;
  background: linear-gradient(
    90deg,
    var(--color-surface-muted) 25%,
    var(--color-border) 37%,
    var(--color-surface-muted) 63%
  );
  background-size: 400% 100%;
  animation: ui-skeleton-shimmer 1.4s ease infinite;
  border-radius: var(--radius-sm);
}
.ui-skeleton[data-shape='line'] {
  height: 0.9em;
  width: 100%;
}
.ui-skeleton[data-shape='rect'] {
  width: 100%;
  height: 6rem;
}
.ui-skeleton[data-shape='circle'] {
  width: 36px;
  height: 36px;
  border-radius: 50%;
}
.ui-skeleton-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}
@keyframes ui-skeleton-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .ui-skeleton {
    animation: none;
  }
}
</style>
