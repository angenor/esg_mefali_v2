<script setup lang="ts">
import { computed } from 'vue'
import { useField } from 'vee-validate'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  name?: string
  label?: string
  helper?: string
  required?: boolean
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  name: undefined,
  label: undefined,
  helper: undefined,
  required: false,
  id: undefined,
})

const localId = props.id ?? useFieldId('ui-field')
const helperId = `${localId}-helper`
const errorId = `${localId}-error`

// Branche vee-validate optionnelle.
const veeField = props.name
  ? useField(props.name, undefined, { validateOnValueUpdate: true })
  : null

const errorMessage = computed(() => veeField?.errorMessage.value)
const value = computed(() => veeField?.value.value)

function onUpdate(v: unknown): void {
  if (veeField) veeField.handleChange(v)
}

const describedBy = computed(() => {
  const ids = []
  if (props.helper) ids.push(helperId)
  if (errorMessage.value) ids.push(errorId)
  return ids.length ? ids.join(' ') : undefined
})

const slotProps = computed(() => ({
  id: localId,
  modelValue: value.value,
  'onUpdate:modelValue': onUpdate,
  'aria-invalid': !!errorMessage.value || undefined,
  'aria-describedby': describedBy.value,
  error: errorMessage.value,
  state: {
    invalid: !!errorMessage.value,
    errorMessage: errorMessage.value,
    describedById: describedBy.value,
  },
}))
</script>

<template>
  <div class="ui-field">
    <label v-if="label" :for="localId" class="ui-field__label">
      {{ label }}
      <span v-if="required" aria-hidden="true">*</span>
    </label>
    <slot v-bind="slotProps" />
    <span v-if="helper && !errorMessage" :id="helperId" class="ui-field__helper">{{ helper }}</span>
    <span v-if="errorMessage" :id="errorId" class="ui-field__error" role="alert">
      {{ errorMessage }}
    </span>
  </div>
</template>

<style scoped>
.ui-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-family: var(--font-sans);
}
.ui-field__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}
.ui-field__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-field__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
