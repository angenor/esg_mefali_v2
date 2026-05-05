<script setup lang="ts">
// F52 US3 — Page /dashboard/exports — historique + nouvelle génération.
import { onMounted, ref } from 'vue'
import { useExportsStore } from '~/stores/exports'
import ExportsTable from '~/components/dashboard/ExportsTable.vue'
import NewExportBottomSheet from '~/components/dashboard/NewExportBottomSheet.vue'

definePageMeta({ middleware: ['pme-only'] })

const store = useExportsStore()
const sheetOpen = ref(false)

onMounted(() => {
  void store.load()
})

async function onSubmit(payload: { type: string; format: string }) {
  await store.create(payload as Parameters<typeof store.create>[0])
}

function loadMore() {
  if (!store.nextCursor) return
  void store.load({ cursor: store.nextCursor })
}
</script>

<template>
  <section class="mx-auto max-w-5xl px-4 py-8" data-testid="exports-page">
    <header class="mb-6 flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Mes exports</h1>
        <p class="mt-1 text-sm text-gray-500">
          Historique des exports RGPD, rapports et attestations générés.
        </p>
      </div>
      <button
        type="button"
        class="rounded bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        data-testid="exports-new-btn"
        @click="sheetOpen = true"
      >
        Nouvel export
      </button>
    </header>

    <ExportsTable :items="store.items" :loading="store.loading" />

    <p
      v-if="store.error"
      class="mt-3 text-sm text-red-700"
      data-testid="exports-error"
    >
      Échec du chargement : {{ store.error }}
    </p>

    <div v-if="store.nextCursor" class="mt-4 text-center">
      <button
        type="button"
        class="rounded border border-gray-200 bg-white px-3 py-1.5 text-sm"
        @click="loadMore"
      >
        Charger plus
      </button>
    </div>

    <NewExportBottomSheet v-model="sheetOpen" @submit="onSubmit" />
  </section>
</template>
