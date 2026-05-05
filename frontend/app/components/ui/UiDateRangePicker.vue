<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

interface DateRange {
  start: string
  end: string
}

interface Props {
  modelValue?: DateRange | null
  min?: string
  max?: string
  disabled?: boolean
  error?: string
  helper?: string
  size?: UiSize
  id?: string
  locale?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  min: undefined,
  max: undefined,
  disabled: false,
  error: undefined,
  helper: undefined,
  size: 'md',
  id: undefined,
  locale: 'fr-FR',
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: DateRange | null): void
}>()

const localId = props.id ?? useFieldId('ui-range')
const start = ref(props.modelValue?.start ?? '')
const end = ref(props.modelValue?.end ?? '')

const fmt = computed(
  () => new Intl.DateTimeFormat(props.locale, { weekday: 'long', day: 'numeric', month: 'long' }),
)

function isValidIso(s: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s))
}

function clamp(v: string): string {
  if (props.min && v < props.min) return props.min
  if (props.max && v > props.max) return props.max
  return v
}

function emitRange(): void {
  if (start.value && end.value && isValidIso(start.value) && isValidIso(end.value)) {
    let s = clamp(start.value)
    let e = clamp(end.value)
    if (s > e) [s, e] = [e, s]
    emit('update:modelValue', { start: s, end: e })
  } else if (!start.value && !end.value) {
    emit('update:modelValue', null)
  }
}

const startLabel = computed(() => (start.value && isValidIso(start.value) ? fmt.value.format(new Date(start.value)) : ''))
const endLabel = computed(() => (end.value && isValidIso(end.value) ? fmt.value.format(new Date(end.value)) : ''))
</script>

<template>
  <div class="ui-range" :data-size="size" :data-error="!!error || undefined" :id="localId">
    <div class="ui-range__field">
      <label class="ui-range__leg">
        <span class="ui-range__label">Début</span>
        <input
          v-model="start"
          type="date"
          lang="fr-FR"
          :min="min"
          :max="max"
          :disabled="disabled"
          @change="emitRange"
        />
        <span v-if="startLabel" class="ui-range__pretty">{{ startLabel }}</span>
      </label>
      <label class="ui-range__leg">
        <span class="ui-range__label">Fin</span>
        <input
          v-model="end"
          type="date"
          lang="fr-FR"
          :min="start || min"
          :max="max"
          :disabled="disabled"
          @change="emitRange"
        />
        <span v-if="endLabel" class="ui-range__pretty">{{ endLabel }}</span>
      </label>
    </div>
    <span v-if="helper && !error" class="ui-range__helper">{{ helper }}</span>
    <span v-if="error" class="ui-range__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-range__field {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.ui-range__leg {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ui-range__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.ui-range__pretty {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.ui-range[data-error] input {
  border-color: var(--color-danger-500);
}
.ui-range input {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  min-height: 44px;
  font: inherit;
  background: var(--color-surface);
  color: var(--color-text);
}
.ui-range input:focus-visible {
  outline: 2px solid var(--color-focus-ring);
}
.ui-range__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-range__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
