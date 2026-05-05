<script setup lang="ts" generic="V extends string | number">
import { computed } from 'vue'
import type { UiOption, UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: V[]
  options: UiOption<V>[]
  layout?: 'inline' | 'stacked'
  size?: UiSize
  disabled?: boolean
  ariaLabel?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  layout: 'stacked',
  size: 'md',
  disabled: false,
  ariaLabel: undefined,
  id: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: V[]): void
  (e: 'change', v: V[]): void
}>()

const groupId = props.id ?? useFieldId('ui-checkbox-group')

const selected = computed(() => new Set(props.modelValue))

function isChecked(opt: UiOption<V>): boolean {
  return selected.value.has(opt.value)
}

function toggle(opt: UiOption<V>): void {
  if (props.disabled || opt.disabled) return
  const set = new Set(props.modelValue)
  if (set.has(opt.value)) set.delete(opt.value)
  else set.add(opt.value)
  const next = [...set]
  emit('update:modelValue', next)
  emit('change', next)
}
</script>

<template>
  <fieldset
    :id="groupId"
    :aria-label="ariaLabel"
    :aria-disabled="disabled || undefined"
    :data-layout="layout"
    :data-size="size"
    class="ui-checkbox-group"
  >
    <label
      v-for="opt in options"
      :key="String(opt.value)"
      class="ui-checkbox-group__item"
      :data-disabled="opt.disabled || disabled || undefined"
    >
      <input
        type="checkbox"
        class="ui-checkbox-group__control"
        :checked="isChecked(opt)"
        :disabled="disabled || opt.disabled"
        :aria-checked="isChecked(opt)"
        @change="toggle(opt)"
      />
      <span class="ui-checkbox-group__label">{{ opt.label }}</span>
    </label>
  </fieldset>
</template>

<style scoped>
.ui-checkbox-group {
  display: flex;
  gap: var(--space-3);
  border: 0;
  margin: 0;
  padding: 0;
  font-family: var(--font-sans);
}
.ui-checkbox-group[data-layout='stacked'] {
  flex-direction: column;
}
.ui-checkbox-group[data-layout='inline'] {
  flex-direction: row;
  flex-wrap: wrap;
}
.ui-checkbox-group__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  min-height: 44px;
}
.ui-checkbox-group__item[data-disabled] {
  cursor: not-allowed;
  opacity: 0.6;
}
.ui-checkbox-group__control {
  width: 18px;
  height: 18px;
  accent-color: var(--color-brand-500);
}
.ui-checkbox-group__control:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
</style>
