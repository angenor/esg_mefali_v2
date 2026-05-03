<script setup lang="ts">
// F44 T027 — Carte Empreinte carbone (cf. C-COMP-3 Carbon).
import { computed } from "vue"
import UiCard from "~/components/ui/UiCard.vue"
import VizKPICard from "~/components/viz/VizKPICard.vue"
import VizLineChart from "~/components/viz/VizLineChart.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, CarbonCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<CarbonCardData>
}

const props = defineProps<Props>()
const { t } = useT()

const trendSeries = computed(() => {
  if (props.vm.kind !== "filled" || props.vm.data.trend.length === 0) return null
  return [
    {
      label: t("dashboard.cards.carbon.kpi_label"),
      points: props.vm.data.trend.map((q) => ({ x: q.quarter, y: Number(q.tco2e) })),
    },
  ]
})
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-carbon">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.carbon.title") }}</h2>
    </template>

    <CardSkeleton v-if="props.vm.kind === 'loading'" :with-chart="true" />

    <EmptyCardCTA
      v-else-if="props.vm.kind === 'empty'"
      :cta="props.vm.cta"
      :message="props.vm.message"
    />

    <CardErrorState
      v-else-if="props.vm.kind === 'error'"
      :message="props.vm.message"
      @retry="props.vm.retry"
    />

    <NuxtLink v-else :to="props.vm.data.href" class="card-link">
      <VizKPICard
        :label="t('dashboard.cards.carbon.kpi_label')"
        :value="props.vm.data.totalAnnualTco2e"
        :unit="String(props.vm.data.year)"
        size="sm"
      />
      <VizLineChart v-if="trendSeries" :series="trendSeries" size="sm" />
    </NuxtLink>
  </UiCard>
</template>

<style scoped>
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.card-link {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  text-decoration: none;
  color: inherit;
}
</style>
