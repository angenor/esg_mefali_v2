<script setup lang="ts" generic="V extends string | number">
import { computed, ref } from 'vue'
import type { UiOption, UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: V | null
  options: UiOption<V>[]
  groups?: string[]
  placeholder?: string
  clearable?: boolean
  disabled?: boolean
  size?: UiSize
  error?: string
  helper?: string
  id?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  groups: undefined,
  placeholder: 'Sélectionner…',
  clearable: true,
  disabled: false,
  size: 'md',
  error: undefined,
  helper: undefined,
  id: undefined,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: V | null): void
  (e: 'change', v: V | null): void
}>()

const selectRef = ref<HTMLSelectElement | null>(null)
const localId = props.id ?? useFieldId('ui-select')

const grouped = computed<Record<string, UiOption<V>[]>>(() => {
  if (!props.groups || props.groups.length === 0) {
    return { __default: props.options }
  }
  const out: Record<string, UiOption<V>[]> = {}
  for (const g of props.groups) out[g] = []
  for (const o of props.options) {
    const g = o.group ?? '__default'
    if (!out[g]) out[g] = []
    out[g].push(o)
  }
  return out
})

function onChange(e: Event): void {
  const v = (e.target as HTMLSelectElement).value
  if (v === '') {
    emit('update:modelValue', null)
    emit('change', null)
    return
  }
  // Coerce back to original type by lookup.
  const opt = props.options.find((o) => String(o.value) === v)
  emit('update:modelValue', (opt?.value ?? (v as unknown)) as V | null)
  emit('change', (opt?.value ?? (v as unknown)) as V | null)
}

defineExpose({ focus: () => selectRef.value?.focus() })
</script>

<template>
  <div class="ui-select" :data-size="size" :data-error="!!error || undefined">
    <select
      ref="selectRef"
      :id="localId"
      :value="modelValue ?? ''"
      :disabled="disabled"
      :aria-invalid="!!error || undefined"
      :aria-label="ariaLabel"
      class="ui-select__control"
      @change="onChange"
    >
      <option v-if="clearable || modelValue == null" value="">{{ placeholder }}</option>
      <template v-for="(opts, group) in grouped" :key="group">
        <optgroup v-if="group !== '__default'" :label="String(group)">
          <option
            v-for="o in opts"
            :key="String(o.value)"
            :value="String(o.value)"
            :disabled="o.disabled"
          >
            {{ o.label }}
          </option>
        </optgroup>
        <template v-else>
          <option
            v-for="o in opts"
            :key="String(o.value)"
            :value="String(o.value)"
            :disabled="o.disabled"
          >
            {{ o.label }}
          </option>
        </template>
      </template>
    </select>
    <span v-if="helper && !error" class="ui-select__helper">{{ helper }}</span>
    <span v-if="error" class="ui-select__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-select {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ui-select__control {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  font: inherit;
  font-family: var(--font-sans);
  min-height: 44px;
  color: var(--color-text);
}
.ui-select[data-error] .ui-select__control {
  border-color: var(--color-danger-500);
}
.ui-select__control:focus-visible {
  outline: 2px solid var(--color-focus-ring);
}
.ui-select__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-select__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
