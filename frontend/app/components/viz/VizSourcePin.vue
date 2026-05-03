<!--
  F40 T015-T016 — VizSourcePin : pin universel cliquable ouvrant une popover
  qui affiche la source résolue via useSourcesStore(). Fail-silent en 404 (US5 #3).
-->
<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useSourcesStore } from '~/stores/sources'
import { SourceNotFoundError, type SourceRef } from '~/types/viz/source'
import { useFloating } from '~/composables/useFloating'

interface Props {
  source_id: string
  label?: string
}
const props = withDefaults(defineProps<Props>(), {
  label: 'Voir la source',
})

const sources = useSourcesStore()
const open = ref(false)
const data = ref<SourceRef | null>(null)
const loading = ref(false)
const notFound = ref(false)
const error = ref<string | null>(null)

const { referenceRef, floatingRef, floatingStyles } = useFloating({
  placement: 'bottom-start',
  open,
  offsetPx: 6,
})

async function fetchOnce(): Promise<void> {
  if (data.value || notFound.value) return
  loading.value = true
  error.value = null
  try {
    data.value = await sources.resolve(props.source_id)
  }
  catch (e) {
    if (e instanceof SourceNotFoundError) {
      notFound.value = true
    }
    else {
      error.value = e instanceof Error ? e.message : 'unknown'
      // eslint-disable-next-line no-console
      console.error('[VizSourcePin]', e)
    }
  }
  finally {
    loading.value = false
  }
}

onMounted(() => {
  // Lecture cache immédiate sans réseau
  const peek = sources.peek(props.source_id)
  if (peek) data.value = peek
})

async function toggle(): Promise<void> {
  if (notFound.value) return
  if (!open.value) await fetchOnce()
  if (!notFound.value) open.value = !open.value
}

function close(): void { open.value = false }

const pillarColor = computed<string>(() => {
  switch (data.value?.pillar) {
    case 'E': return 'var(--color-brand-500, #16a34a)'
    case 'S': return 'var(--color-info-500, #0ea5e9)'
    case 'G': return 'var(--color-violet-500, #8b5cf6)'
    case 'financial': return 'var(--color-warning-500, #f59e0b)'
    case 'regulatory': return 'var(--color-danger-500, #ef4444)'
    case 'methodology': return 'var(--color-neutral-500, #737373)'
    default: return 'var(--color-neutral-400, #a3a3a3)'
  }
})

const isRevoked = computed<boolean>(() => data.value?.status === 'revoked')

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape' && open.value) close()
}

watch(() => props.source_id, () => {
  data.value = null
  notFound.value = false
  open.value = false
})
</script>

<template>
  <span v-if="!notFound" class="viz-source-pin" @keydown="onKey">
    <button
      ref="referenceRef"
      type="button"
      class="viz-source-pin__btn"
      :aria-label="props.label"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="toggle"
    >
      <svg
        class="viz-source-pin__icon"
        :class="{ 'is-revoked': isRevoked }"
        viewBox="0 0 24 24"
        width="14"
        height="14"
        aria-hidden="true"
        focusable="false"
      >
        <path
          v-if="!isRevoked"
          fill="currentColor"
          d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"
        />
        <path
          v-else
          fill="currentColor"
          d="M12 2 1 21h22L12 2zm0 6 7.5 13h-15L12 8zm-1 4v4h2v-4h-2zm0 6v2h2v-2h-2z"
        />
      </svg>
    </button>

    <div
      v-if="open && data"
      ref="floatingRef"
      class="viz-source-pin__popover"
      role="dialog"
      :aria-label="data.title"
      :style="floatingStyles"
    >
      <div class="viz-source-pin__head">
        <span class="viz-source-pin__pillar" :style="{ background: pillarColor }">
          {{ data.pillar }}
        </span>
        <a
          class="viz-source-pin__title"
          :href="data.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ data.title }}
        </a>
        <button
          type="button"
          class="viz-source-pin__close"
          aria-label="Fermer"
          @click="close"
        >×</button>
      </div>
      <p class="viz-source-pin__meta">
        Validité : {{ data.valid_from }}<template v-if="data.valid_to"> → {{ data.valid_to }}</template>
      </p>
      <p v-if="isRevoked" class="viz-source-pin__warn">
        ⚠ Source révoquée<template v-if="data.revoked_reason"> : {{ data.revoked_reason }}</template>
      </p>
    </div>

    <span v-if="loading" class="sr-only">Chargement de la source…</span>
  </span>
</template>

<style scoped>
.viz-source-pin {
  display: inline-flex;
  position: relative;
  vertical-align: baseline;
}
.viz-source-pin__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  color: var(--color-brand-600, #15803d);
  cursor: pointer;
}
.viz-source-pin__btn:focus-visible {
  outline: 2px solid var(--color-info-500, #0ea5e9);
  outline-offset: 2px;
}
.viz-source-pin__icon.is-revoked { color: var(--color-warning-500, #f59e0b); }

.viz-source-pin__popover {
  z-index: 100;
  width: 18rem;
  padding: 0.75rem;
  background: var(--color-neutral-50, #ffffff);
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  font-size: 0.85rem;
}
.viz-source-pin__head {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}
.viz-source-pin__pillar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.5rem;
  padding: 0 0.4rem;
  height: 1.25rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: white;
  border-radius: 999px;
  text-transform: uppercase;
}
.viz-source-pin__title {
  flex: 1;
  color: var(--color-brand-700, #166534);
  text-decoration: underline;
  word-break: break-word;
}
.viz-source-pin__close {
  background: none;
  border: none;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  color: var(--color-neutral-500, #737373);
}
.viz-source-pin__meta {
  margin: 0.4rem 0 0;
  color: var(--color-neutral-600, #525252);
  font-size: 0.75rem;
}
.viz-source-pin__warn {
  margin: 0.4rem 0 0;
  color: var(--color-warning-700, #b45309);
  font-size: 0.75rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
