<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_qcu' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const allowOther = computed(() => Boolean(props.instruction.payload.allow_other))
const options = computed(() =>
  props.instruction.payload.options.map((o) => ({
    value: o.value,
    label: sanitizeText(o.label),
    description: o.description ? sanitizeText(o.description) : undefined,
  })),
)

const selected = ref<string | null>(null)
const otherText = ref<string>('')
const submit = useBottomSheetSubmit()

const isOtherSelected = computed(() => selected.value === '__other__')
const submitDisabled = computed(() => {
  if (selected.value === null) return true
  if (isOtherSelected.value && otherText.value.trim().length === 0) return true
  return false
})

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const value = isOtherSelected.value ? 'other' : selected.value!
  const label = isOtherSelected.value
    ? otherText.value.trim()
    : (options.value.find((o) => o.value === selected.value)?.label ?? value)

  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_qcu',
    value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_qcu', value, label })
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
    :error-message="submit.inFlight.value ? null : null"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <fieldset class="ask-qcu">
      <legend class="sr-only">{{ question }}</legend>
      <label v-for="opt in options" :key="opt.value" class="ask-qcu__opt">
        <input
          v-model="selected"
          type="radio"
          name="ask_qcu"
          :value="opt.value"
          :data-testid="`ask-qcu-opt-${opt.value}`"
        />
        <span>
          <strong>{{ opt.label }}</strong>
          <small v-if="opt.description">{{ opt.description }}</small>
        </span>
      </label>
      <label v-if="allowOther" class="ask-qcu__opt">
        <input
          v-model="selected"
          type="radio"
          name="ask_qcu"
          value="__other__"
          data-testid="ask-qcu-opt-other"
        />
        <span>Autre</span>
      </label>
      <div v-if="isOtherSelected" class="ask-qcu__other">
        <label for="ask-qcu-other-input" class="sr-only">Précisez</label>
        <input
          id="ask-qcu-other-input"
          v-model="otherText"
          type="text"
          class="ask-qcu__other-input"
          placeholder="Précisez…"
          data-testid="ask-qcu-other-input"
        />
      </div>
    </fieldset>
  </BottomSheetShell>
</template>

<style scoped>
.ask-qcu { display: flex; flex-direction: column; gap: var(--space-2, 8px); border: 0; padding: 0; margin: 0; }
.ask-qcu__opt { display: flex; gap: var(--space-3, 12px); align-items: flex-start; padding: var(--space-3, 12px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); cursor: pointer; }
.ask-qcu__opt input { margin-top: 0.25rem; }
.ask-qcu__opt small { display: block; color: var(--color-text-muted, #64748b); font-size: var(--font-size-sm, 0.875rem); }
.ask-qcu__other { padding: var(--space-2, 8px) 0 0 var(--space-6, 24px); }
.ask-qcu__other-input { width: 100%; padding: var(--space-2, 8px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
