<script setup lang="ts">
/**
 * ChatHeader — titre du thread + bouton Nouveau chat + slot MemoryBadge.
 * F41 / US4 (T036) + US9 (T055).
 */
import MemoryBadge from './MemoryBadge.vue'

interface Props {
  title: string
  threadId: string
}

defineProps<Props>()
const emit = defineEmits<{
  (e: 'new-chat'): void
}>()
</script>

<template>
  <div class="chat-header">
    <h1 class="chat-header__title">{{ title }}</h1>
    <div class="chat-header__actions">
      <MemoryBadge :thread-id="threadId" />
      <button
        type="button"
        class="chat-header__new"
        aria-label="Nouvelle conversation"
        @click="emit('new-chat')"
      >
        Nouveau chat
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}
.chat-header__title {
  flex: 1;
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgb(var(--color-fg-strong, 17 24 39));
}
.chat-header__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.chat-header__new {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  border: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  color: rgb(var(--color-fg-strong, 17 24 39));
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.15s;
}
.chat-header__new:hover {
  background: rgb(var(--color-bg-muted, 243 244 246));
}
.chat-header__new:focus-visible {
  outline: 2px solid rgb(var(--color-brand-500, 59 130 246));
  outline-offset: 2px;
}
</style>
