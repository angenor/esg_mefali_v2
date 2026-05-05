<!--
  F50 T028 — DocumentTable (vue-virtual-scroller).
  Cf. contracts/documents_ui_contracts.md §2.
-->
<script setup lang="ts">
import { computed } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import type { DocumentDetail } from '~/types/documents'
import { mapOcrStatusToUi } from '~/utils/ocrStatusUi'

interface Props {
  items: DocumentDetail[]
  loading?: boolean
  selectedId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectedId: null,
})

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'preview', id: string): void
  (e: 'verify', id: string): void
  (e: 'delete', id: string): void
}>()

const ROW_HEIGHT = 56

const rows = computed(() => props.items)

function fmtSize(n: number): string {
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

function fmtDate(s: string): string {
  try {
    return new Date(s).toLocaleDateString('fr-FR')
  } catch {
    return s
  }
}
</script>

<template>
  <div role="grid" aria-label="Liste de documents" class="rounded-2xl border border-gray-200 bg-white">
    <div
      class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-2 border-b border-gray-200 px-4 py-2 text-xs font-medium uppercase tracking-wide text-gray-500"
      role="row"
    >
      <span role="columnheader">Nom</span>
      <span role="columnheader">Type</span>
      <span role="columnheader">Date</span>
      <span role="columnheader">Statut</span>
      <span role="columnheader">Taille</span>
      <span role="columnheader" class="sr-only">Actions</span>
    </div>

    <div v-if="loading" class="p-8 text-center text-sm text-gray-500">Chargement…</div>

    <RecycleScroller
      v-else
      class="max-h-[60vh]"
      :items="rows"
      :item-size="ROW_HEIGHT"
      key-field="id"
      role="rowgroup"
      v-slot="{ item, index }"
    >
      <div
        :key="item.id"
        :class="[
          'grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] items-center gap-2 border-b border-gray-100 px-4 py-2 text-sm',
          selectedId === item.id ? 'bg-emerald-50' : 'hover:bg-gray-50',
        ]"
        role="row"
        :aria-rowindex="index + 2"
        tabindex="0"
        @click="emit('select', item.id)"
        @keydown.enter="emit('select', item.id)"
      >
        <span class="truncate font-medium text-gray-900" role="gridcell">{{ item.name }}</span>
        <span class="text-gray-600" role="gridcell">{{ item.type }}</span>
        <span class="text-gray-600" role="gridcell">{{ fmtDate(item.created_at) }}</span>
        <span role="gridcell">
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
            :class="{
              'bg-emerald-100 text-emerald-700': mapOcrStatusToUi(item).tone === 'success',
              'bg-amber-100 text-amber-700': mapOcrStatusToUi(item).tone === 'warning',
              'bg-blue-100 text-blue-700': mapOcrStatusToUi(item).tone === 'info',
              'bg-red-100 text-red-700': mapOcrStatusToUi(item).tone === 'danger',
              'bg-gray-100 text-gray-700': mapOcrStatusToUi(item).tone === 'neutral',
            }"
            :aria-label="`Statut OCR : ${mapOcrStatusToUi(item).label}`"
          >
            {{ mapOcrStatusToUi(item).label }}
          </span>
        </span>
        <span class="text-gray-600" role="gridcell">{{ fmtSize(item.size_bytes) }}</span>
        <span class="flex gap-1" role="gridcell">
          <button
            type="button"
            class="rounded-md p-1 text-xs text-gray-600 hover:bg-gray-100"
            aria-label="Prévisualiser"
            @click.stop="emit('preview', item.id)"
          >👁</button>
          <button
            v-if="mapOcrStatusToUi(item).status === 'verify'"
            type="button"
            class="rounded-md bg-amber-100 px-2 py-1 text-xs text-amber-800 hover:bg-amber-200"
            @click.stop="emit('verify', item.id)"
          >Vérifier</button>
          <button
            type="button"
            class="rounded-md p-1 text-xs text-red-600 hover:bg-red-50"
            aria-label="Supprimer"
            @click.stop="emit('delete', item.id)"
          >🗑</button>
        </span>
      </div>
    </RecycleScroller>
  </div>
</template>
