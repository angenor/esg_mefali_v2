<script setup lang="ts">
// F44 T028 — Carte Score crédit vert (cf. C-COMP-3 Credit).
import UiCard from "~/components/ui/UiCard.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import VizGaugeChart from "~/components/viz/VizGaugeChart.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, CreditCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<CreditCardData>
}

const props = defineProps<Props>()
const { t } = useT()
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-credit">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.credit.title") }}</h2>
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
      <VizGaugeChart :value="props.vm.data.combineScore" :min="0" :max="100" size="sm" />
      <div class="card-credit__badges">
        <UiBadge
          v-for="badge in props.vm.data.eligibilityBadges"
          :key="badge"
          severity="success"
          data-testid="eligibility-badge"
        >
          {{ badge }}
        </UiBadge>
        <UiBadge v-if="props.vm.data.coherenceWarning" severity="warning" data-testid="coherence-warning">
          {{ t("dashboard.cards.credit.coherence_warning") }}
        </UiBadge>
      </div>
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
  gap: 0.75rem;
  text-decoration: none;
  color: inherit;
}
.card-credit__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
