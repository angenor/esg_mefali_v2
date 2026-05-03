<script setup lang="ts">
// F38 T017 — page stub PME
// F42 T037 — déclenche le tour onboarding si state=pending au mount
// F42 T063 — affiche EmptyStateLanding si profil entreprise < 50 %
import { onMounted, ref, computed } from "vue"
import { useOnboardingTour } from "~/composables/useOnboardingTour"
import { useEntrepriseStore } from "~/stores/entreprise"
import FullscreenTourStep from "~/components/onboarding/FullscreenTourStep.vue"
import EmptyStateLanding from "~/components/onboarding/EmptyStateLanding.vue"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Tableau de bord" }],
  title: "Tableau de bord",
})

const { startIfPending } = useOnboardingTour()
const entrepriseStore = useEntrepriseStore()
const completionLoaded = ref(false)

const showEmptyState = computed(() => {
  if (!completionLoaded.value) return false
  const pct = entrepriseStore.completionPct
  return pct === null || pct < 50
})

onMounted(async () => {
  await nextTick()
  await entrepriseStore.loadCompletion()
  completionLoaded.value = true
  await startIfPending()
})
</script>

<template>
  <EmptyStateLanding v-if="showEmptyState" />
  <section v-else class="p-6">
    <h1 class="text-2xl font-bold">Tableau de bord</h1>
    <p class="mt-2 text-gray-600">Page placeholder — KPI livrés par F31.</p>
    <FullscreenTourStep />
  </section>
</template>
