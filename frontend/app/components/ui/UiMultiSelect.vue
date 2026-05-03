<script setup lang="ts" generic="V extends string | number">
import { computed, ref } from 'vue'
import type { UiOption, UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: V[]
  options: UiOption<V>[]
  placeholder?: string
  creatable?: boolean
  maxSelected?: number
  disabled?: boolean
  size?: UiSize
  error?: string
  id?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  placeholder: 'Sélectionner…',
  creatable: false,
  maxSelected: undefined,
  disabled: false,
  size: 'md',
  error: undefined,
  id: undefined,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: V[]): void
  (e: 'select', opt: UiOption<V>): void
  (e: 'remove', opt: UiOption<V>): void
}>()

const search = ref('')
const open = ref(false)
const localId = props.id ?? useFieldId('ui-multi')

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return props.options
    .filter((o) => !props.modelValue.includes(o.value))
    .filter((o) => !q || o.label.toLowerCase().includes(q))
})

const selectedOptions = computed(() =>
  props.modelValue
    .map((v) => props.options.find((o) => o.value === v) ?? { value: v, label: String(v) })
)

function add(opt: UiOption<V>): void {
  if (props.maxSelected !== undefined && props.modelValue.length >= props.maxSelected) return
  emit('update:modelValue', [...props.modelValue, opt.value])
  emit('select', opt)
  search.value = ''
}

function remove(opt: UiOption<V>): void {
  emit('update:modelValue', props.modelValue.filter((v) => v !== opt.value))
  emit('remove', opt)
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Backspace' && search.value === '' && props.modelValue.length > 0) {
    const last = selectedOptions.value[selectedOptions.value.length - 1]!
    remove(last)
    e.preventDefault()
  } else if (e.key === 'Enter') {
    if (filtered.value.length > 0) {
      add(filtered.value[0]!)
    } else if (props.creatable && search.value.trim()) {
      const v = search.value.trim() as unknown as V
      add({ value: v, label: search.value.trim() })
    }
    e.preventDefault()
  }
}
</script>

<template>
  <div class="ui-multi" :data-size="size" :data-error="!!error || undefined">
    <div class="ui-multi__field" :id="localId">
      <span
        v-for="opt in selectedOptions"
        :key="String(opt.value)"
        class="ui-multi__chip"
        :data-removable="true"
      >
        <slot name="chip" :option="opt">{{ opt.label }}</slot>
        <button type="button" :aria-label="`Retirer ${opt.label}`" @click="remove(opt)">×</button>
      </span>
      <input
        v-model="search"
        :placeholder="modelValue.length === 0 ? placeholder : ''"
        :disabled="disabled"
        :aria-label="ariaLabel"
        :aria-invalid="!!error || undefined"
        class="ui-multi__input"
        @keydown="onKeydown"
        @focus="open = true"
        @blur="open = false"
      />
    </div>
    <ul v-if="open && filtered.length" role="listbox" class="ui-multi__list">
      <li
        v-for="o in filtered"
        :key="String(o.value)"
        role="option"
        :aria-selected="false"
        class="ui-multi__option"
        @mousedown.prevent="add(o)"
      >
        <slot name="option" :option="o">{{ o.label }}</slot>
      </li>
    </ul>
    <span v-if="error" class="ui-multi__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-multi__field {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  background: var(--color-surface);
  min-height: 44px;
}
.ui-multi[data-error] .ui-multi__field {
  border-color: var(--color-danger-500);
}
.ui-multi__field:focus-within {
  outline: 2px solid var(--color-focus-ring);
}
.ui-multi__chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  background: var(--color-brand-50);
  color: var(--color-brand-700);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  min-height: 28px;
}
.ui-multi__chip button {
  background: none;
  border: 0;
  cursor: pointer;
  color: inherit;
  font-size: var(--font-size-base);
}
.ui-multi__input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  min-width: 4rem;
}
.ui-multi__list {
  list-style: none;
  margin: var(--space-1) 0 0;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-md);
  max-height: 12rem;
  overflow-y: auto;
}
.ui-multi__option {
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
}
.ui-multi__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
