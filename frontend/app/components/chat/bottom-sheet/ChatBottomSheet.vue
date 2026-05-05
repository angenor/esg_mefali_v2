<script setup lang="ts">
/**
 * ChatBottomSheet — orchestrateur racine du moteur F39.
 *
 * Responsabilités :
 *  - Souscrit à `current` du store éphémère.
 *  - Monte dynamiquement le wrapper correspondant à `current.tool`.
 *  - Émet les events de contrat (`submit`, `dismiss-for-freetext`, `cancel`, `opened`,
 *    `closed`, `error`) — cf. orchestrator-events.md.
 *  - Mesure NFR-001 : `performance.now()` autour de l'ouverture (event `opened`).
 *
 * Le composable `useChatBottomSheet` est l'API publique pour les pages — ce composant
 * doit être monté dans le layout chat (F38) et reste invisible tant que `current === null`.
 */
import { computed, defineAsyncComponent, ref, watch, type Component } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatBottomSheetStore } from '~/stores/chatBottomSheet'
import { FREETEXT_EVENT_NAME, useChatBottomSheet } from '~/composables/useChatBottomSheet'
import type { ToolName, ToolResponse } from '~/types/tools/contracts'

const emit = defineEmits<{
  (e: 'submit', value: ToolResponse): void
  (e: 'dismiss-for-freetext', value: { tool: ToolName; message_id: string }): void
  (e: 'cancel', value: { tool: ToolName; message_id: string }): void
  (e: 'opened', value: { tool: ToolName; message_id: string; durationMs: number }): void
  (e: 'closed', value: { tool: ToolName; reason: 'submit' | 'freetext' | 'cancel' }): void
  (e: 'error', value: { code: string; message: string; retriable: boolean }): void
}>()

const store = useChatBottomSheetStore()
const { current } = storeToRefs(store)
const sheet = useChatBottomSheet()

const wrapperMap: Record<ToolName, () => Promise<Component>> = {
  ask_yes_no: () => import('./AskYesNo.vue').then((m) => m.default),
  ask_qcu: () => import('./AskQcu.vue').then((m) => m.default),
  ask_qcm: () => import('./AskQcm.vue').then((m) => m.default),
  ask_select: () => import('./AskSelect.vue').then((m) => m.default),
  ask_number: () => import('./AskNumber.vue').then((m) => m.default),
  ask_date: () => import('./AskDate.vue').then((m) => m.default),
  ask_date_range: () => import('./AskDateRange.vue').then((m) => m.default),
  ask_rating: () => import('./AskRating.vue').then((m) => m.default),
  ask_file_upload: () => import('./AskFileUpload.vue').then((m) => m.default),
  show_form: () => import('./ShowForm.vue').then((m) => m.default),
  show_summary_card: () => import('./ShowSummaryCard.vue').then((m) => m.default),
}

const activeWrapper = computed<Component | null>(() => {
  const inst = current.value
  if (!inst) return null
  return defineAsyncComponent(wrapperMap[inst.tool])
})

const openedAt = ref<number | null>(null)

watch(current, (next, prev) => {
  if (next && !prev) {
    openedAt.value = typeof performance !== 'undefined' ? performance.now() : Date.now()
  } else if (!next) {
    openedAt.value = null
  }
})

function onWrapperSubmit(value: ToolResponse): void {
  emit('submit', value)
  const inst = current.value
  if (!inst) return
  emit('closed', { tool: inst.tool, reason: 'submit' })
  void sheet.close('submit')
}

function onWrapperFreeText(): void {
  const inst = current.value
  if (!inst) return
  emit('dismiss-for-freetext', { tool: inst.tool, message_id: inst.context.message_id })
  emit('closed', { tool: inst.tool, reason: 'freetext' })
  void sheet.close('freetext')
}

function onWrapperCancel(value?: ToolResponse): void {
  const inst = current.value
  if (!inst) return
  if (value) emit('submit', value)
  emit('cancel', { tool: inst.tool, message_id: inst.context.message_id })
  emit('closed', { tool: inst.tool, reason: 'cancel' })
  void sheet.close('cancel')
}

function onWrapperOpened(): void {
  const inst = current.value
  if (!inst) return
  const duration = openedAt.value !== null && typeof performance !== 'undefined' ? performance.now() - openedAt.value : 0
  emit('opened', { tool: inst.tool, message_id: inst.context.message_id, durationMs: duration })
}

function onWrapperError(payload: { code: string; message: string; retriable: boolean }): void {
  emit('error', payload)
}

defineExpose({
  // Pour les tests / l'intégration : permet d'ouvrir un sheet sans passer par le SSE.
  open: sheet.open,
  close: sheet.close,
  rebuildFromThread: sheet.rebuildFromThread,
  current: current,
})

// Permet à un composant parent (input chat F38) d'écouter le freetext via DOM event :
// `window.addEventListener(FREETEXT_EVENT_NAME, …)` exposé dans useChatBottomSheet.
defineOptions({ inheritAttrs: false })
void FREETEXT_EVENT_NAME // évite le warning « unused import » côté ESLint.
</script>

<template>
  <Teleport to="body">
    <component
      :is="activeWrapper"
      v-if="activeWrapper && current"
      :instruction="current"
      @submit="onWrapperSubmit"
      @dismiss-for-freetext="onWrapperFreeText"
      @cancel="onWrapperCancel"
      @opened="onWrapperOpened"
      @error="onWrapperError"
    />
  </Teleport>
</template>
