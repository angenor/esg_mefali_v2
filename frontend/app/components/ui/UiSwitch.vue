<script setup lang="ts">
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: boolean
  size?: UiSize
  disabled?: boolean
  ariaLabel?: string
  labelOn?: string
  labelOff?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  size: 'md',
  disabled: false,
  ariaLabel: undefined,
  labelOn: undefined,
  labelOff: undefined,
  id: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'change', v: boolean): void
}>()

const switchId = props.id ?? useFieldId('ui-switch')

function toggle(): void {
  if (props.disabled) return
  const next = !props.modelValue
  emit('update:modelValue', next)
  emit('change', next)
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    toggle()
  }
}
</script>

<template>
  <button
    :id="switchId"
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="ariaLabel"
    :aria-disabled="disabled || undefined"
    :disabled="disabled"
    :data-size="size"
    :data-checked="modelValue || undefined"
    class="ui-switch"
    @click="toggle"
    @keydown="onKeydown"
  >
    <span class="ui-switch__track">
      <span class="ui-switch__thumb" />
    </span>
    <span v-if="modelValue && labelOn" class="ui-switch__label">
      <slot name="label-on">{{ labelOn }}</slot>
    </span>
    <span v-else-if="!modelValue && labelOff" class="ui-switch__label">
      <slot name="label-off">{{ labelOff }}</slot>
    </span>
  </button>
</template>

<style scoped>
.ui-switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  border: 0;
  padding: 0;
  cursor: pointer;
  font-family: var(--font-sans);
  min-height: 44px;
  min-width: 44px;
}
.ui-switch[data-size='sm'] {
  min-height: 36px;
  min-width: 36px;
}
.ui-switch:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ui-switch__track {
  width: 36px;
  height: 20px;
  background: var(--color-border);
  border-radius: 999px;
  position: relative;
  transition: background-color var(--duration-fast) var(--ease-out);
}
.ui-switch[data-checked] .ui-switch__track {
  background: var(--color-brand-500);
}
.ui-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: transform var(--duration-fast) var(--ease-out);
}
.ui-switch[data-checked] .ui-switch__thumb {
  transform: translateX(16px);
}
.ui-switch:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
@media (prefers-reduced-motion: reduce) {
  .ui-switch__track,
  .ui-switch__thumb {
    transition: none;
  }
}
.ui-switch__label {
  font-size: var(--font-size-sm);
  color: var(--color-text);
}
</style>
