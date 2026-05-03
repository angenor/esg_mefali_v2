<script setup lang="ts">
/**
 * ShowForm — formulaire multi-champs typé.
 * Validation locale par champ (required + bornes) ; soumission bloquée si invalide.
 * vee-validate est dispo dans le projet mais on reste léger en MVP : un objet de
 * validation manuelle suffit pour un nombre raisonnable de champs.
 */
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'show_form' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const title = computed(() => sanitizeText(props.instruction.payload.title))
const fields = computed(() =>
  props.instruction.payload.fields.map((f) => ({ ...f, label: sanitizeText(f.label) })),
)

type FieldValue = string | number | boolean | null
const values = ref<Record<string, FieldValue>>(
  Object.fromEntries(fields.value.map((f) => [f.name, f.type === 'checkbox' ? false : ''])),
)

const errors = computed<Record<string, string | null>>(() => {
  const errs: Record<string, string | null> = {}
  for (const f of fields.value) {
    const v = values.value[f.name]
    if (f.required) {
      if (f.type === 'checkbox' && v !== true) {
        errs[f.name] = 'Champ requis'
        continue
      }
      if (f.type !== 'checkbox' && (v === '' || v === null || v === undefined)) {
        errs[f.name] = 'Champ requis'
        continue
      }
    }
    if (f.type === 'number' && v !== '' && v !== null) {
      const n = typeof v === 'number' ? v : Number.parseFloat(String(v))
      if (Number.isNaN(n)) {
        errs[f.name] = 'Nombre attendu'
        continue
      }
      if (f.min !== undefined && n < f.min) errs[f.name] = `≥ ${f.min}`
      else if (f.max !== undefined && n > f.max) errs[f.name] = `≤ ${f.max}`
      else errs[f.name] = null
      continue
    }
    if ((f.type === 'text' || f.type === 'textarea') && f.max_length !== undefined && typeof v === 'string' && v.length > f.max_length) {
      errs[f.name] = `≤ ${f.max_length} caractères`
      continue
    }
    errs[f.name] = null
  }
  return errs
})

const submitDisabled = computed(() => Object.values(errors.value).some((e) => e !== null))

const submit = useBottomSheetSubmit()

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const value: Record<string, FieldValue> = {}
  for (const f of fields.value) {
    const v = values.value[f.name]
    if (f.type === 'number' && v !== '' && v !== null) {
      value[f.name] = typeof v === 'number' ? v : Number.parseFloat(String(v))
    } else if (f.type === 'checkbox') {
      value[f.name] = Boolean(v)
    } else if (v === '' || v === undefined) {
      value[f.name] = null
    } else {
      value[f.name] = v
    }
  }
  const label = `Formulaire complété (${fields.value.length} champs)`
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'show_form',
    value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'show_form', value, label })
    return
  }
  emit('error', {
    code: res.errorCode ?? 'unknown',
    message: res.errorMessage ?? 'Erreur',
    retriable: res.errorCode === '5xx' || res.errorCode === 'network',
  })
}
</script>

<template>
  <BottomSheetShell
    :title="title"
    :submit-disabled="submitDisabled"
    :in-flight="submit.inFlight.value"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <form class="show-form" @submit.prevent="onSubmit">
      <div v-for="f in fields" :key="f.name" class="show-form__field">
        <label :for="`form-${f.name}`">
          {{ f.label }}
          <span v-if="f.required" aria-hidden="true">*</span>
        </label>
        <input
          v-if="f.type === 'text'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          type="text"
          :maxlength="f.max_length"
          :data-testid="`show-form-${f.name}`"
        />
        <textarea
          v-else-if="f.type === 'textarea'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          :maxlength="f.max_length"
          :data-testid="`show-form-${f.name}`"
        />
        <input
          v-else-if="f.type === 'number'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          type="number"
          :min="f.min"
          :max="f.max"
          :data-testid="`show-form-${f.name}`"
        />
        <input
          v-else-if="f.type === 'date'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          type="date"
          lang="fr-FR"
          :data-testid="`show-form-${f.name}`"
        />
        <select
          v-else-if="f.type === 'select'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          :data-testid="`show-form-${f.name}`"
        >
          <option value="" disabled>—</option>
          <option v-for="o in f.options" :key="o.value" :value="o.value">{{ sanitizeText(o.label) }}</option>
        </select>
        <input
          v-else-if="f.type === 'checkbox'"
          :id="`form-${f.name}`"
          v-model="values[f.name]"
          type="checkbox"
          :data-testid="`show-form-${f.name}`"
        />
        <small v-if="errors[f.name]" class="show-form__error">{{ errors[f.name] }}</small>
      </div>
    </form>
  </BottomSheetShell>
</template>

<style scoped>
.show-form { display: flex; flex-direction: column; gap: var(--space-3, 12px); }
.show-form__field { display: flex; flex-direction: column; gap: var(--space-1, 4px); }
.show-form__field input, .show-form__field textarea, .show-form__field select { padding: var(--space-2, 8px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); font-size: var(--font-size-base, 1rem); }
.show-form__error { color: var(--color-danger-600, #dc2626); font-size: var(--font-size-xs, 0.75rem); }
</style>
