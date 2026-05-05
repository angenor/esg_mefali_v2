<script setup lang="ts">
import type { UiSeverity } from '~/types/ui'

interface Props {
  severity?: UiSeverity
  variant?: 'subtle' | 'solid'
}

withDefaults(defineProps<Props>(), {
  severity: 'info',
  variant: 'subtle',
})
</script>

<template>
  <span class="ui-badge" :data-severity="severity" :data-variant="variant">
    <slot />
  </span>
</template>

<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-2);
  height: 20px;
  border-radius: 999px;
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: 1;
}
.ui-badge[data-variant='subtle'][data-severity='info'] { background: var(--color-info-50); color: var(--color-info-700); }
.ui-badge[data-variant='subtle'][data-severity='success'] { background: var(--color-success-50); color: var(--color-success-700); }
.ui-badge[data-variant='subtle'][data-severity='warning'] { background: var(--color-warning-50); color: var(--color-warning-700); }
.ui-badge[data-variant='subtle'][data-severity='error'] { background: var(--color-danger-50); color: var(--color-danger-700); }
.ui-badge[data-variant='solid'] { color: #fff; }
.ui-badge[data-variant='solid'][data-severity='info'] { background: var(--color-info-500); }
.ui-badge[data-variant='solid'][data-severity='success'] { background: var(--color-success-500); }
.ui-badge[data-variant='solid'][data-severity='warning'] { background: var(--color-warning-500); }
.ui-badge[data-variant='solid'][data-severity='error'] { background: var(--color-danger-500); }
</style>
