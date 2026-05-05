<!--
  F50 T056 — Grille embed sur /profil/projets/[id].
  Consomme l'union document_projet + document_entreprise via document_link_projet.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDocumentsStore } from '~/stores/documents'
import { documentEvents } from '~/lib/documentEvents'
import DocumentEmptyState from '~/components/documents/DocumentEmptyState.vue'
import UploadZone from '~/components/documents/UploadZone.vue'
import { mapOcrStatusToUi } from '~/utils/ocrStatusUi'
import type { DocumentDetail } from '~/types/documents'

interface Props {
  projetId: string
  projetName?: string
}

const props = defineProps<Props>()
const store = useDocumentsStore()

const showUpload = ref(false)
const showLinkPicker = ref(false)
const linking = ref(false)
const linkError = ref<string | null>(null)

const docs = computed<DocumentDetail[]>(() => {
  const ids = store.byProjet[props.projetId] ?? []
  return ids.map((id) => store.items[id]).filter(Boolean) as DocumentDetail[]
})

const candidates = computed<DocumentDetail[]>(() => {
  // Documents entreprise non encore liés à ce projet.
  const linkedSet = new Set(docs.value.map((d) => d.id))
  return Object.values(store.items).filter(
    (d) => !linkedSet.has(d.id) && !d.linked_projets.includes(props.projetId),
  )
})

let unsubscribers: Array<() => void> = []

onMounted(async () => {
  await Promise.all([store.fetchProjet(props.projetId), store.fetchEntreprise()])
  unsubscribers.push(
    documentEvents.on('documents:created', () => {
      void store.fetchProjet(props.projetId)
    }),
    documentEvents.on('documents:linked-projet', () => {
      void store.fetchProjet(props.projetId)
    }),
    documentEvents.on('documents:unlinked-projet', () => {
      void store.fetchProjet(props.projetId)
    }),
  )
})

async function onLink(docId: string): Promise<void> {
  linking.value = true
  linkError.value = null
  try {
    await store.linkProjet(docId, props.projetId)
    showLinkPicker.value = false
  } catch (e) {
    linkError.value = (e as Error).message ?? 'link_failed'
  } finally {
    linking.value = false
  }
}

async function onUnlink(docId: string): Promise<void> {
  if (!window.confirm('Retirer ce document du projet ?')) return
  await store.unlinkProjet(docId, props.projetId)
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}
</script>

<template>
  <section
    class="space-y-4 rounded-2xl border border-gray-200 bg-white p-4"
    aria-label="Documents du projet"
  >
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-lg font-semibold text-gray-900">Documents du projet</h2>
      <div class="flex gap-2">
        <button
          type="button"
          class="rounded-xl border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          @click="showLinkPicker = !showLinkPicker"
        >Lier un document existant</button>
        <button
          type="button"
          class="rounded-xl bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          @click="showUpload = !showUpload"
        >{{ showUpload ? 'Masquer' : 'Téléverser' }}</button>
      </div>
    </header>

    <UploadZone
      v-if="showUpload"
      :show="true"
      context="projet"
      :projet-id="projetId"
    />

    <div
      v-if="showLinkPicker"
      class="rounded-xl border border-gray-200 bg-gray-50 p-3"
      role="region"
      aria-label="Sélection d'un document à lier"
    >
      <p class="mb-2 text-sm text-gray-700">
        Documents de l'entreprise disponibles ({{ candidates.length }})
      </p>
      <p
        v-if="linkError"
        role="alert"
        class="mb-2 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700"
      >{{ linkError }}</p>
      <ul v-if="candidates.length > 0" class="max-h-60 space-y-1 overflow-y-auto">
        <li
          v-for="d in candidates"
          :key="d.id"
          class="flex items-center justify-between rounded-md bg-white px-2 py-1 text-sm"
        >
          <span class="truncate">{{ d.name }}</span>
          <button
            type="button"
            class="rounded-md bg-emerald-600 px-2 py-0.5 text-xs text-white hover:bg-emerald-700 disabled:opacity-50"
            :disabled="linking"
            @click="onLink(d.id)"
          >Lier</button>
        </li>
      </ul>
      <p v-else class="text-xs text-gray-500">Aucun document disponible à lier.</p>
    </div>

    <DocumentEmptyState
      v-if="docs.length === 0 && !showUpload"
      context="projet"
      :projet-name="projetName"
      @cta-click="showUpload = true"
    />

    <ul
      v-else-if="docs.length > 0"
      class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
      role="list"
    >
      <li
        v-for="d in docs"
        :key="d.id"
        class="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-3 shadow-sm"
      >
        <div class="flex items-start justify-between gap-2">
          <span class="line-clamp-2 text-sm font-medium text-gray-900">{{ d.name }}</span>
          <span
            class="shrink-0 rounded-full px-2 py-0.5 text-xs"
            :class="{
              'bg-emerald-100 text-emerald-700': mapOcrStatusToUi(d).tone === 'success',
              'bg-amber-100 text-amber-700': mapOcrStatusToUi(d).tone === 'warning',
              'bg-blue-100 text-blue-700': mapOcrStatusToUi(d).tone === 'info',
              'bg-red-100 text-red-700': mapOcrStatusToUi(d).tone === 'danger',
              'bg-gray-100 text-gray-700': mapOcrStatusToUi(d).tone === 'neutral',
            }"
          >{{ mapOcrStatusToUi(d).label }}</span>
        </div>
        <div class="flex items-center justify-between text-xs text-gray-500">
          <span>{{ d.type }}</span>
          <span>{{ fmtSize(d.size_bytes) }}</span>
        </div>
        <button
          type="button"
          class="self-end text-xs text-red-600 hover:underline"
          @click="onUnlink(d.id)"
        >Retirer du projet</button>
      </li>
    </ul>
  </section>
</template>
