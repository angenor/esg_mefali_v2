<script setup lang="ts">
// F44 T057 [US7] — Carte Intermédiaires recommandés (mini-Leaflet 3 pins).
//
// Lazy-fetch /me/matching/recommendations?limit=3.
// L'isolation d'erreur est garantie par try/catch local (FR-020 / SC-010).
import { computed, onMounted, ref } from "vue"
import UiCard from "~/components/ui/UiCard.vue"
import VizLeafletMap from "~/components/viz/VizLeafletMap.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { MapPin } from "~/types/viz/chart"

interface Recommendation {
  id: string
  label: string
  type: "fond" | "banque" | "autre"
  lat: number
  lng: number
}

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

const { t } = useT()
const loading = ref(true)
const error = ref<string | null>(null)
const recommendations = ref<Recommendation[]>([])

async function fetchRecommendations(): Promise<void> {
  loading.value = true
  error.value = null
  const apiBase =
    (globalThis.useRuntimeConfig?.() as RuntimeConfigShape | undefined)?.public?.apiBase ?? ""
  const url = `${apiBase}/me/matching/recommendations?limit=3`
  const fetchFn = globalThis.$fetch as
    | (<T>(u: string, o?: Record<string, unknown>) => Promise<T>)
    | undefined
  try {
    if (!fetchFn) throw new Error("$fetch unavailable")
    const data = await fetchFn<{ items: Recommendation[] }>(url, { credentials: "include" })
    recommendations.value = data.items ?? []
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Erreur réseau"
  } finally {
    loading.value = false
  }
}

const pins = computed<MapPin[]>(() =>
  recommendations.value.map((r) => ({
    lat: r.lat,
    lng: r.lng,
    label: r.label,
    type: r.type,
  })),
)

onMounted(() => {
  void fetchRecommendations()
})
</script>

<template>
  <UiCard :aria-busy="loading || undefined" data-testid="card-intermediaires">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.intermediaires.title") }}</h2>
    </template>

    <CardSkeleton v-if="loading" :with-chart="true" :lines="1" />
    <CardErrorState
      v-else-if="error"
      :message="error"
      @retry="fetchRecommendations"
    />
    <EmptyCardCTA
      v-else-if="recommendations.length === 0"
      :cta="{ label: t('dashboard.cards.intermediaires.empty_cta'), href: '/matching' }"
      :message="t('dashboard.cards.intermediaires.empty_message')"
    />
    <div v-else class="card-intermediaires">
      <VizLeafletMap :pins="pins" height="160px" />
      <NuxtLink to="/matching" class="card-intermediaires__see-all" data-testid="see-all-matching">
        {{ t("dashboard.cards.intermediaires.see_all") }}
      </NuxtLink>
    </div>
  </UiCard>
</template>

<style scoped>
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.card-intermediaires {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.card-intermediaires__see-all {
  font-size: 0.8rem;
  color: var(--color-primary, #0a7d4d);
  text-decoration: none;
  align-self: flex-end;
}
</style>
