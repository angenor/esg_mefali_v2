<script setup lang="ts">
import { computed, onMounted } from 'vue'
import type { UiSize, UiVariant } from '~/types/ui'

interface Props {
  variant?: UiVariant
  size?: UiSize
  loading?: boolean
  disabled?: boolean
  iconOnly?: boolean
  type?: 'button' | 'submit' | 'reset'
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
  iconOnly: false,
  type: 'button',
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'click', evt: MouseEvent): void
}>()

onMounted(() => {
  if (process.env.NODE_ENV !== 'production' && props.iconOnly && !props.ariaLabel) {
    // eslint-disable-next-line no-console
    console.warn('[UiButton] iconOnly requires `ariaLabel`')
  }
})

const isDisabled = computed(() => props.disabled || props.loading)

function onClick(e: MouseEvent): void {
  if (isDisabled.value) {
    e.preventDefault()
    e.stopPropagation()
    return
  }
  emit('click', e)
}
</script>

<template>
  <button
    :type="type"
    :disabled="isDisabled"
    :aria-disabled="isDisabled || undefined"
    :aria-busy="loading || undefined"
    :aria-label="ariaLabel"
    :data-variant="variant"
    :data-size="size"
    :data-loading="loading || undefined"
    :data-icon-only="iconOnly || undefined"
    class="ui-button"
    @click="onClick"
  >
    <span v-if="loading" class="ui-button__spinner" aria-hidden="true" />
    <span v-else-if="$slots.prefix" class="ui-button__prefix">
      <slot name="prefix" />
    </span>
    <span v-if="!iconOnly || !loading" class="ui-button__label">
      <slot />
    </span>
    <span v-if="$slots.suffix && !loading" class="ui-button__suffix">
      <slot name="suffix" />
    </span>
  </button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  font-family: var(--font-sans);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-out);
  min-height: 44px;
  min-width: 44px;
}
.ui-button[data-size='sm'] {
  font-size: var(--font-size-sm);
  padding: var(--space-1) var(--space-3);
  min-height: 36px;
  min-width: 36px;
}
.ui-button[data-size='md'] {
  font-size: var(--font-size-base);
  padding: var(--space-2) var(--space-4);
}
.ui-button[data-size='lg'] {
  font-size: var(--font-size-lg);
  padding: var(--space-3) var(--space-6);
}
.ui-button[data-variant='primary'] {
  background: var(--color-brand-500);
  color: #fff;
}
.ui-button[data-variant='primary']:hover:not(:disabled) {
  background: var(--color-brand-600);
}
.ui-button[data-variant='secondary'] {
  background: var(--color-surface);
  color: var(--color-text);
  border-color: var(--color-border);
}
.ui-button[data-variant='ghost'] {
  background: transparent;
  color: var(--color-text);
}
.ui-button[data-variant='danger'] {
  background: var(--color-danger-500);
  color: #fff;
}
.ui-button[data-variant='link'] {
  background: transparent;
  color: var(--color-brand-600);
  text-decoration: underline;
  min-height: auto;
  min-width: auto;
  padding: 0;
}
.ui-button:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
.ui-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}
.ui-button__spinner {
  width: 1em;
  height: 1em;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: ui-button-spin 0.7s linear infinite;
}
@media (prefers-reduced-motion: reduce) {
  .ui-button__spinner {
    animation: none;
  }
}
@keyframes ui-button-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
