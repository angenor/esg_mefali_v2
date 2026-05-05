<!--
  F50 T029 — Page /documents : empty state + UploadZone + DocumentTable + recherche.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useDocumentsStore } from '~/stores/documents'
import { documentEvents } from '~/lib/documentEvents'
import DocumentEmptyState from '~/components/documents/DocumentEmptyState.vue'
import DocumentTable from '~/components/documents/DocumentTable.vue'
import UploadZone from '~/components/documents/UploadZone.vue'
import DuplicateChoiceSheet from '~/components/documents/DuplicateChoiceSheet.vue'
import OcrSummarySheet from '~/components/documents/OcrSummarySheet.vue'
import DocPreviewDrawer from '~/components/documents/DocPreviewDrawer.vue'
import DeleteConfirmModal from '~/components/documents/DeleteConfirmModal.vue'
import type { DocumentDetail } from '~/types/documents'

const store = useDocumentsStore()

const showUpload = ref(false)
const duplicateOpen = ref(false)
const duplicateExisting = ref<DocumentDetail | null>(null)
const duplicateFilename = ref('')
const duplicateJobId = ref<string | null>(null)

const summaryOpen = ref(false)
const summaryDocId = ref<string | null>(null)

const previewOpen = ref(false)
const previewDoc = ref<DocumentDetail | null>(null)

const deleteOpen = ref(false)
const deleteDocId = ref<string | null>(null)
const deleteDocName = ref('')

const items = computed(() => store.filteredItems)

onMounted(async () => {
  await store.fetchEntreprise()
  // Démarrer polling pour docs non terminaux.
  for (const doc of store.entrepriseList) {
    if (doc.ocr_status === 'pending' || doc.ocr_status === 'processing') {
      store.startPolling(doc.id)
    }
  }
  // Sync cross-onglet : rafraîchir au document:created reçu.
  unsubCreated = documentEvents.on('documents:created', () => {
    void store.fetchEntreprise()
  })
  unsubDeleted = documentEvents.on('documents:deleted', () => {
    void store.fetchEntreprise()
  })
})

let unsubCreated: (() => void) | null = null
let unsubDeleted: (() => void) | null = null

onUnmounted(() => {
  store.stopAllPolling()
  unsubCreated?.()
  unsubDeleted?.()
})

function onDuplicate({ jobId, existingId }: { jobId: string; existingId: string }) {
  const job = store.uploadQueue.find((j) => j.id === jobId)
  duplicateJobId.value = jobId
  duplicateFilename.value = job?.filename ?? ''
  // existingId is sha256 in our queue; we don't have the full doc here — try to find in store.
  duplicateExisting.value =
    Object.values(store.items).find((d) => d.content_sha256 === existingId) ?? null
  duplicateOpen.value = true
}

function onReuse() {
  if (duplicateJobId.value) store.confirmDuplicateReuse(duplicateJobId.value)
  duplicateOpen.value = false
  duplicateJobId.value = null
}

function onForceNew() {
  if (duplicateJobId.value) {
    store.confirmDuplicateForceNew(duplicateJobId.value, { type: 'autre' })
  }
  duplicateOpen.value = false
  duplicateJobId.value = null
}

function onCancelDuplicate() {
  if (duplicateJobId.value) store.confirmDuplicateReuse(duplicateJobId.value)
  duplicateOpen.value = false
  duplicateJobId.value = null
}

function openVerify(id: string) {
  summaryDocId.value = id
  summaryOpen.value = true
}

function openPreview(id: string) {
  previewDoc.value = store.items[id] ?? null
  previewOpen.value = true
}

function askDelete(id: string) {
  const doc = store.items[id]
  deleteDocId.value = id
  deleteDocName.value = doc?.name ?? ''
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!deleteDocId.value) return
  await store.softDelete(deleteDocId.value)
  deleteOpen.value = false
  deleteDocId.value = null
}

async function onTagsUpdate(payload: { id: string; tags: string[] }) {
  await store.updateTags(payload.id, payload.tags)
}
</script>

<template>
  <main class="mx-auto max-w-6xl space-y-6 p-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">Mes documents</h1>
      <button
        v-if="items.length > 0 || showUpload"
        type="button"
        class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        @click="showUpload = !showUpload"
      >
        {{ showUpload ? 'Masquer le téléversement' : 'Téléverser' }}
      </button>
    </header>

    <div v-if="store.loading" class="text-sm text-gray-500">Chargement…</div>

    <DocumentEmptyState
      v-else-if="items.length === 0 && !showUpload"
      context="entreprise"
      @cta-click="showUpload = true"
    />

    <UploadZone
      v-if="showUpload || items.length > 0"
      :show="showUpload || items.length === 0"
      context="entreprise"
      @duplicate-detected="onDuplicate"
    />

    <div v-if="items.length > 0" class="space-y-3">
      <div class="flex flex-wrap gap-2">
        <input
          type="search"
          placeholder="Rechercher (nom, tag…)"
          class="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm"
          :value="store.search.q"
          @input="store.setSearch({ q: ($event.target as HTMLInputElement).value })"
        >
        <select
          class="rounded-xl border border-gray-300 px-3 py-2 text-sm"
          :value="store.search.type ?? ''"
          aria-label="Filtrer par type"
          @change="store.setSearch({ type: ($event.target as HTMLSelectElement).value || null })"
        >
          <option value="">Tous types</option>
          <option value="statuts">Statuts</option>
          <option value="rapport_activite">Rapport activité</option>
          <option value="facture">Facture</option>
          <option value="contrat">Contrat</option>
          <option value="politique">Politique</option>
          <option value="autre">Autre</option>
        </select>
        <input
          type="date"
          aria-label="Date à partir du"
          class="rounded-xl border border-gray-300 px-3 py-2 text-sm"
          :value="store.search.from ?? ''"
          @input="store.setSearch({ from: ($event.target as HTMLInputElement).value || null })"
        >
        <input
          type="date"
          aria-label="Date jusqu'au"
          class="rounded-xl border border-gray-300 px-3 py-2 text-sm"
          :value="store.search.to ?? ''"
          @input="store.setSearch({ to: ($event.target as HTMLInputElement).value || null })"
        >
      </div>

      <DocumentTable
        :items="items"
        :loading="store.loading"
        @verify="openVerify"
        @preview="openPreview"
        @delete="askDelete"
      />
    </div>

    <DuplicateChoiceSheet
      :open="duplicateOpen"
      :filename="duplicateFilename"
      :existing="duplicateExisting"
      @reuse="onReuse"
      @force-new="onForceNew"
      @cancel="onCancelDuplicate"
    />

    <OcrSummarySheet
      v-if="summaryDocId"
      :open="summaryOpen"
      :doc-id="summaryDocId"
      @close="summaryOpen = false"
    />

    <DocPreviewDrawer
      :open="previewOpen"
      :doc="previewDoc"
      @close="previewOpen = false"
    />

    <DeleteConfirmModal
      :open="deleteOpen"
      :document-name="deleteDocName"
      @cancel="deleteOpen = false"
      @confirm="confirmDelete"
    />
  </main>
</template>
