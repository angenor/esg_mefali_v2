<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: string | null
  min?: string
  max?: string
  disabled?: boolean
  readonly?: boolean
  error?: string
  helper?: string
  size?: UiSize
  id?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  min: undefined,
  max: undefined,
  disabled: false,
  readonly: false,
  error: undefined,
  helper: undefined,
  size: 'md',
  id: undefined,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string | null): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const localId = props.id ?? useFieldId('ui-date')
const helperId = `${localId}-helper`
const errorId = `${localId}-error`

const describedBy = computed(() => {
  const ids = []
  if (props.helper) ids.push(helperId)
  if (props.error) ids.push(errorId)
  return ids.length ? ids.join(' ') : undefined
})

function isValidIso(s: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s))
}

function clamp(v: string): string | null {
  if (!isValidIso(v)) return null
  if (props.min && v < props.min) return props.min
  if (props.max && v > props.max) return props.max
  return v
}

function onInput(e: Event): void {
  const v = (e.target as HTMLInputElement).value
  if (v === '') {
    emit('update:modelValue', null)
    return
  }
  const ok = clamp(v)
  if (ok === null) return // valeur invalide ne casse pas le modelValue
  emit('update:modelValue', ok)
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<template>
  <div class="ui-date" :data-size="size" :data-error="!!error || undefined">
    <input
      ref="inputRef"
      :id="localId"
      type="date"
      lang="fr-FR"
      :value="modelValue ?? ''"
      :min="min"
      :max="max"
      :disabled="disabled"
      :readonly="readonly"
      :aria-invalid="!!error || undefined"
      :aria-describedby="describedBy"
      :aria-label="ariaLabel"
      class="ui-date__control"
      @input="onInput"
      @change="onInput"
    />
    <span v-if="helper && !error" :id="helperId" class="ui-date__helper">{{ helper }}</span>
    <span v-if="error" :id="errorId" class="ui-date__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-date {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ui-date__control {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-family: var(--font-sans);
  min-height: 44px;
  color: var(--color-text);
  background: var(--color-surface);
}
.ui-date[data-error] .ui-date__control {
  border-color: var(--color-danger-500);
}
.ui-date__control:focus-visible {
  outline: 2px solid var(--color-focus-ring);
}
.ui-date__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-date__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
