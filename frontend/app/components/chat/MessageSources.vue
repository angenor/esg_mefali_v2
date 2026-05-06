<script setup lang="ts">
/**
 * F56 / T041 (US7) — Rendu inline des chips Source.
 *
 * Reçoit le texte assistant + les sources (FR-011) et insère des
 * superscripts cliquables aux spans correspondants. Au clic, affiche un
 * popover via le composant <VizSourcePin> (F40) avec
 * title / publisher / URL / verification_status.
 *
 * Conforme P10 (UX bottom sheet) : le popover est read-only ; aucune
 * input form n'est demandée à l'utilisateur.
 */

import { computed, ref } from 'vue'
import type { SourceRef, UnsourcedClaim } from '~/types/chat'

interface Props {
  text: string
  sources?: SourceRef[]
  unsourcedClaims?: UnsourcedClaim[]
}

const props = withDefaults(defineProps<Props>(), {
  sources: () => [],
  unsourcedClaims: () => [],
})

const openSource = ref<SourceRef | null>(null)

interface SegmentText {
  kind: 'text'
  content: string
}

interface SegmentSource {
  kind: 'source'
  source: SourceRef
  start: number
  end: number
}

interface SegmentUnsourced {
  kind: 'unsourced'
  claim: UnsourcedClaim
  start: number
  end: number
}

type Segment = SegmentText | SegmentSource | SegmentUnsourced

/**
 * Découpe ``text`` en segments selon les spans des sources/claims.
 * Aux endroits matchés, on insère un superscript ; ailleurs, on conserve le
 * texte tel quel.
 */
const segments = computed<Segment[]>(() => {
  const text = props.text
  if (!text) return []

  type Marker = {
    start: number
    end: number
    payload: SegmentSource | SegmentUnsourced
  }
  const markers: Marker[] = []

  for (const src of props.sources ?? []) {
    for (const span of src.spans ?? []) {
      const [s, e] = span
      if (s < 0 || e > text.length || s >= e) continue
      markers.push({
        start: s,
        end: e,
        payload: { kind: 'source', source: src, start: s, end: e },
      })
    }
  }

  for (const claim of props.unsourcedClaims ?? []) {
    if (!claim.span) continue
    const [s, e] = claim.span
    if (s < 0 || e > text.length || s >= e) continue
    markers.push({
      start: s,
      end: e,
      payload: { kind: 'unsourced', claim, start: s, end: e },
    })
  }

  if (markers.length === 0) {
    return [{ kind: 'text', content: text }]
  }

  // Trier par start ; éviter les chevauchements en gardant le plus tôt
  markers.sort((a, b) => a.start - b.start)
  const out: Segment[] = []
  let cursor = 0
  for (const m of markers) {
    if (m.start < cursor) continue // overlap → skip
    if (cursor < m.start) {
      out.push({ kind: 'text', content: text.slice(cursor, m.start) })
    }
    out.push(m.payload)
    cursor = m.end
  }
  if (cursor < text.length) {
    out.push({ kind: 'text', content: text.slice(cursor) })
  }
  return out
})

/** Affiche/masque le popover. */
function open(src: SourceRef): void {
  openSource.value = src
}

function close(): void {
  openSource.value = null
}

function onPdfClick(src: SourceRef): void {
  if (typeof window !== 'undefined' && src.url) {
    window.open(src.url, '_blank', 'noopener,noreferrer')
  }
}
</script>

<template>
  <span class="message-sources">
    <template v-for="(seg, idx) in segments" :key="idx">
      <template v-if="seg.kind === 'text'">{{ seg.content }}</template>
      <template v-else-if="seg.kind === 'source'">
        <span>{{ text.slice(seg.start, seg.end) }}</span>
        <sup
          class="cursor-pointer text-blue-600 hover:text-blue-800 ml-0.5 select-none"
          :data-testid="'source-superscript'"
          :data-source-id="seg.source.source_id"
          role="button"
          tabindex="0"
          @click="open(seg.source)"
          @keydown.enter="open(seg.source)"
        >
          [{{ seg.source.citation_index }}]
        </sup>
      </template>
      <template v-else>
        <span
          class="bg-yellow-100 px-0.5 rounded"
          :data-testid="'unsourced-claim-chip'"
          :title="seg.claim.reason"
        >
          {{ text.slice(seg.start, seg.end) }}
        </span>
      </template>
    </template>

    <!-- Popover Source (read-only ; conforme P10) -->
    <div
      v-if="openSource"
      data-testid="source-pin-popover"
      role="dialog"
      class="fixed inset-0 flex items-center justify-center bg-black/30 z-50"
      @click="close"
    >
      <div
        class="bg-white rounded-lg shadow-lg p-4 max-w-md w-full"
        @click.stop
      >
        <div class="flex justify-between items-start mb-2">
          <h3 class="font-bold text-lg">{{ openSource.title }}</h3>
          <button
            class="text-gray-500 hover:text-gray-800"
            aria-label="Fermer"
            @click="close"
          >
            ✕
          </button>
        </div>
        <p class="text-sm text-gray-700 mb-1">
          <span class="font-semibold">Éditeur :</span> {{ openSource.publisher }}
        </p>
        <p v-if="openSource.page" class="text-sm text-gray-700 mb-1">
          <span class="font-semibold">Page :</span> {{ openSource.page }}
        </p>
        <p v-if="openSource.section" class="text-sm text-gray-700 mb-1">
          <span class="font-semibold">Section :</span> {{ openSource.section }}
        </p>
        <p v-if="openSource.version" class="text-sm text-gray-700 mb-1">
          <span class="font-semibold">Version :</span> {{ openSource.version }}
        </p>
        <p
          v-if="openSource.verification_status === 'outdated'"
          data-testid="source-outdated-badge"
          class="inline-block bg-orange-100 text-orange-700 px-2 py-0.5 rounded text-xs mb-2"
        >
          Source obsolète
        </p>
        <button
          class="mt-2 inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          @click="onPdfClick(openSource)"
        >
          Ouvrir le PDF
        </button>
      </div>
    </div>
  </span>
</template>
