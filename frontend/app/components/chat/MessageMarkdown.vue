<script setup lang="ts">
/**
 * MessageMarkdown — rendu Markdown sanitisé tolérant aux fragments.
 *
 * F41 / US1 (T013). Sécurité : passe par useMarkdownStream (markdown-it +
 * DOMPurify allow-list stricte). Curseur clignotant si streaming.
 */
import { computed } from 'vue'
import { useMarkdownStream } from '~/composables/useMarkdownStream'

interface Props {
  content: string
  streaming?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  streaming: false,
})

const { render } = useMarkdownStream()
const html = computed(() => render(props.content))
</script>

<template>
  <div class="chat-md">
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div class="chat-md__body" v-html="html" />
    <span v-if="streaming" class="chat-md__cursor" aria-hidden="true" />
  </div>
</template>

<style scoped>
.chat-md {
  display: inline;
  line-height: 1.55;
  color: rgb(var(--color-fg-strong, 17 24 39));
}
.chat-md__body :deep(p) { margin: 0 0 0.5em; }
.chat-md__body :deep(p:last-child) { margin-bottom: 0; }
.chat-md__body :deep(ul),
.chat-md__body :deep(ol) { padding-left: 1.25em; margin: 0.25em 0; }
.chat-md__body :deep(code) {
  background: rgb(var(--color-bg-muted, 243 244 246));
  padding: 0.1em 0.3em;
  border-radius: 4px;
  font-size: 0.92em;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.chat-md__body :deep(pre) {
  background: rgb(var(--color-bg-muted, 243 244 246));
  padding: 0.75em 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5em 0;
}
.chat-md__body :deep(pre code) { background: transparent; padding: 0; }
.chat-md__body :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
  font-size: 0.95em;
}
.chat-md__body :deep(th),
.chat-md__body :deep(td) {
  border: 1px solid rgb(var(--color-border, 229 231 235));
  padding: 0.4em 0.7em;
  text-align: left;
}
.chat-md__body :deep(blockquote) {
  border-left: 3px solid rgb(var(--color-border, 229 231 235));
  padding-left: 0.75em;
  margin: 0.5em 0;
  color: rgb(var(--color-fg-muted, 107 114 128));
}
.chat-md__body :deep(a) {
  color: rgb(var(--color-brand-600, 37 99 235));
  text-decoration: underline;
  text-underline-offset: 2px;
}
.chat-md__cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: rgb(var(--color-brand-500, 59 130 246));
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: chat-md-blink 1s steps(2, start) infinite;
}
@keyframes chat-md-blink { to { visibility: hidden; } }
@media (prefers-reduced-motion: reduce) {
  .chat-md__cursor { animation: none; opacity: 0.6; }
}
</style>
