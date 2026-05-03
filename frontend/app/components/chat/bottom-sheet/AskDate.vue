<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_date' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const value = ref<string>('')
const submit = useBottomSheetSubmit()

const submitDisabled = computed(() => !/^\d{4}-\d{2}-\d{2}$/.test(value.value))

const formatted = computed(() => {
  if (!value.value) return ''
  try {
    return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date(value.value))
  } catch {
    return value.value
  }
})

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const label = formatted.value || value.value
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_date',
    value: value.value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_date', value: value.value, label })
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
    <label class="sr-only" for="ask-date-input">{{ question }}</label>
    <input
      id="ask-date-input"
      v-model="value"
      type="date"
      lang="fr-FR"
      class="ask-date__input"
      :aria-label="question"
      :min="instruction.payload.min"
      :max="instruction.payload.max"
      data-testid="ask-date-input"
    />
    <p v-if="formatted" class="ask-date__preview">{{ formatted }}</p>
  </BottomSheetShell>
</template>

<style scoped>
.ask-date__input { width: 100%; padding: var(--space-3, 12px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); font-size: var(--font-size-base, 1rem); }
.ask-date__preview { color: var(--color-text-muted, #64748b); margin: var(--space-2, 8px) 0 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
