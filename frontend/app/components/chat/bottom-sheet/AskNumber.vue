<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import { eurToXof, xofToEur } from '~/utils/moneyPeg'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_number' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const unit = computed(() => sanitizeText(props.instruction.payload.unit))
const min = computed(() => props.instruction.payload.min)
const max = computed(() => props.instruction.payload.max)
const currency = computed(() => props.instruction.payload.money?.currency)

const raw = ref<string>('')
const submit = useBottomSheetSubmit()

const numericValue = computed(() => {
  const trimmed = raw.value.trim()
  if (trimmed === '' || !/^-?\d+(\.\d+)?$/.test(trimmed)) return null
  return Number.parseFloat(trimmed)
})

const submitDisabled = computed(() => {
  const n = numericValue.value
  if (n === null || Number.isNaN(n)) return true
  if (min.value !== undefined && n < min.value) return true
  if (max.value !== undefined && n > max.value) return true
  return false
})

const conversion = computed<string | null>(() => {
  if (!currency.value || raw.value.trim() === '') return null
  if (!/^-?\d+(\.\d+)?$/.test(raw.value.trim())) return null
  try {
    if (currency.value === 'XOF') {
      return `≈ ${xofToEur(raw.value.trim(), { decimals: 2 })} EUR`
    }
    if (currency.value === 'EUR') {
      return `≈ ${eurToXof(raw.value.trim(), { decimals: 0 })} XOF`
    }
  } catch {
    return null
  }
  return null
})

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const amount = raw.value.trim()
  const labelParts = [amount]
  if (currency.value) labelParts.push(currency.value)
  else if (unit.value) labelParts.push(unit.value)
  const label = labelParts.join(' ')
  const value = currency.value
    ? { amount, currency: currency.value, ...(unit.value ? { unit: unit.value } : {}) }
    : { amount, ...(unit.value ? { unit: unit.value } : {}) }

  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_number',
    value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_number', value, label })
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
    :title="question"
    :submit-disabled="submitDisabled"
    :in-flight="submit.inFlight.value"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <div class="ask-number">
      <label for="ask-number-input" class="sr-only">{{ question }}</label>
      <input
        id="ask-number-input"
        v-model="raw"
        type="text"
        inputmode="decimal"
        class="ask-number__input"
        :min="min"
        :max="max"
        data-testid="ask-number-input"
      />
      <span v-if="currency || unit" class="ask-number__unit">{{ currency ?? unit }}</span>
    </div>
    <p v-if="conversion" class="ask-number__conversion" data-testid="ask-number-conversion">{{ conversion }}</p>
    <p v-if="min !== undefined || max !== undefined" class="ask-number__bounds">
      <span v-if="min !== undefined">min : {{ min }}</span>
      <span v-if="min !== undefined && max !== undefined"> · </span>
      <span v-if="max !== undefined">max : {{ max }}</span>
    </p>
  </BottomSheetShell>
</template>

<style scoped>
.ask-number { display: flex; gap: var(--space-2, 8px); align-items: center; }
.ask-number__input { flex: 1 1 auto; padding: var(--space-3, 12px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); font-size: var(--font-size-lg, 1.125rem); }
.ask-number__unit { color: var(--color-text-muted, #64748b); font-weight: var(--font-weight-medium, 500); }
.ask-number__conversion { color: var(--color-text-muted, #64748b); font-size: var(--font-size-sm, 0.875rem); margin: var(--space-2, 8px) 0 0; }
.ask-number__bounds { color: var(--color-text-muted, #64748b); font-size: var(--font-size-xs, 0.75rem); margin: var(--space-1, 4px) 0 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
