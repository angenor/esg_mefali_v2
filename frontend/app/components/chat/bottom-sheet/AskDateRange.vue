<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_date_range' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const start = ref<string>('')
const end = ref<string>('')
const submit = useBottomSheetSubmit()

const validRange = computed(() => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start.value) || !/^\d{4}-\d{2}-\d{2}$/.test(end.value)) return false
  if (new Date(end.value).getTime() < new Date(start.value).getTime()) return false
  const span = props.instruction.payload.max_span_days
  if (span !== undefined) {
    const diff = (new Date(end.value).getTime() - new Date(start.value).getTime()) / 86_400_000
    if (diff > span) return false
  }
  return true
})

async function onSubmit(): Promise<void> {
  if (!validRange.value) return
  const label = `${start.value} → ${end.value}`
  const value = { start: start.value, end: end.value }
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_date_range',
    value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_date_range', value, label })
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
    :submit-disabled="!validRange"
    :in-flight="submit.inFlight.value"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <div class="ask-date-range">
      <label class="ask-date-range__field">
        <span>Début</span>
        <input
          v-model="start"
          type="date"
          lang="fr-FR"
          :min="instruction.payload.min"
          :max="instruction.payload.max"
          data-testid="ask-date-range-start"
        />
      </label>
      <label class="ask-date-range__field">
        <span>Fin</span>
        <input
          v-model="end"
          type="date"
          lang="fr-FR"
          :min="start || instruction.payload.min"
          :max="instruction.payload.max"
          data-testid="ask-date-range-end"
        />
      </label>
    </div>
  </BottomSheetShell>
</template>

<style scoped>
.ask-date-range { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3, 12px); }
.ask-date-range__field { display: flex; flex-direction: column; gap: var(--space-1, 4px); }
.ask-date-range__field input { padding: var(--space-2, 8px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); }
</style>
