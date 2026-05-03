<script setup lang="ts">
import { computed, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_rating' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const scale = computed(() => props.instruction.payload.scale)
const style = computed(() => props.instruction.payload.style ?? 'numeric')
const value = ref<number | null>(null)
const submit = useBottomSheetSubmit()

const submitDisabled = computed(() => value.value === null)
const items = computed(() => Array.from({ length: scale.value }, (_, i) => i + 1))

function onKeydown(e: KeyboardEvent): void {
  if (/^\d$/.test(e.key)) {
    const digit = Number.parseInt(e.key, 10)
    if (digit === 0 && scale.value === 10) {
      value.value = 10
      e.preventDefault()
      return
    }
    if (digit >= 1 && digit <= scale.value) {
      value.value = digit
      e.preventDefault()
      return
    }
  }
  if (e.key === 'Enter' && !submitDisabled.value) {
    e.preventDefault()
    void onSubmit()
  }
}

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  const v = value.value!
  const label = `${v}/${scale.value}`
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'ask_rating',
    value: v,
    label,
  })
  if (res.ok || res.errorCode === '409') {
    emit('submit', { tool: 'ask_rating', value: v, label })
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
    <div
      class="ask-rating"
      role="radiogroup"
      :aria-label="question"
      tabindex="0"
      data-testid="ask-rating-group"
      @keydown="onKeydown"
    >
      <button
        v-for="n in items"
        :key="n"
        type="button"
        class="ask-rating__item"
        :class="{ 'ask-rating__item--active': value !== null && n <= value }"
        :aria-checked="value === n"
        role="radio"
        :data-testid="`ask-rating-${n}`"
        @click="value = n"
      >
        <template v-if="style === 'stars'">★</template>
        <template v-else>{{ n }}</template>
      </button>
    </div>
    <p v-if="value !== null" class="ask-rating__current">Note : {{ value }} / {{ scale }}</p>
  </BottomSheetShell>
</template>

<style scoped>
.ask-rating { display: flex; gap: var(--space-2, 8px); flex-wrap: wrap; }
.ask-rating__item { min-width: 44px; min-height: 44px; border: 1px solid var(--color-border, #e2e8f0); background: var(--color-surface, #fff); border-radius: var(--radius-md, 8px); font-size: var(--font-size-lg, 1.125rem); cursor: pointer; }
.ask-rating__item--active { background: var(--color-brand-500, #16a34a); color: #fff; border-color: var(--color-brand-500, #16a34a); }
.ask-rating__current { margin: var(--space-2, 8px) 0 0; color: var(--color-text-muted, #64748b); }
</style>
