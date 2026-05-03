<script setup lang="ts">
import { computed } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_yes_no' }>
}
const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const yesLabel = computed(() => sanitizeText(props.instruction.payload.yes_label) || 'Oui')
const noLabel = computed(() => sanitizeText(props.instruction.payload.no_label) || 'Non')
const question = computed(() => sanitizeText(props.instruction.payload.question))

const submit = useBottomSheetSubmit()

async function choose(value: boolean, label: string): Promise<void> {
  if (submit.inFlight.value) return
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_yes_no',
    value,
    label,
  })
  if (res.ok) {
    emit('submit', { tool: 'ask_yes_no', value, label })
    return
  }
  if (res.errorCode === '409') {
    // Race : le tool est déjà résolu — fermeture silencieuse comme un submit.
    emit('submit', { tool: 'ask_yes_no', value, label })
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
    :in-flight="submit.inFlight.value"
    :hide-footer="true"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <div class="ask-yes-no">
      <button
        type="button"
        class="ask-yes-no__btn ask-yes-no__btn--yes"
        data-testid="ask-yes-no-yes"
        :disabled="submit.inFlight.value"
        @click="choose(true, yesLabel)"
      >
        {{ yesLabel }}
      </button>
      <button
        type="button"
        class="ask-yes-no__btn ask-yes-no__btn--no"
        data-testid="ask-yes-no-no"
        :disabled="submit.inFlight.value"
        @click="choose(false, noLabel)"
      >
        {{ noLabel }}
      </button>
    </div>
  </BottomSheetShell>
</template>

<style scoped>
.ask-yes-no {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3, 12px);
}
.ask-yes-no__btn {
  min-height: 56px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-surface, #fff);
  font-size: var(--font-size-base, 1rem);
  font-weight: var(--font-weight-medium, 500);
  cursor: pointer;
}
.ask-yes-no__btn:hover:not(:disabled) {
  background: var(--color-surface-2, #f1f5f9);
}
.ask-yes-no__btn--yes {
  border-color: var(--color-brand-400, #4ade80);
  color: var(--color-brand-700, #15803d);
}
.ask-yes-no__btn--no {
  color: var(--color-text-muted, #64748b);
}
.ask-yes-no__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
