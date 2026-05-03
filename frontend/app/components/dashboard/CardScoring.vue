<script setup lang="ts">
// F44 T026 — Carte Scoring ESG (cf. C-COMP-3 Scoring).
import { computed } from "vue"
import UiCard from "~/components/ui/UiCard.vue"
import VizKPICard from "~/components/viz/VizKPICard.vue"
import VizRadarChart from "~/components/viz/VizRadarChart.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, ScoringCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<ScoringCardData>
}

const props = defineProps<Props>()
const { t } = useT()

const radarSeries = computed(() => {
  if (props.vm.kind !== "filled") return null
  return {
    axes: [
      t("dashboard.cards.scoring.axis_e"),
      t("dashboard.cards.scoring.axis_s"),
      t("dashboard.cards.scoring.axis_g"),
    ],
    datasets: [
      {
        label: props.vm.data.referentielCode,
        data: [props.vm.data.byAxis.e, props.vm.data.byAxis.s, props.vm.data.byAxis.g],
      },
    ],
  }
})
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-scoring">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.scoring.title") }}</h2>
    </template>

    <CardSkeleton v-if="props.vm.kind === 'loading'" :with-chart="true" :lines="2" />

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
        :label="t('dashboard.cards.scoring.score_label')"
        :value="props.vm.data.scoreGlobal"
        size="sm"
      />
      <VizRadarChart v-if="radarSeries" :series="radarSeries" size="sm" />
      <p class="card-meta">
        {{ props.vm.data.referentielCode }} v{{ props.vm.data.referentielVersion }} ·
        <span data-testid="source-count">
          {{ t("dashboard.cards.scoring.sources", { count: props.vm.data.sourceCount }) }}
        </span>
      </p>
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
.card-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted, #666);
  margin: 0;
}
</style>
