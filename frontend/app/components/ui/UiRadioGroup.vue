<script setup lang="ts" generic="V extends string | number">
import { computed, ref } from 'vue'
import type { UiOption, UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: V | null
  options: UiOption<V>[]
  layout?: 'inline' | 'stacked'
  size?: UiSize
  disabled?: boolean
  ariaLabel?: string
  name?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  layout: 'stacked',
  size: 'md',
  disabled: false,
  ariaLabel: undefined,
  name: undefined,
  id: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: V): void
  (e: 'change', v: V): void
}>()

const groupId = props.id ?? useFieldId('ui-radio-group')
const groupName = props.name ?? groupId
const itemRefs = ref<Record<string, HTMLElement>>({})

const enabledIndex = computed(() =>
  props.options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0),
)

function isSelected(opt: UiOption<V>): boolean {
  return props.modelValue !== null && props.modelValue === opt.value
}

function selectIndex(idx: number): void {
  const opt = props.options[idx]
  if (!opt || opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  const el = itemRefs.value[String(opt.value)]
  el?.focus()
}

function onKeydown(e: KeyboardEvent, currentIdx: number): void {
  const enabled = enabledIndex.value
  if (enabled.length === 0) return
  const pos = enabled.indexOf(currentIdx)
  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
    e.preventDefault()
    selectIndex(enabled[(pos + 1) % enabled.length]!)
  } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
    e.preventDefault()
    selectIndex(enabled[(pos - 1 + enabled.length) % enabled.length]!)
  } else if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    selectIndex(currentIdx)
  } else if (e.key === 'Home') {
    e.preventDefault()
    selectIndex(enabled[0]!)
  } else if (e.key === 'End') {
    e.preventDefault()
    selectIndex(enabled[enabled.length - 1]!)
  }
}

function tabIndexFor(opt: UiOption<V>, idx: number): number {
  if (opt.disabled) return -1
  if (props.modelValue !== null) {
    return isSelected(opt) ? 0 : -1
  }
  // Aucun selected : premier non-disabled est tabbable.
  return enabledIndex.value[0] === idx ? 0 : -1
}

function setItemRef(value: V, el: Element | null): void {
  if (el) itemRefs.value[String(value)] = el as HTMLElement
}
</script>

<template>
  <div
    :id="groupId"
    role="radiogroup"
    :aria-label="ariaLabel"
    :aria-disabled="disabled || undefined"
    :data-layout="layout"
    :data-size="size"
    class="ui-radio-group"
  >
    <label
      v-for="(opt, idx) in options"
      :key="String(opt.value)"
      class="ui-radio-group__item"
      :data-disabled="opt.disabled || disabled || undefined"
    >
      <span
        :ref="(el) => setItemRef(opt.value, el as Element | null)"
        role="radio"
        :aria-checked="isSelected(opt)"
        :aria-disabled="opt.disabled || disabled || undefined"
        :aria-label="opt.label"
        :tabindex="disabled ? -1 : tabIndexFor(opt, idx)"
        :data-name="groupName"
        class="ui-radio-group__control"
        @click="!disabled && !opt.disabled && selectIndex(idx)"
        @keydown="onKeydown($event, idx)"
      />
      <span class="ui-radio-group__label" aria-hidden="true">{{ opt.label }}</span>
    </label>
  </div>
</template>

<style scoped>
.ui-radio-group {
  display: flex;
  gap: var(--space-3);
  font-family: var(--font-sans);
}
.ui-radio-group[data-layout='stacked'] {
  flex-direction: column;
}
.ui-radio-group[data-layout='inline'] {
  flex-direction: row;
  flex-wrap: wrap;
}
.ui-radio-group__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  min-height: 44px;
}
.ui-radio-group__item[data-disabled] {
  cursor: not-allowed;
  opacity: 0.6;
}
.ui-radio-group__control {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-radius: 50%;
  display: inline-block;
  position: relative;
  background: var(--color-surface);
}
.ui-radio-group__control[aria-checked='true'] {
  border-color: var(--color-brand-500);
}
.ui-radio-group__control[aria-checked='true']::after {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: var(--color-brand-500);
}
.ui-radio-group__control:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
</style>
