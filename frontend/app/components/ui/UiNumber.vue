<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'
import { useMoneyFormat } from '~/composables/useMoneyFormat'

interface Props {
  modelValue?: number | null
  mode?: 'plain' | 'money'
  currency?: string
  locale?: string
  precision?: number
  min?: number
  max?: number
  step?: number
  disabled?: boolean
  readonly?: boolean
  placeholder?: string
  error?: string
  helper?: string
  size?: UiSize
  id?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  mode: 'plain',
  currency: undefined,
  locale: 'fr-FR',
  precision: undefined,
  min: undefined,
  max: undefined,
  step: undefined,
  disabled: false,
  readonly: false,
  placeholder: undefined,
  error: undefined,
  helper: undefined,
  size: 'md',
  id: undefined,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: number | null): void
  (e: 'focus', evt: FocusEvent): void
  (e: 'blur', evt: FocusEvent): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const focused = ref(false)
const localId = props.id ?? useFieldId('ui-number')
const helperId = `${localId}-helper`
const errorId = `${localId}-error`

const money = computed(() => {
  if (props.mode !== 'money' || !props.currency) return null
  return useMoneyFormat({
    currency: props.currency,
    locale: props.locale,
    precision: props.precision,
  })
})

const displayed = computed(() => {
  if (focused.value) {
    return props.modelValue == null ? '' : String(props.modelValue)
  }
  if (money.value) return money.value.display(props.modelValue)
  return props.modelValue == null ? '' : String(props.modelValue)
})

const describedBy = computed(() => {
  const ids = []
  if (props.helper) ids.push(helperId)
  if (props.error) ids.push(errorId)
  return ids.length ? ids.join(' ') : undefined
})

function clamp(n: number): number {
  if (props.min !== undefined && n < props.min) return props.min
  if (props.max !== undefined && n > props.max) return props.max
  return n
}

function onInput(e: Event): void {
  const raw = (e.target as HTMLInputElement).value
  if (raw === '') {
    emit('update:modelValue', null)
    return
  }
  let n: number | null = null
  if (money.value) n = money.value.parse(raw)
  else {
    const cleaned = raw.replace(',', '.')
    const candidate = Number(cleaned)
    n = Number.isFinite(candidate) ? candidate : null
  }
  if (n === null) return
  emit('update:modelValue', clamp(n))
}

function onFocus(e: FocusEvent): void {
  focused.value = true
  emit('focus', e)
}
function onBlur(e: FocusEvent): void {
  focused.value = false
  emit('blur', e)
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<template>
  <div class="ui-number" :data-size="size" :data-error="!!error || undefined">
    <span v-if="$slots.prefix" class="ui-number__prefix"><slot name="prefix" /></span>
    <input
      ref="inputRef"
      :id="localId"
      :value="displayed"
      :disabled="disabled"
      :readonly="readonly"
      :placeholder="placeholder"
      :step="step"
      :aria-invalid="!!error || undefined"
      :aria-describedby="describedBy"
      :aria-label="ariaLabel"
      type="text"
      inputmode="decimal"
      class="ui-number__control"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
    />
    <span v-if="$slots.suffix" class="ui-number__suffix"><slot name="suffix" /></span>
    <span v-if="helper && !error" :id="helperId" class="ui-number__helper">{{ helper }}</span>
    <span v-if="error" :id="errorId" class="ui-number__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-number {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-family: var(--font-sans);
}
.ui-number[data-error] {
  border-color: var(--color-danger-500);
}
.ui-number:focus-within {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 1px;
}
.ui-number__control {
  border: 0;
  outline: 0;
  background: transparent;
  width: 100%;
  font: inherit;
  text-align: right;
  color: var(--color-text);
}
.ui-number__helper,
.ui-number__error {
  grid-column: 1 / -1;
  font-size: var(--font-size-xs);
}
.ui-number__helper {
  color: var(--color-text-muted);
}
.ui-number__error {
  color: var(--color-danger-700);
}
</style>
