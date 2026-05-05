<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_qcm' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const options = computed(() =>
  props.instruction.payload.options.map((o) => ({ value: o.value, label: sanitizeText(o.label) })),
)
const minSelect = computed(() => props.instruction.payload.min_select ?? 0)
const maxSelect = computed(() => props.instruction.payload.max_select ?? options.value.length)

const selected = ref<string[]>([])
const submit = useBottomSheetSubmit()

const counterLabel = computed(() => {
  const n = selected.value.length
  return `${n} sur ${options.value.length} (min ${minSelect.value}, max ${maxSelect.value})`
})

const submitDisabled = computed(() => {
  const n = selected.value.length
  return n < minSelect.value || n > maxSelect.value
})

function toggle(value: string, checked: boolean): void {
  if (checked) {
    if (selected.value.length >= maxSelect.value) return
    if (!selected.value.includes(value)) selected.value = [...selected.value, value]
  } else {
    selected.value = selected.value.filter((v) => v !== value)
  }
}

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const labels = options.value.filter((o) => selected.value.includes(o.value)).map((o) => o.label)
  const label = labels.length <= 3 ? labels.join(', ') : `${labels.length} options`
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_qcm',
    value: selected.value,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_qcm', value: selected.value, label })
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
    :description="counterLabel"
    :submit-disabled="submitDisabled"
    :in-flight="submit.inFlight.value"
    @submit="onSubmit"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <fieldset class="ask-qcm">
      <legend class="sr-only">{{ question }}</legend>
      <label v-for="opt in options" :key="opt.value" class="ask-qcm__opt">
        <input
          type="checkbox"
          :checked="selected.includes(opt.value)"
          :data-testid="`ask-qcm-opt-${opt.value}`"
          @change="toggle(opt.value, ($event.target as HTMLInputElement).checked)"
        />
        <span>{{ opt.label }}</span>
      </label>
    </fieldset>
  </BottomSheetShell>
</template>

<style scoped>
.ask-qcm { display: flex; flex-direction: column; gap: var(--space-2, 8px); border: 0; padding: 0; margin: 0; }
.ask-qcm__opt { display: flex; gap: var(--space-3, 12px); align-items: center; padding: var(--space-3, 12px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); cursor: pointer; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
