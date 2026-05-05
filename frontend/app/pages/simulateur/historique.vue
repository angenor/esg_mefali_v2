<script setup lang="ts">
// F51 T091 — Page historique des simulations sauvegardées.
import { onMounted } from "vue"
import { useSimulateurStore } from "~/stores/simulateur"
import HistoriqueList from "~/components/simulateur/HistoriqueList.vue"

const store = useSimulateurStore()
onMounted(() => {
  void store.fetchHistory()
})

useHead({ title: "Historique des simulations — ESG Mefali" })
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6 p-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Historique des simulations</h1>
      <NuxtLink to="/simulateur" class="text-sm text-emerald-700 hover:underline">
        ← Retour au simulateur
      </NuxtLink>
    </header>

    <p v-if="store.historyLoading" class="text-sm text-gray-500">Chargement…</p>
    <HistoriqueList v-else />
  </div>
</template>
