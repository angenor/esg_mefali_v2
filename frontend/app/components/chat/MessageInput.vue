<script setup lang="ts">
/**
 * MessageInput — zone de saisie texte.
 *
 * F41 / US1 (T018) + US2 (T028).
 * UiTextarea autoresize 1–6 lignes, bouton envoi, attache (event-only),
 * `Cmd/Ctrl+Enter` envoie. Masqué quand un bottom sheet est ouvert (P10).
 */
import { computed, ref } from 'vue'
import { useChatBottomSheet } from '~/composables/useChatBottomSheet'

interface Props {
  disabled?: boolean
  maxLength?: number
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  maxLength: 32000,
})

const emit = defineEmits<{
  (e: 'submit', content: string): void
  (e: 'attach'): void
  (e: 'cancel'): void
}>()

const sheet = useChatBottomSheet()
const text = ref('')

const canSend = computed(() => !props.disabled && text.value.trim().length > 0 && text.value.length <= props.maxLength)
const isHidden = computed(() => sheet.isOpen.value)

function send(): void {
  if (!canSend.value) return
  const value = text.value.trim()
  text.value = ''
  emit('submit', value)
}

function onKeyDown(e: KeyboardEvent): void {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div v-if="!isHidden" class="chat-input" :data-disabled="props.disabled || null">
    <button
      type="button"
      class="chat-input__attach"
      aria-label="Ajouter une pièce jointe"
      :disabled="props.disabled"
      @click="emit('attach')"
    >
      <span aria-hidden="true">📎</span>
    </button>
    <UiTextarea
      v-model="text"
      :rows="1"
      :autosize="true"
      :maxlength="props.maxLength"
      :disabled="props.disabled"
      placeholder="Écrivez votre message…"
      aria-label="Message à l'assistant"
      class="chat-input__field"
      @keydown="onKeyDown"
    />
    <button
      type="button"
      class="chat-input__send"
      :disabled="!canSend"
      aria-label="Envoyer le message"
      @click="send"
    >
      <span aria-hidden="true">➤</span>
    </button>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.75rem;
  padding-bottom: max(0.75rem, env(safe-area-inset-bottom, 0));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  border-top: 1px solid rgb(var(--color-border, 229 231 235));
}
.chat-input__field {
  flex: 1;
  max-height: 9rem;
  overflow-y: auto;
}
.chat-input__attach,
.chat-input__send {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 8px;
  border: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  color: rgb(var(--color-fg-muted, 107 114 128));
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.chat-input__attach:hover:not(:disabled),
.chat-input__send:hover:not(:disabled) {
  background: rgb(var(--color-bg-muted, 243 244 246));
}
.chat-input__send {
  background: rgb(var(--color-brand-600, 37 99 235));
  color: white;
  border-color: rgb(var(--color-brand-600, 37 99 235));
}
.chat-input__send:disabled,
.chat-input__attach:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.chat-input__send:focus-visible,
.chat-input__attach:focus-visible {
  outline: 2px solid rgb(var(--color-brand-500, 59 130 246));
  outline-offset: 2px;
}
</style>
