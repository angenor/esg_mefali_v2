<!--
  F50 T046 — DocPreviewDrawer (slide right, lazy pdfjs + image fallback + bureautique).
  Cf. contracts/documents_ui_contracts.md §6.
-->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useDocumentPreviewLazy } from '~/composables/useDocumentPreviewLazy'
import type { DocumentDetail } from '~/types/documents'

interface Props {
  open: boolean
  doc: DocumentDetail | null
  /** Construit l'URL de download/blob ; injectable pour tests. */
  downloadUrl?: (id: string) => string
}

const props = withDefaults(defineProps<Props>(), {
  doc: null,
  downloadUrl: undefined,
})

const emit = defineEmits<{
  (e: 'close'): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const pageNum = ref(1)
const totalPages = ref(0)
const loading = ref(false)
const errorMessage = ref<string | null>(null)

let pdfDoc: Awaited<ReturnType<ReturnType<typeof useDocumentPreviewLazy>['load']>> extends infer M
  ? M extends { getDocument: (...args: unknown[]) => infer D }
    ? D extends { promise: Promise<infer R> } ? R : null
    : null
  : null = null as never

function buildUrl(id: string): string {
  if (props.downloadUrl) return props.downloadUrl(id)
  // Dev/Nuxt : runtime config.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg = g.useRuntimeConfig?.()
  const base = String(cfg?.public?.apiBase ?? '').replace(/\/$/, '')
  return `${base}/me/entreprise/documents/${id}/download`
}

const isPdf = computed(() => props.doc?.mime_type === 'application/pdf')
const isImage = computed(() => /^image\//.test(props.doc?.mime_type ?? ''))
const isOffice = computed(() => {
  const m = props.doc?.mime_type ?? ''
  return (
    m.startsWith('application/vnd.openxmlformats-officedocument') ||
    m === 'application/msword' ||
    m === 'application/vnd.ms-excel'
  )
})

async function loadPdf(): Promise<void> {
  if (!props.doc || !isPdf.value) return
  loading.value = true
  errorMessage.value = null
  try {
    const { load } = useDocumentPreviewLazy()
    const pdfjs = await load()
    const url = buildUrl(props.doc.id)
    const resp = await fetch(url, { credentials: 'include' })
    if (!resp.ok) {
      if (resp.status === 423 || resp.status === 409) {
        errorMessage.value = 'Analyse antivirus en cours. Réessayez dans quelques instants.'
      } else {
        errorMessage.value = `Téléchargement impossible (${resp.status}).`
      }
      return
    }
    const buf = await resp.arrayBuffer()
    pdfDoc = (await pdfjs.getDocument({ data: new Uint8Array(buf) }).promise) as never
    totalPages.value = (pdfDoc as { numPages: number }).numPages
    pageNum.value = 1
    await renderPage()
  } catch (e) {
    errorMessage.value = (e as Error).message ?? 'preview_failed'
  } finally {
    loading.value = false
  }
}

async function renderPage(): Promise<void> {
  if (!pdfDoc || !canvasRef.value) return
  const page = await (pdfDoc as { getPage: (n: number) => Promise<unknown> }).getPage(
    pageNum.value,
  )
  const viewport = (page as {
    getViewport: (o: { scale: number }) => { width: number; height: number }
  }).getViewport({ scale: 1.2 })
  const canvas = canvasRef.value
  canvas.width = viewport.width
  canvas.height = viewport.height
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  await (page as {
    render: (o: { canvasContext: CanvasRenderingContext2D; viewport: unknown }) => {
      promise: Promise<void>
    }
  })
    .render({ canvasContext: ctx, viewport })
    .promise
}

function nextPage(): void {
  if (pageNum.value < totalPages.value) {
    pageNum.value += 1
    void nextTick(renderPage)
  }
}

function prevPage(): void {
  if (pageNum.value > 1) {
    pageNum.value -= 1
    void nextTick(renderPage)
  }
}

function onKeydown(e: KeyboardEvent): void {
  if (!props.open) return
  if (e.key === 'ArrowRight') nextPage()
  else if (e.key === 'ArrowLeft') prevPage()
  else if (e.key === 'Escape') emit('close')
}

watch(
  () => [props.open, props.doc?.id],
  async ([open]) => {
    if (open && isPdf.value) {
      await nextTick()
      await loadPdf()
    } else if (!open) {
      pdfDoc = null as never
      totalPages.value = 0
      pageNum.value = 1
      errorMessage.value = null
    }
  },
)

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onKeydown)
}
onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onKeydown)
  }
})
</script>

<template>
  <transition name="slide">
    <aside
      v-if="open && doc"
      class="fixed inset-y-0 right-0 z-40 flex w-full max-w-2xl flex-col bg-white shadow-2xl"
      role="dialog"
      aria-modal="true"
      :aria-label="`Aperçu de ${doc.name}`"
    >
      <header class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 class="truncate text-base font-semibold text-gray-900">{{ doc.name }}</h2>
        <div class="flex items-center gap-2">
          <a
            :href="buildUrl(doc.id)"
            class="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
            download
          >Télécharger</a>
          <button
            type="button"
            class="rounded-md p-1 text-gray-400 hover:text-gray-700"
            aria-label="Fermer la prévisualisation"
            @click="emit('close')"
          >✕</button>
        </div>
      </header>

      <div class="flex-1 overflow-auto bg-gray-50 p-4">
        <p
          v-if="errorMessage"
          role="alert"
          class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >{{ errorMessage }}</p>

        <div v-if="loading" role="status" aria-live="polite" class="text-sm text-gray-500">
          Chargement de l'aperçu…
        </div>

        <!-- PDF -->
        <div v-if="isPdf && !errorMessage" class="flex flex-col items-center gap-3">
          <canvas ref="canvasRef" class="rounded shadow" aria-label="Aperçu du PDF" />
          <nav v-if="totalPages > 0" class="flex items-center gap-3" aria-label="Navigation des pages">
            <button
              type="button"
              class="rounded-md border px-2 py-1 text-xs disabled:opacity-50"
              :disabled="pageNum <= 1"
              @click="prevPage"
            >Précédente</button>
            <span class="text-xs text-gray-600">Page {{ pageNum }} / {{ totalPages }}</span>
            <button
              type="button"
              class="rounded-md border px-2 py-1 text-xs disabled:opacity-50"
              :disabled="pageNum >= totalPages"
              @click="nextPage"
            >Suivante</button>
          </nav>
        </div>

        <!-- Image -->
        <div v-else-if="isImage && !errorMessage" class="flex justify-center">
          <img
            :src="buildUrl(doc.id)"
            :alt="doc.name"
            class="max-h-full max-w-full rounded shadow"
          >
        </div>

        <!-- Office (xlsx/docx) — fallback download -->
        <div
          v-else-if="isOffice && !errorMessage"
          class="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-center"
        >
          <p class="mb-3 text-sm text-gray-700">
            Aperçu indisponible pour les fichiers Excel/Word. Téléchargez le document pour le consulter.
          </p>
          <a
            :href="buildUrl(doc.id)"
            class="inline-flex rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            download
          >Télécharger {{ doc.original_filename }}</a>
        </div>

        <div v-else-if="!loading && !errorMessage" class="text-sm text-gray-500">
          Format non pris en charge pour la prévisualisation.
        </div>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
