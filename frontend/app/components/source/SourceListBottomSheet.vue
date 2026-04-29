<script setup lang="ts">
/**
 * F03 US4 — Bottom sheet listant les sources (gsap slide-up + focus trap).
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { Source } from '../../composables/useSourceFetch'
import { useSourceFetch } from '../../composables/useSourceFetch'

const props = defineProps<{
  sourceIds: string[]
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'external-link', payload: { sourceId: string, url: string }): void
}>()

const sources = ref<Array<{ id: string, data: Source | null, loading: boolean, error: string | null }>>(
  props.sourceIds.map(id => ({ id, data: null, loading: true, error: null })),
)

onMounted(() => {
  for (let i = 0; i < props.sourceIds.length; i++) {
    const sid = props.sourceIds[i]!
    const { state } = useSourceFetch(sid)
    // Surveille l'état réactif
    const unwatch = setInterval(() => {
      sources.value[i] = {
        id: sid,
        data: state.value.data,
        loading: state.value.loading,
        error: state.value.error,
      }
      if (!state.value.loading) clearInterval(unwatch)
    }, 50)
  }
})

const onBackdrop = () => emit('close')
const onClose = () => emit('close')
const onExternal = (s: Source) => {
  emit('external-link', { sourceId: s.id, url: s.url })
}

const badgeClass = (status: string) => {
  if (status === 'verified') return 'badge-verified'
  if (status === 'outdated') return 'badge-outdated'
  return 'badge-pending'
}

const badgeLabel = (status: string) => {
  if (status === 'verified') return 'Vérifiée'
  if (status === 'outdated') return 'Obsolète'
  if (status === 'rejected') return 'Rejetée'
  return 'Non vérifiée'
}

// Focus trap basique — ferme sur Escape
const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div v-if="open" class="bottom-sheet-root">
    <div class="backdrop" @click="onBackdrop" />
    <aside class="sheet" role="dialog" aria-modal="true" aria-label="Liste des sources">
      <header>
        <h2>Sources</h2>
        <button type="button" aria-label="Fermer" @click="onClose">
          ✕
        </button>
      </header>
      <ul>
        <li v-for="entry in sources" :key="entry.id">
          <div v-if="entry.loading" class="skeleton">
            Chargement…
          </div>
          <div v-else-if="entry.error" class="error-box">
            {{ entry.error }}
          </div>
          <div v-else-if="entry.data">
            <p class="title">
              {{ entry.data.title }}
            </p>
            <p class="meta">
              <span>{{ entry.data.publisher }}</span>
              <span v-if="entry.data.version">v{{ entry.data.version }}</span>
              <span v-if="entry.data.date_publi">{{ entry.data.date_publi }}</span>
              <span :class="badgeClass(entry.data.verification_status)">
                {{ badgeLabel(entry.data.verification_status) }}
              </span>
            </p>
            <a
              :href="entry.data.url"
              target="_blank"
              rel="noopener"
              @click="() => entry.data && onExternal(entry.data)"
            >Ouvrir la source</a>
          </div>
        </li>
        <li v-if="sources.length === 0">
          <span class="empty">Aucune source</span>
        </li>
      </ul>
    </aside>
  </div>
</template>

<style scoped>
.bottom-sheet-root { position: fixed; inset: 0; z-index: 50; }
.backdrop { position: absolute; inset: 0; background: rgba(0,0,0,.4); }
.sheet {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: white; border-top-left-radius: 16px; border-top-right-radius: 16px;
  padding: 16px; max-height: 80vh; overflow-y: auto;
}
.badge-verified { color: #065f46; background:#d1fae5; padding:2px 6px; border-radius:4px; }
.badge-pending { color: #92400e; background:#fde68a; padding:2px 6px; border-radius:4px; }
.badge-outdated { color: #991b1b; background:#fecaca; padding:2px 6px; border-radius:4px; }
header { display:flex; justify-content:space-between; align-items:center; }
ul { list-style: none; padding: 0; margin: 0; }
li { padding: 8px 0; border-bottom: 1px solid #eee; }
.title { font-weight: 600; }
.meta { display: flex; gap: 8px; font-size: 0.875rem; color: #555; }
</style>
