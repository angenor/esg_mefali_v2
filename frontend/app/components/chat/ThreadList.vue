<script setup lang="ts">
/**
 * ThreadList — sidebar listant les threads + bouton Nouveau chat.
 *
 * F41 / US4 (T035). Tri DESC `lastMessageAt`. Au-delà de 50 threads,
 * virtualisation via vue-virtual-scroller.
 */
import { computed } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import type { ChatThreadSummary } from '~/types/chat'

interface Props {
  threads: ChatThreadSummary[]
  currentId?: string
}

const props = withDefaults(defineProps<Props>(), { currentId: '' })
const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'new-chat'): void
}>()

const VIRTUALIZE_THRESHOLD = 50

const sorted = computed(() => {
  return [...props.threads]
    .filter((t) => !t.archived)
    .sort((a, b) => {
      return new Date(b.lastMessageAt).getTime() - new Date(a.lastMessageAt).getTime()
    })
})

const shouldVirtualize = computed(() => sorted.value.length > VIRTUALIZE_THRESHOLD)

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    const today = new Date()
    if (d.toDateString() === today.toDateString()) {
      return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
  } catch {
    return ''
  }
}
</script>

<template>
  <div class="thread-list">
    <button
      type="button"
      class="thread-list__new"
      @click="emit('new-chat')"
    >
      <span aria-hidden="true">＋</span>
      Nouveau chat
    </button>

    <ClientOnly v-if="shouldVirtualize">
      <RecycleScroller
        class="thread-list__virtual"
        :items="sorted"
        :item-size="64"
        key-field="id"
        v-slot="{ item }"
      >
        <button
          type="button"
          class="thread-list__item"
          :class="{ 'thread-list__item--active': item.id === currentId }"
          @click="emit('select', item.id)"
        >
          <span class="thread-list__title">{{ item.title || 'Sans titre' }}</span>
          <span class="thread-list__time">{{ formatDate(item.lastMessageAt) }}</span>
        </button>
      </RecycleScroller>
    </ClientOnly>
    <ul v-else class="thread-list__items" role="list">
      <li v-for="t in sorted" :key="t.id">
        <button
          type="button"
          class="thread-list__item"
          :class="{ 'thread-list__item--active': t.id === currentId }"
          @click="emit('select', t.id)"
        >
          <span class="thread-list__title">{{ t.title || 'Sans titre' }}</span>
          <span class="thread-list__time">{{ formatDate(t.lastMessageAt) }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.thread-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.75rem;
  gap: 0.5rem;
}
.thread-list__new {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgb(var(--color-brand-200, 191 219 254));
  background: rgb(var(--color-brand-50, 239 246 255));
  color: rgb(var(--color-brand-700, 29 78 216));
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.15s;
}
.thread-list__new:hover {
  background: rgb(var(--color-brand-100, 219 234 254));
}
.thread-list__new:focus-visible {
  outline: 2px solid rgb(var(--color-brand-500, 59 130 246));
  outline-offset: 2px;
}
.thread-list__items,
.thread-list__virtual {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  overflow-y: auto;
}
.thread-list__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  border-radius: 6px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 0.125rem;
}
.thread-list__item:hover {
  background: rgb(var(--color-bg-muted, 243 244 246));
}
.thread-list__item--active {
  background: rgb(var(--color-brand-100, 219 234 254));
}
.thread-list__title {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(var(--color-fg-strong, 17 24 39));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}
.thread-list__time {
  font-size: 0.75rem;
  color: rgb(var(--color-fg-muted, 107 114 128));
}
</style>
