<script setup lang="ts">
/**
 * MessageBubbleUser — bulle utilisateur (droite, fond brand-50).
 * F41 / US1 (T014). Timestamp en hover (title attribute).
 */
import { computed } from 'vue'

interface Props {
  content: string
  createdAt: string
}

const props = defineProps<Props>()

const timeLabel = computed(() => {
  try {
    return new Date(props.createdAt).toLocaleString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
})

const fullDate = computed(() => {
  try {
    return new Date(props.createdAt).toLocaleString('fr-FR')
  } catch {
    return props.createdAt
  }
})
</script>

<template>
  <div class="chat-bubble-user" role="listitem">
    <div class="chat-bubble-user__bubble" :title="fullDate">
      <p class="chat-bubble-user__content">{{ content }}</p>
    </div>
    <span class="chat-bubble-user__time">{{ timeLabel }}</span>
  </div>
</template>

<style scoped>
.chat-bubble-user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
  margin: 0.5rem 0;
}
.chat-bubble-user__bubble {
  background: rgb(var(--color-brand-50, 239 246 255));
  color: rgb(var(--color-brand-900, 30 58 138));
  border: 1px solid rgb(var(--color-brand-100, 219 234 254));
  border-radius: 16px 16px 4px 16px;
  padding: 0.625rem 0.875rem;
  max-width: min(80ch, 75%);
  word-wrap: break-word;
}
.chat-bubble-user__content {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.55;
}
.chat-bubble-user__time {
  font-size: 0.75rem;
  color: rgb(var(--color-fg-muted, 107 114 128));
  opacity: 0;
  transition: opacity 0.15s;
}
.chat-bubble-user:hover .chat-bubble-user__time {
  opacity: 1;
}
</style>
