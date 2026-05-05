<script setup lang="ts">
interface Props {
  removable?: boolean
  ariaLabel?: string
  removeAriaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  removable: false,
  ariaLabel: undefined,
  removeAriaLabel: 'Retirer',
})

const emit = defineEmits<{
  (e: 'remove'): void
}>()

function onRemoveKey(e: KeyboardEvent): void {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('remove')
  }
}
</script>

<template>
  <span class="ui-tag" :aria-label="ariaLabel">
    <slot />
    <button
      v-if="removable"
      type="button"
      class="ui-tag__remove"
      :aria-label="removeAriaLabel"
      @click="emit('remove')"
      @keydown="onRemoveKey"
    >
      ×
    </button>
  </span>
</template>

<style scoped>
.ui-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  color: var(--color-text);
}
.ui-tag__remove {
  background: none;
  border: 0;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1;
  min-width: 20px;
  min-height: 20px;
}
.ui-tag__remove:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  border-radius: var(--radius-sm);
}
</style>
