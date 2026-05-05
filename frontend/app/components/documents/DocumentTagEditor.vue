<!--
  F50 T062 — DocumentTagEditor (chips inline éditables, ARIA).
-->
<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  modelValue: string[]
  documentId: string
  maxLength?: number
}

const props = withDefaults(defineProps<Props>(), { maxLength: 40 })
const emit = defineEmits<{
  (e: 'update:modelValue', tags: string[]): void
  (e: 'commit', payload: { id: string; tags: string[] }): void
}>()

const draft = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function add(): void {
  const v = draft.value.trim()
  if (!v) return
  if (v.length > props.maxLength) return
  if (props.modelValue.includes(v)) {
    draft.value = ''
    return
  }
  const next = [...props.modelValue, v]
  emit('update:modelValue', next)
  emit('commit', { id: props.documentId, tags: next })
  draft.value = ''
}

function remove(tag: string): void {
  const next = props.modelValue.filter((t) => t !== tag)
  emit('update:modelValue', next)
  emit('commit', { id: props.documentId, tags: next })
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    add()
  } else if (
    e.key === 'Backspace' &&
    draft.value === '' &&
    props.modelValue.length > 0
  ) {
    remove(props.modelValue[props.modelValue.length - 1]!)
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-1" role="group" aria-label="Tags du document">
    <span
      v-for="tag in modelValue"
      :key="tag"
      class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"
    >
      {{ tag }}
      <button
        type="button"
        class="text-emerald-700 hover:text-emerald-900"
        :aria-label="`Retirer le tag ${tag}`"
        @click="remove(tag)"
      >×</button>
    </span>
    <input
      ref="inputRef"
      v-model="draft"
      type="text"
      placeholder="Ajouter un tag…"
      :maxlength="maxLength"
      class="min-w-[8ch] rounded-md border border-transparent bg-transparent px-1 py-0.5 text-xs focus:border-gray-300 focus:outline-none"
      aria-label="Ajouter un tag"
      @keydown="onKeydown"
      @blur="add"
    >
  </div>
</template>
