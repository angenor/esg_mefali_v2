<script setup lang="ts">
/**
 * QuickReplies — chips de suggestions sous la dernière bulle assistant finale.
 * F41 / US8 (T050). Émet `pick` avec le contenu sélectionné.
 */
interface Props {
  suggestions: string[]
}

const props = withDefaults(defineProps<Props>(), { suggestions: () => [] })
const emit = defineEmits<{
  (e: 'pick', content: string): void
}>()
</script>

<template>
  <div v-if="props.suggestions.length > 0" class="quick-replies" role="group" aria-label="Réponses rapides">
    <button
      v-for="(s, i) in props.suggestions.slice(0, 3)"
      :key="i"
      type="button"
      class="quick-replies__chip"
      @click="emit('pick', s)"
    >
      {{ s }}
    </button>
  </div>
</template>

<style scoped>
.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0 1rem 0.5rem;
  max-width: 920px;
  margin: 0 auto;
  width: 100%;
}
.quick-replies__chip {
  padding: 0.375rem 0.75rem;
  border-radius: 999px;
  border: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  color: rgb(var(--color-fg-strong, 17 24 39));
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.15s;
}
.quick-replies__chip:hover {
  background: rgb(var(--color-bg-muted, 243 244 246));
}
.quick-replies__chip:focus-visible {
  outline: 2px solid rgb(var(--color-brand-500, 59 130 246));
  outline-offset: 2px;
}
</style>
