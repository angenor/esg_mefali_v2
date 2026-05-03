<script setup lang="ts">
import { computed } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'show_summary_card' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'cancel', value: ToolResponse): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const title = computed(() => sanitizeText(props.instruction.payload.title))
const okLabel = computed(() => sanitizeText(props.instruction.payload.ok_label) || 'Valider')
const editLabel = computed(() => sanitizeText(props.instruction.payload.edit_label) || 'Corriger')
const cancelLabel = computed(() => sanitizeText(props.instruction.payload.cancel_label) || 'Annuler')

const rows = computed(() =>
  props.instruction.payload.rows.map((r) => ({
    label: sanitizeText(r.label),
    value: sanitizeText(r.value),
    sourceLabel: r.source_label ? sanitizeText(r.source_label) : undefined,
    sourceId: r.source_id,
  })),
)

const submit = useBottomSheetSubmit()

async function postAction(action: 'validate' | 'correct' | 'cancel', label: string): Promise<void> {
  const res = await submit.submit({
    threadId: props.instruction.context.thread_id,
    inResponseToMessageId: props.instruction.context.message_id,
    tool: 'show_summary_card',
    value: { action },
    label,
  })
  const value: ToolResponse = { tool: 'show_summary_card', value: { action }, label }
  if (res.ok || res.errorCode === '409') {
    if (action === 'cancel') emit('cancel', value)
    else if (action === 'correct') {
      emit('submit', value)
      emit('dismiss-for-freetext')
    } else {
      emit('submit', value)
    }
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
    :hide-footer="true"
    :hide-free-text="true"
    :in-flight="submit.inFlight.value"
    @opened="emit('opened')"
    @dismiss-for-freetext="emit('dismiss-for-freetext')"
  >
    <table class="show-summary">
      <tbody>
        <tr v-for="r in rows" :key="r.label">
          <th scope="row">{{ r.label }}</th>
          <td>
            {{ r.value }}
            <span v-if="r.sourceLabel" class="show-summary__source" :title="r.sourceId">
              {{ r.sourceLabel }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
    <div class="show-summary__actions">
      <button
        type="button"
        class="show-summary__btn show-summary__btn--cancel"
        :disabled="submit.inFlight.value"
        data-testid="show-summary-cancel"
        @click="postAction('cancel', 'Récap annulé')"
      >
        {{ cancelLabel }}
      </button>
      <button
        type="button"
        class="show-summary__btn show-summary__btn--edit"
        :disabled="submit.inFlight.value"
        data-testid="show-summary-edit"
        @click="postAction('correct', 'Correction demandée')"
      >
        {{ editLabel }}
      </button>
      <button
        type="button"
        class="show-summary__btn show-summary__btn--ok"
        :disabled="submit.inFlight.value"
        data-testid="show-summary-ok"
        @click="postAction('validate', 'Récap validé')"
      >
        {{ okLabel }}
      </button>
    </div>
  </BottomSheetShell>
</template>

<style scoped>
.show-summary { width: 100%; border-collapse: collapse; }
.show-summary th, .show-summary td { padding: var(--space-2, 8px); border-bottom: 1px solid var(--color-border, #e2e8f0); text-align: left; vertical-align: top; }
.show-summary th { color: var(--color-text-muted, #64748b); font-weight: var(--font-weight-medium, 500); width: 40%; }
.show-summary__source { display: inline-block; margin-left: var(--space-2, 8px); padding: 2px 6px; border-radius: var(--radius-sm, 4px); background: var(--color-surface-2, #f1f5f9); font-size: var(--font-size-xs, 0.75rem); color: var(--color-text-muted, #64748b); }
.show-summary__actions { display: flex; gap: var(--space-2, 8px); justify-content: flex-end; padding-top: var(--space-3, 12px); position: sticky; bottom: 0; background: var(--color-surface, #fff); }
.show-summary__btn { padding: var(--space-2, 8px) var(--space-4, 16px); border-radius: var(--radius-md, 8px); border: 1px solid var(--color-border, #e2e8f0); background: var(--color-surface, #fff); cursor: pointer; min-height: 44px; }
.show-summary__btn--ok { background: var(--color-brand-500, #16a34a); color: #fff; border-color: var(--color-brand-500, #16a34a); }
.show-summary__btn--cancel { color: var(--color-danger-600, #dc2626); }
.show-summary__btn:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
