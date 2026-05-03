<script setup lang="ts">
/**
 * /chat/[thread_id] — page principale du chat.
 *
 * F41 / US1 (T021, T022) + US3 (T031) + US4 (T037) + US6 (T043) + US8 (T051).
 * Compose ChatLayout avec ThreadList + ChatHeader + ChatHistory + MessageInput.
 */
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useChatStore } from '~/stores/chat'
import { useChatOnboarding } from '~/composables/useChatOnboarding'
import { useChatToolBridge } from '~/composables/useChatToolBridge'
import ChatLayout from '~/components/chat/ChatLayout.vue'
import ChatHeader from '~/components/chat/ChatHeader.vue'
import ChatHistory from '~/components/chat/ChatHistory.vue'
import MessageInput from '~/components/chat/MessageInput.vue'
import ThreadList from '~/components/chat/ThreadList.vue'
import QuickReplies from '~/components/chat/QuickReplies.vue'
import ChatBottomSheet from '~/components/chat/bottom-sheet/ChatBottomSheet.vue'
import type { ToolResponse } from '~/types/tools/contracts'

definePageMeta({ middleware: ['pme-only'], layout: false })

const route = useRoute()
const router = useRouter()
const store = useChatStore()
const { currentMessages, isStreaming, streamingPhase } = storeToRefs(store)

const threadId = computed(() => String(route.params.thread_id ?? ''))

const showTyping = computed(() => {
  if (!isStreaming.value) return false
  const last = currentMessages.value[currentMessages.value.length - 1]
  if (!last || last.role !== 'assistant') return true
  return last.streaming === true && (!last.content || last.content.length === 0)
})

const lastAssistant = computed(() => {
  for (let i = currentMessages.value.length - 1; i >= 0; i -= 1) {
    const m = currentMessages.value[i]
    if (m && m.role === 'assistant' && !m.streaming) return m
  }
  return null
})

const showQuickReplies = computed(() => {
  if (isStreaming.value) return false
  return lastAssistant.value !== null && lastAssistant.value.payload?.kind !== 'error'
})

const onboarding = useChatOnboarding()
useChatToolBridge()

onMounted(async () => {
  if (store.threads.length === 0) await store.loadThreads()
  if (threadId.value) await store.selectThread(threadId.value)
  await onboarding.maybeStart()
})

watch(threadId, async (id) => {
  if (id) await store.selectThread(id)
})

function onSubmit(content: string): void {
  void store.sendMessage(content)
}

function onSelectThread(id: string): void {
  void router.push(`/chat/${id}`)
}

async function onNewChat(): Promise<void> {
  const t = await store.newThread()
  if (t) await router.push(`/chat/${t.id}`)
}

function onRetry(messageId: string): void {
  store.retry(messageId)
}

function onPickQuickReply(text: string): void {
  void store.sendMessage(text)
}

function onSheetSubmit(value: ToolResponse): void {
  void store.sendMessage(value.label || `[${value.tool}]`, { payload: value })
}
</script>

<template>
  <ChatLayout>
    <template #sidebar>
      <ThreadList
        :threads="store.threads"
        :current-id="threadId"
        @select="onSelectThread"
        @new-chat="onNewChat"
      />
    </template>
    <template #header>
      <ChatHeader
        :title="store.currentThread?.title ?? 'Nouveau chat'"
        :thread-id="threadId"
        @new-chat="onNewChat"
      />
    </template>
    <template #history>
      <ChatHistory
        :messages="currentMessages"
        :show-typing="showTyping"
        @retry="onRetry"
      />
      <QuickReplies
        v-if="showQuickReplies"
        :suggestions="['Continuer', 'Reformuler', 'Donne un exemple']"
        @pick="onPickQuickReply"
      />
    </template>
    <template #input>
      <MessageInput :disabled="streamingPhase === 'awaiting_sheet'" @submit="onSubmit" />
    </template>
  </ChatLayout>
  <ChatBottomSheet @submit="onSheetSubmit" />
</template>
