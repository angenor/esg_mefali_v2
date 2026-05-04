<script setup lang="ts">
// F46 T031 [US1] — Page entrée /scoring : redirige vers le référentiel courant
// (par défaut BOAD constitution) ou affiche l'empty state si aucun calcul.
import { computed, onMounted, ref } from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import EmptyNoCalculation from "~/components/scoring/EmptyNoCalculation.vue"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Scoring ESG" }],
  title: "Scoring ESG",
})

const DEFAULT_REFERENTIEL = "BOAD"

const store = useScoringStore()
const entreprise = useEntrepriseStore()
const router = useRouter()
const toast = useToast()
const { t } = useT()

const ready = ref<boolean>(false)
const recomputing = ref<boolean>(false)

const hasAnySummary = computed<boolean>(
  () => Object.keys(store.summariesByRef).length > 0,
)

const targetCode = computed<string>(() => {
  if (store.currentReferentielCode) return store.currentReferentielCode
  const refs = Object.keys(store.summariesByRef)
  return refs[0] ?? DEFAULT_REFERENTIEL
})

onMounted(async () => {
  try {
    if (!entreprise.data) {
      await entreprise.loadAll()
    }
    const id = entreprise.data?.id
    if (id) {
      store.setEntity("entreprise", id)
      await store.loadSummaries()
    }
  } catch {
    toast.push({
      severity: "error",
      message: t("scoring.errors.loadFailed"),
      duration: 4000,
    })
  } finally {
    if (hasAnySummary.value) {
      await router.replace(`/scoring/${targetCode.value}`)
    }
    ready.value = true
  }
})

async function onStart(): Promise<void> {
  if (recomputing.value) return
  if (!entreprise.data?.id) return
  recomputing.value = true
  try {
    await store.recompute(DEFAULT_REFERENTIEL)
    await router.replace(`/scoring/${DEFAULT_REFERENTIEL}`)
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : "unknown"
    toast.push({
      severity: "error",
      message: t("scoring.errors.recomputeFailed", { reason }),
      duration: 5000,
    })
  } finally {
    recomputing.value = false
  }
}
</script>

<template>
  <section class="scoring-index" data-testid="scoring-index" :aria-busy="!ready">
    <h1 class="scoring-index__title">{{ t("scoring.pageTitle") }}</h1>
    <EmptyNoCalculation
      v-if="ready && !hasAnySummary"
      :referentiel-code="DEFAULT_REFERENTIEL"
      :loading="recomputing"
      @start="onStart"
    />
  </section>
</template>

<style scoped>
.scoring-index {
  padding: var(--space-6, 1.5rem);
  max-width: 1200px;
  margin: 0 auto;
}
.scoring-index__title {
  font-size: var(--font-size-2xl, 1.5rem);
  font-weight: 700;
  margin: 0 0 var(--space-4, 1rem);
}
</style>
