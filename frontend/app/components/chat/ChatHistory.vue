<script setup lang="ts">
/**
 * ChatHistory — liste des messages avec scroll-pinning.
 *
 * F41 / US1 (T017). Itère messages, intercale TypingIndicator quand le
 * streaming est actif sans premier token, branche les events `cite-click` et
 * `retry` venant des bulles.
 */
import { ref } from 'vue'
import type { ChatMessage } from '~/types/chat'
import { useChatScroll } from '~/composables/useChatScroll'
import MessageBubbleUser from './MessageBubbleUser.vue'
import MessageBubbleAssistant from './MessageBubbleAssistant.vue'
import TypingIndicator from './TypingIndicator.vue'

interface Props {
  messages: ChatMessage[]
  showTyping?: boolean
}

withDefaults(defineProps<Props>(), { showTyping: false })

const emit = defineEmits<{
  (e: 'retry', messageId: string): void
  (e: 'cite-click', sourceId: string): void
}>()

const containerRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)
useChatScroll(containerRef, contentRef)
</script>

<template>
  <div ref="containerRef" class="chat-history" tabindex="-1">
    <div ref="contentRef" class="chat-history__inner" role="list" aria-label="Historique de conversation">
      <template v-for="msg in messages" :key="msg.id">
        <MessageBubbleUser
          v-if="msg.role === 'user'"
          :content="msg.content"
          :created-at="msg.createdAt"
        />
        <MessageBubbleAssistant
          v-else-if="msg.role === 'assistant'"
          :message-id="msg.id"
          :content="msg.content"
          :payload="msg.payload"
          :streaming="msg.streaming"
          :has-mutation="msg.hasMutation"
          @retry="(id: string) => emit('retry', id)"
          @cite-click="(s: string) => emit('cite-click', s)"
        />
      </template>
      <TypingIndicator v-if="showTyping" />
    </div>
  </div>
</template>

<style scoped>
.chat-history {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1rem;
  scroll-behavior: smooth;
}
@media (prefers-reduced-motion: reduce) {
  .chat-history { scroll-behavior: auto; }
}
.chat-history__inner {
  display: flex;
  flex-direction: column;
  max-width: 920px;
  margin: 0 auto;
  width: 100%;
}
</style>
