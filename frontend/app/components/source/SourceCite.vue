<script setup lang="ts">
/**
 * F03 US4 — <SourceCite> : picto cliquable ouvrant le bottom sheet des sources.
 *
 * Contrat : voir specs/003-source-anti-hallucination/contracts/SourceCite.props.md.
 */
import { computed, ref } from 'vue'
import SourceListBottomSheet from './SourceListBottomSheet.vue'

const props = withDefaults(
  defineProps<{
    sourceIds: string[]
    inline?: boolean
    size?: 'sm' | 'md' | 'lg'
    accent?: 'auto' | 'verified' | 'pending' | 'outdated'
  }>(),
  {
    inline: true,
    size: 'sm',
    accent: 'auto',
  },
)

const emit = defineEmits<{
  (e: 'open', payload: { sourceIds: string[] }): void
  (e: 'external-link', payload: { sourceId: string, url: string }): void
}>()

const open = ref(false)

const sizeClass = computed(() => `cite-${props.size}`)

const onClick = () => {
  open.value = true
  emit('open', { sourceIds: props.sourceIds })
}

const onClose = () => {
  open.value = false
}

const onExternal = (payload: { sourceId: string, url: string }) => {
  emit('external-link', payload)
}
</script>

<template>
  <span :class="['source-cite', sizeClass, inline ? 'inline' : 'block']">
    <button
      type="button"
      class="picto"
      aria-label="Voir les sources de cette donnée"
      @click="onClick"
    >
      <span aria-hidden="true">🔗</span>
    </button>
    <SourceListBottomSheet
      :source-ids="sourceIds"
      :open="open"
      @close="onClose"
      @external-link="onExternal"
    />
  </span>
</template>

<style scoped>
.source-cite { display: inline-flex; align-items: center; }
.source-cite.block { display: block; }
.picto { background: none; border: none; cursor: pointer; padding: 2px; }
.cite-sm .picto { font-size: 0.75rem; }
.cite-md .picto { font-size: 1rem; }
.cite-lg .picto { font-size: 1.5rem; }
</style>
