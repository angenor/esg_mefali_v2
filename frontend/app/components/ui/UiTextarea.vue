<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

defineOptions({
  // Forward extra attrs (data-testid, custom HTML attributes) on the
  // textarea element rather than the wrapper div, so E2E selectors and
  // labelling tools can target the actual input.
  inheritAttrs: false,
})

interface Props {
  modelValue?: string
  rows?: number
  maxlength?: number
  autosize?: boolean
  disabled?: boolean
  readonly?: boolean
  placeholder?: string
  error?: string
  helper?: string
  size?: UiSize
  id?: string
  ariaLabel?: string
  showCounter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  rows: 3,
  maxlength: undefined,
  autosize: false,
  disabled: false,
  readonly: false,
  placeholder: undefined,
  error: undefined,
  helper: undefined,
  size: 'md',
  id: undefined,
  ariaLabel: undefined,
  showCounter: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'focus', evt: FocusEvent): void
  (e: 'blur', evt: FocusEvent): void
}>()

const ta = ref<HTMLTextAreaElement | null>(null)
const localId = props.id ?? useFieldId('ui-textarea')
const helperId = `${localId}-helper`
const errorId = `${localId}-error`

const describedBy = computed(() => {
  const ids = []
  if (props.helper) ids.push(helperId)
  if (props.error) ids.push(errorId)
  return ids.length ? ids.join(' ') : undefined
})

function resize(): void {
  if (!props.autosize || !ta.value) return
  ta.value.style.height = 'auto'
  ta.value.style.height = `${ta.value.scrollHeight}px`
}

function onInput(e: Event): void {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
  nextTick(resize)
}

watch(() => props.modelValue, () => nextTick(resize))
onMounted(resize)

defineExpose({ focus: () => ta.value?.focus() })
</script>

<template>
  <div class="ui-textarea" :data-size="size" :data-error="!!error || undefined">
    <textarea
      ref="ta"
      :id="localId"
      :rows="rows"
      :value="modelValue"
      :disabled="disabled"
      :readonly="readonly"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :aria-invalid="!!error || undefined"
      :aria-describedby="describedBy"
      :aria-label="ariaLabel"
      class="ui-textarea__control"
      v-bind="$attrs"
      @input="onInput"
      @focus="emit('focus', $event)"
      @blur="emit('blur', $event)"
    />
    <span v-if="helper && !error" :id="helperId" class="ui-textarea__helper">
      <slot name="helper">{{ helper }}</slot>
    </span>
    <span v-if="error" :id="errorId" class="ui-textarea__error" role="alert">
      <slot name="error">{{ error }}</slot>
    </span>
    <span v-if="showCounter && maxlength" class="ui-textarea__counter">
      <slot name="counter">{{ modelValue.length }}/{{ maxlength }}</slot>
    </span>
  </div>
</template>

<style scoped>
.ui-textarea {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ui-textarea__control {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-family: var(--font-sans);
  resize: vertical;
  background: var(--color-surface);
  color: var(--color-text);
  min-height: 64px;
}
.ui-textarea[data-error] .ui-textarea__control {
  border-color: var(--color-danger-500);
}
.ui-textarea__control:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 1px;
}
.ui-textarea__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-textarea__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
.ui-textarea__counter {
  align-self: flex-end;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
</style>
