<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: string
  type?: 'text' | 'email' | 'password' | 'search' | 'tel' | 'url'
  size?: UiSize
  disabled?: boolean
  readonly?: boolean
  placeholder?: string
  maxlength?: number
  error?: string
  helper?: string
  clearable?: boolean
  id?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  type: 'text',
  size: 'md',
  disabled: false,
  readonly: false,
  placeholder: undefined,
  maxlength: undefined,
  error: undefined,
  helper: undefined,
  clearable: false,
  id: undefined,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
  (e: 'focus', evt: FocusEvent): void
  (e: 'blur', evt: FocusEvent): void
  (e: 'clear'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const localId = props.id ?? useFieldId('ui-input')
const helperId = `${localId}-helper`
const errorId = `${localId}-error`

const describedBy = computed(() => {
  const ids = []
  if (props.helper) ids.push(helperId)
  if (props.error) ids.push(errorId)
  return ids.length ? ids.join(' ') : undefined
})

function onInput(e: Event): void {
  const v = (e.target as HTMLInputElement).value
  emit('update:modelValue', v)
}
function onChange(e: Event): void {
  emit('change', (e.target as HTMLInputElement).value)
}
function onClear(): void {
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}

defineExpose({
  focus: () => inputRef.value?.focus(),
})
</script>

<template>
  <div class="ui-input" :data-size="size" :data-error="!!error || undefined">
    <span v-if="$slots.prefix" class="ui-input__prefix"><slot name="prefix" /></span>
    <input
      ref="inputRef"
      :id="localId"
      :type="type"
      :value="modelValue"
      :disabled="disabled"
      :readonly="readonly"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :aria-invalid="!!error || undefined"
      :aria-describedby="describedBy"
      :aria-label="ariaLabel"
      class="ui-input__control"
      @input="onInput"
      @change="onChange"
      @focus="emit('focus', $event)"
      @blur="emit('blur', $event)"
    />
    <button
      v-if="clearable && modelValue"
      type="button"
      aria-label="Effacer"
      class="ui-input__clear"
      @click="onClear"
    >
      ×
    </button>
    <span v-if="$slots.suffix" class="ui-input__suffix"><slot name="suffix" /></span>
    <span v-if="helper && !error" :id="helperId" class="ui-input__helper">
      <slot name="helper">{{ helper }}</slot>
    </span>
    <span v-if="error" :id="errorId" class="ui-input__error" role="alert">
      <slot name="error">{{ error }}</slot>
    </span>
  </div>
</template>

<style scoped>
.ui-input {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-family: var(--font-sans);
}
.ui-input[data-size='sm'] {
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-size-sm);
}
.ui-input[data-size='lg'] {
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-lg);
}
.ui-input[data-error] {
  border-color: var(--color-danger-500);
}
.ui-input:focus-within {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 1px;
}
.ui-input__control {
  border: 0;
  outline: 0;
  background: transparent;
  width: 100%;
  font: inherit;
  color: var(--color-text);
  min-height: 28px;
}
.ui-input__clear {
  background: none;
  border: 0;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: var(--font-size-lg);
  min-width: 24px;
  min-height: 24px;
}
.ui-input__helper,
.ui-input__error {
  grid-column: 1 / -1;
  font-size: var(--font-size-xs);
}
.ui-input__helper {
  color: var(--color-text-muted);
}
.ui-input__error {
  color: var(--color-danger-700);
}
</style>
