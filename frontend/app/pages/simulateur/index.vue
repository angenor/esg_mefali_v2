<script setup lang="ts">
// F51 T090 — Page simulateur principale.
import { onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import { useSimulateurStore } from "~/stores/simulateur"
import { useSimulateurDebounce } from "~/composables/useSimulateurDebounce"
import { buildMatchingTargetFromInputs } from "~/utils/simulateurNav"
import SliderPanel from "~/components/simulateur/SliderPanel.vue"
import ResultsCharts from "~/components/simulateur/ResultsCharts.vue"
import SaveSimulationSheet from "~/components/simulateur/SaveSimulationSheet.vue"

const store = useSimulateurStore()
const route = useRoute()
const { trigger } = useSimulateurDebounce(300)
const saveOpen = ref(false)

onMounted(() => {
  store.rehydrateFromQuery(
    Object.fromEntries(
      Object.entries(route.query).map(([k, v]) => [k, Array.isArray(v) ? v.map(String) : String(v ?? "")]),
    ) as Record<string, string | string[]>,
  )
  void store.compute()
})

function onChange(): void {
  trigger()
}

async function onSave(label: string): Promise<void> {
  const ok = await store.save(label)
  if (ok) saveOpen.value = false
}

async function gotoMatching(): Promise<void> {
  // Navigation toujours basee sur les inputs courants (pas sur store.results) :
  // le CTA doit fonctionner meme si compute() n'a jamais reussi (defaults
  // 100k EUR / 60 mois). cf. F51 SC-006.
  const target = buildMatchingTargetFromInputs(store.inputs)
  await navigateTo(target)
}

useHead({ title: "Simulateur — ESG Mefali" })
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-6 p-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Simulateur de financement</h1>
      <NuxtLink to="/simulateur/historique" class="text-sm text-emerald-700 hover:underline">
        Historique →
      </NuxtLink>
    </header>

    <div class="grid gap-6 lg:grid-cols-[360px_1fr]">
      <SliderPanel @change="onChange" />
      <ResultsCharts />
    </div>

    <p v-if="store.error" class="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ store.error }}
    </p>

    <footer class="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 pt-4">
      <button
        type="button"
        class="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
        :disabled="!store.results"
        @click="saveOpen = true"
      >
        Sauvegarder
      </button>
      <button
        type="button"
        class="rounded bg-emerald-600 px-4 py-2 font-medium text-white shadow hover:bg-emerald-700"
        @click="gotoMatching"
      >
        Trouver des offres compatibles →
      </button>
    </footer>

    <SaveSimulationSheet
      :open="saveOpen"
      @save="onSave"
      @cancel="saveOpen = false"
    />
  </div>
</template>
