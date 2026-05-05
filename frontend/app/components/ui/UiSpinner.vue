<script setup lang="ts">
import type { UiSize } from '~/types/ui'

interface Props {
  size?: UiSize
  label?: string
}

withDefaults(defineProps<Props>(), {
  size: 'md',
  label: 'Chargement…',
})
</script>

<template>
  <span class="ui-spinner" role="status" :aria-label="label" :data-size="size">
    <span class="ui-spinner__svg" aria-hidden="true" />
  </span>
</template>

<style scoped>
.ui-spinner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ui-spinner[data-size='sm'] { width: 16px; height: 16px; }
.ui-spinner[data-size='md'] { width: 24px; height: 24px; }
.ui-spinner[data-size='lg'] { width: 36px; height: 36px; }
.ui-spinner__svg {
  width: 100%;
  height: 100%;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-brand-500);
  border-radius: 50%;
  animation: ui-spinner-rot 0.8s linear infinite;
}
@keyframes ui-spinner-rot {
  to { transform: rotate(360deg); }
}
@media (prefers-reduced-motion: reduce) {
  .ui-spinner__svg { animation-duration: 4s; }
}
</style>
