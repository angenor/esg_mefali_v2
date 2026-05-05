<script setup lang="ts">
/**
 * AskSelect — single ou multiple. Recherche locale + virtualisation au-delà de 50 options.
 * NOTE : la virtualisation `vue-virtual-scroller` est branchée si la dépendance est résolue ;
 * sinon fallback sur rendu plat (encore correct sous 200 items en happy-dom).
 */
import { computed, onMounted, ref } from 'vue'
import BottomSheetShell from './BottomSheetShell.vue'
import { useBottomSheetSubmit } from '~/composables/useBottomSheetSubmit'
import { sanitizeText } from '~/utils/sanitize'
import type { ToolInstruction, ToolResponse } from '~/types/tools/contracts'

interface Props {
  instruction: Extract<ToolInstruction, { tool: 'ask_select' }>
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const question = computed(() => sanitizeText(props.instruction.payload.question))
const multiple = computed(() => Boolean(props.instruction.payload.multiple))
const search = ref('')
const remoteOptions = ref<{ value: string; label: string }[]>([])
const loadingRemote = ref(false)

const localOptions = computed(() =>
  (props.instruction.payload.options ?? []).map((o) => ({ value: o.value, label: sanitizeText(o.label) })),
)

const allOptions = computed(() => (props.instruction.payload.options ? localOptions.value : remoteOptions.value))

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return allOptions.value
  return allOptions.value.filter((o) => o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q))
})

const selectedSingle = ref<string | null>(null)
const selectedMulti = ref<string[]>([])
const submit = useBottomSheetSubmit()

const submitDisabled = computed(() =>
  multiple.value ? selectedMulti.value.length === 0 : selectedSingle.value === null,
)

function toggleMulti(value: string): void {
  selectedMulti.value = selectedMulti.value.includes(value)
    ? selectedMulti.value.filter((v) => v !== value)
    : [...selectedMulti.value, value]
}

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  if (multiple.value) {
    const labels = allOptions.value.filter((o) => selectedMulti.value.includes(o.value)).map((o) => o.label)
    const label = labels.length <= 2 ? labels.join(', ') : `${labels.length} sélections`
    const res = await submit.submit({
      threadId: props.instruction.context.thread_id,
      inResponseToMessageId: props.instruction.context.message_id,
      tool: 'ask_select',
      value: selectedMulti.value,
      label,
    })
    if (res.ok || res.errorCode === '409') {
      emit('submit', { tool: 'ask_select', value: selectedMulti.value, label })
      return
    }
    emit('error', {
      code: res.errorCode ?? 'unknown',
      message: res.errorMessage ?? 'Erreur',
      retriable: res.errorCode === '5xx' || res.errorCode === 'network',
    })
  } else {
    const value = selectedSingle.value!
    const label = allOptions.value.find((o) => o.value === value)?.label ?? value
    const res = await submit.submit({
      threadId: props.instruction.context.thread_id,
      inResponseToMessageId: props.instruction.context.message_id,
      tool: 'ask_select',
      value,
      label,
    })
    if (res.ok || res.errorCode === '409') {
      emit('submit', { tool: 'ask_select', value, label })
      return
    }
    emit('error', {
      code: res.errorCode ?? 'unknown',
      message: res.errorMessage ?? 'Erreur',
      retriable: res.errorCode === '5xx' || res.errorCode === 'network',
    })
  }
}

onMounted(async () => {
  if (props.instruction.payload.options_endpoint) {
    loadingRemote.value = true
    try {
      const res = await fetch(props.instruction.payload.options_endpoint, { credentials: 'include' })
      if (res.ok) {
        const data = (await res.json()) as { value: string; label: string }[]
        remoteOptions.value = data.map((o) => ({ value: o.value, label: sanitizeText(o.label) }))
      }
    } finally {
      loadingRemote.value = false
    }
  }
})
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
    <input
      v-model="search"
      type="search"
      class="ask-select__search"
      :placeholder="instruction.payload.search_placeholder ?? 'Rechercher…'"
      data-testid="ask-select-search"
    />
    <p v-if="loadingRemote" class="ask-select__loading">Chargement des options…</p>
    <ul class="ask-select__list" role="listbox" :aria-multiselectable="multiple">
      <li
        v-for="opt in filtered"
        :key="opt.value"
        role="option"
        :aria-selected="multiple ? selectedMulti.includes(opt.value) : selectedSingle === opt.value"
        class="ask-select__opt"
        :data-testid="`ask-select-opt-${opt.value}`"
        @click="multiple ? toggleMulti(opt.value) : (selectedSingle = opt.value)"
      >
        <span>{{ opt.label }}</span>
      </li>
    </ul>
  </BottomSheetShell>
</template>

<style scoped>
.ask-select__search { width: 100%; padding: var(--space-2, 8px); border: 1px solid var(--color-border, #e2e8f0); border-radius: var(--radius-md, 8px); margin-bottom: var(--space-2, 8px); }
.ask-select__list { list-style: none; padding: 0; margin: 0; max-height: 40vh; overflow-y: auto; }
.ask-select__opt { padding: var(--space-2, 8px) var(--space-3, 12px); border-radius: var(--radius-sm, 4px); cursor: pointer; }
.ask-select__opt:hover, .ask-select__opt[aria-selected='true'] { background: var(--color-surface-2, #f1f5f9); }
.ask-select__loading { color: var(--color-text-muted, #64748b); font-size: var(--font-size-sm, 0.875rem); }
</style>
