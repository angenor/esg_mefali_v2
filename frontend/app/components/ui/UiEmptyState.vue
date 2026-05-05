<script setup lang="ts">
import type { UiSeverity } from '~/types/ui'

interface Props {
  severity?: UiSeverity | 'neutral'
  title?: string
  description?: string
  actionLabel?: string
}

withDefaults(defineProps<Props>(), {
  severity: 'neutral',
  title: undefined,
  description: undefined,
  actionLabel: undefined,
})

const emit = defineEmits<{
  (e: 'action'): void
}>()
</script>

<template>
  <div class="ui-empty" :data-severity="severity" role="status">
    <div v-if="$slots.illustration" class="ui-empty__illustration" aria-hidden="true">
      <slot name="illustration" />
    </div>
    <h3 v-if="$slots.title || title" class="ui-empty__title">
      <slot name="title">{{ title }}</slot>
    </h3>
    <p v-if="$slots.description || description" class="ui-empty__description">
      <slot name="description">{{ description }}</slot>
    </p>
    <div v-if="$slots.action || actionLabel" class="ui-empty__action">
      <slot name="action">
        <button v-if="actionLabel" type="button" class="ui-empty__action-btn" @click="emit('action')">
          {{ actionLabel }}
        </button>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.ui-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  text-align: center;
  font-family: var(--font-sans);
  color: var(--color-text);
}
.ui-empty__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  margin: 0;
}
.ui-empty__description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
}
.ui-empty__action-btn {
  background: var(--color-brand-500);
  color: #fff;
  border: 0;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  min-height: 44px;
}
.ui-empty__action-btn:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
</style>
