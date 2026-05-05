<script setup lang="ts">
/**
 * MemoryBadge — taille mémoire visible top + modale détail.
 * F41 / US9 (T053). Lit `MemorySnapshot` du store ; click ouvre une modale
 * listant les entrées.
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useChatStore } from '~/stores/chat'

interface Props {
  threadId: string
}

const props = defineProps<Props>()
const store = useChatStore()
const open = ref(false)

const snapshot = computed(() => store.memorySnapshots[props.threadId] ?? null)
const size = computed(() => snapshot.value?.size ?? 0)

function refresh(): void {
  if (!props.threadId) return
  void store.fetchMemorySnapshot(props.threadId)
}

function onMemoryUpdated(e: Event): void {
  const detail = (e as CustomEvent).detail as { threadId?: string } | null
  if (!detail || detail.threadId === props.threadId) refresh()
}

onMounted(() => {
  refresh()
  if (typeof window !== 'undefined') {
    window.addEventListener('chat:memory-updated', onMemoryUpdated as EventListener)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('chat:memory-updated', onMemoryUpdated as EventListener)
  }
})

watch(() => props.threadId, refresh)
</script>

<template>
  <div class="memory-badge">
    <button
      type="button"
      class="memory-badge__btn"
      :aria-label="`Mémoire de la conversation : ${size} entrées`"
      @click="open = true"
    >
      <span aria-hidden="true">🧠</span>
      <span class="memory-badge__count">{{ size }}</span>
    </button>

    <div v-if="open" class="memory-badge__overlay" @click.self="open = false">
      <div class="memory-badge__modal" role="dialog" aria-label="Mémoire conversation">
        <header class="memory-badge__header">
          <h2>Mémoire de la conversation</h2>
          <button type="button" class="memory-badge__close" aria-label="Fermer" @click="open = false">×</button>
        </header>
        <div class="memory-badge__body">
          <p v-if="!snapshot || snapshot.entries.length === 0" class="memory-badge__empty">
            Aucune entrée pour le moment.
          </p>
          <ul v-else class="memory-badge__list">
            <li v-for="(entry, i) in snapshot.entries" :key="i" class="memory-badge__entry">
              <span class="memory-badge__kind">{{ entry.kind }}</span>
              <span class="memory-badge__preview">{{ entry.preview }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.memory-badge__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  border: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  font-size: 0.75rem;
  cursor: pointer;
}
.memory-badge__btn:hover { background: rgb(var(--color-bg-muted, 243 244 246)); }
.memory-badge__btn:focus-visible {
  outline: 2px solid rgb(var(--color-brand-500, 59 130 246));
  outline-offset: 2px;
}
.memory-badge__count { font-weight: 600; }
.memory-badge__overlay {
  position: fixed; inset: 0;
  background: rgb(0 0 0 / 0.4);
  z-index: 50;
  display: flex; align-items: center; justify-content: center;
}
.memory-badge__modal {
  background: white;
  border-radius: 12px;
  width: min(480px, 90vw);
  max-height: 80vh;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.memory-badge__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgb(var(--color-border, 229 231 235));
}
.memory-badge__header h2 { margin: 0; font-size: 1rem; }
.memory-badge__close {
  border: none; background: transparent; font-size: 1.5rem; cursor: pointer;
  width: 2rem; height: 2rem; border-radius: 6px;
}
.memory-badge__close:hover { background: rgb(var(--color-bg-muted, 243 244 246)); }
.memory-badge__body { padding: 0.75rem 1rem; overflow-y: auto; }
.memory-badge__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
.memory-badge__entry {
  display: flex; flex-direction: column; gap: 0.125rem;
  padding: 0.5rem; border-radius: 6px;
  background: rgb(var(--color-bg-muted, 243 244 246));
}
.memory-badge__kind { font-size: 0.75rem; color: rgb(var(--color-fg-muted, 107 114 128)); text-transform: uppercase; letter-spacing: 0.05em; }
.memory-badge__preview { font-size: 0.875rem; }
.memory-badge__empty { color: rgb(var(--color-fg-muted, 107 114 128)); font-size: 0.875rem; }
</style>
