<script setup lang="ts">
// F51 T070 — Page liste candidatures.
import { onMounted } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import CandidaturesTable from "~/components/candidatures/CandidaturesTable.vue"

const store = useCandidaturesStore()

onMounted(() => {
  void store.fetchList()
})

useHead({ title: "Mes candidatures — ESG Mefali" })
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-6 p-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Mes candidatures</h1>
      <NuxtLink
        to="/matching"
        class="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white shadow hover:bg-emerald-700"
      >
        + Nouvelle candidature
      </NuxtLink>
    </header>

    <p v-if="store.loading" class="text-sm text-gray-500">Chargement…</p>
    <p v-else-if="store.error" class="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ store.error }}
    </p>

    <CandidaturesTable v-else />
  </div>
</template>
