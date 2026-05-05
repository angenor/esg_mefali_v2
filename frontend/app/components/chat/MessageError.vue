<script setup lang="ts">
/**
 * MessageError — bulle erreur sobre + bouton Réessayer.
 * F41 / US7 (T045). Libellé FR selon code ; émet `retry`.
 */
import { computed } from 'vue'
import type { ChatErrorCode } from '~/types/chat'

interface Props {
  code: ChatErrorCode
  message?: string
  messageId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'retry', messageId: string): void
}>()

const labels: Record<ChatErrorCode, string> = {
  validation: "La requête est invalide. Reformulez votre message.",
  timeout: "L'assistant a mis trop de temps à répondre.",
  network: "La connexion au serveur a été interrompue.",
  forbidden: "Action non autorisée pour ce compte.",
  unknown: "Une erreur inattendue s'est produite.",
}

const text = computed(() => props.message?.trim() || labels[props.code] || labels.unknown)
const canRetry = computed(() => props.code !== 'forbidden' && props.code !== 'validation')
</script>

<template>
  <div class="chat-error" role="alert">
    <div class="chat-error__inner">
      <span class="chat-error__icon" aria-hidden="true">!</span>
      <span class="chat-error__msg">{{ text }}</span>
    </div>
    <button
      v-if="canRetry"
      type="button"
      class="chat-error__retry"
      @click="emit('retry', props.messageId)"
    >
      Réessayer
    </button>
  </div>
</template>

<style scoped>
.chat-error {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgb(var(--color-danger-50, 254 242 242));
  border: 1px solid rgb(var(--color-danger-200, 254 202 202));
  border-radius: 12px;
  color: rgb(var(--color-danger-800, 153 27 27));
  max-width: min(60ch, 75%);
}
.chat-error__inner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.chat-error__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: rgb(var(--color-danger-200, 254 202 202));
  font-weight: 700;
  font-size: 0.875rem;
}
.chat-error__msg {
  flex: 1;
  font-size: 0.95rem;
  line-height: 1.4;
}
.chat-error__retry {
  align-self: flex-start;
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  border: 1px solid rgb(var(--color-danger-300, 252 165 165));
  background: white;
  color: rgb(var(--color-danger-700, 185 28 28));
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.15s;
}
.chat-error__retry:hover {
  background: rgb(var(--color-danger-50, 254 242 242));
}
.chat-error__retry:focus-visible {
  outline: 2px solid rgb(var(--color-danger-500, 239 68 68));
  outline-offset: 2px;
}
</style>
