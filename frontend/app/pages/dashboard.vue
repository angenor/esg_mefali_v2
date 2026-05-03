<script setup lang="ts">
// F38 T017 — page stub PME.
// F42 T037 — déclenche le tour onboarding si state=pending au mount.
// F42 T063 — affiche EmptyStateLanding si profil entreprise < 50 %.
// F44 T031 — Dashboard 6 cartes (US1 MVP) au-delà de 50 % completion.
import { computed, onMounted, ref } from "vue"
import { useOnboardingTour } from "~/composables/useOnboardingTour"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useDashboardSummary } from "~/composables/useDashboardSummary"
import FullscreenTourStep from "~/components/onboarding/FullscreenTourStep.vue"
import EmptyStateLanding from "~/components/onboarding/EmptyStateLanding.vue"
import WelcomeStrip from "~/components/dashboard/WelcomeStrip.vue"
import DashboardGrid from "~/components/dashboard/DashboardGrid.vue"
import CardScoring from "~/components/dashboard/CardScoring.vue"
import CardCarbon from "~/components/dashboard/CardCarbon.vue"
import CardCredit from "~/components/dashboard/CardCredit.vue"
import CardCandidatures from "~/components/dashboard/CardCandidatures.vue"
import CardRapports from "~/components/dashboard/CardRapports.vue"
import CardActionPlan from "~/components/dashboard/CardActionPlan.vue"
import ExportButton from "~/components/dashboard/ExportButton.vue"
import CardIntermediaires from "~/components/dashboard/CardIntermediaires.vue"
import { useProjetsStore } from "~/stores/projets"

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

const raisonSociale = computed<string>(
  () => entrepriseStore.data?.raison_sociale ?? "",
)

const projetsStore = useProjetsStore()
const hasProjet = computed<boolean>(() => projetsStore.activeList.length > 0)

// Branchement dashboard summary (fetch + polling + sync EventBus).
const { vms, summary } = useDashboardSummary({ hasProjet: hasProjet.value })

const lastDiagnosticAt = computed<Date | null>(() => {
  const scores = summary.value?.scores ?? []
  if (scores.length === 0) return null
  const latest = scores.reduce((acc, s) =>
    new Date(s.computed_at).getTime() > new Date(acc.computed_at).getTime() ? s : acc,
  )
  return new Date(latest.computed_at)
})

onMounted(async () => {
  await nextTick()
  await entrepriseStore.loadCompletion()
  if (entrepriseStore.data === null && typeof entrepriseStore.loadAll === "function") {
    await entrepriseStore.loadAll().catch(() => {})
  }
  // Charge la liste de projets pour décider d'afficher la carte intermédiaires.
  if (typeof projetsStore.loadList === "function") {
    await projetsStore.loadList().catch(() => {})
  }
  completionLoaded.value = true
  await startIfPending()
})
</script>

<template>
  <EmptyStateLanding v-if="showEmptyState" />
  <section v-else class="dashboard-page">
    <header class="dashboard-page__header">
      <WelcomeStrip :raison-sociale="raisonSociale" :last-diagnostic-at="lastDiagnosticAt" />
      <ExportButton />
    </header>
    <DashboardGrid>
      <CardScoring :vm="vms.scoring" />
      <CardCarbon :vm="vms.carbon" />
      <CardCredit :vm="vms.credit" />
      <CardCandidatures :vm="vms.candidatures" />
      <CardRapports :vm="vms.rapports" />
      <CardActionPlan :vm="vms.actionPlan" />
      <CardIntermediaires v-if="hasProjet" />
    </DashboardGrid>
    <FullscreenTourStep />
  </section>
</template>

<style scoped>
.dashboard-page {
  padding: 1.5rem 1rem;
  max-width: 1400px;
  margin: 0 auto;
}
.dashboard-page__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
</style>
