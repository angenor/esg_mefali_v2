<script setup lang="ts">
// F44 T031 (placeholder) — Carte Plan d'action — version statique pour US1.
// La logique de toggle (cocher étape avec PATCH backend) sera ajoutée en US2 (T036/T037).
import UiCard from "~/components/ui/UiCard.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, ActionPlanCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<ActionPlanCardData>
}

const props = defineProps<Props>()
const { t } = useT()

const PRIORITY_TO_SEVERITY: Record<"haute" | "moyenne" | "basse", "error" | "warning" | "info"> = {
  haute: "error",
  moyenne: "warning",
  basse: "info",
}

function formatDate(d: Date): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(d)
}
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-action-plan">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.action_plan.title") }}</h2>
    </template>

    <CardSkeleton v-if="props.vm.kind === 'loading'" :lines="4" />
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
    <ul v-else class="card-action-plan__list">
      <li v-for="step in props.vm.data.steps" :key="step.id" data-testid="action-step">
        <span class="card-action-plan__title">{{ step.title }}</span>
        <div class="card-action-plan__meta">
          <UiBadge :severity="PRIORITY_TO_SEVERITY[step.priority]">
            {{ t(`dashboard.cards.action_plan.priority_${step.priority}`) }}
          </UiBadge>
          <span class="card-action-plan__horizon">{{ formatDate(step.horizonAt) }}</span>
        </div>
      </li>
    </ul>
  </UiCard>
</template>

<style scoped>
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.card-action-plan__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.card-action-plan__list li {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem;
  border-radius: 0.375rem;
  background: var(--color-surface-soft, rgba(0, 0, 0, 0.02));
}
.card-action-plan__title {
  font-size: 0.875rem;
  font-weight: 500;
}
.card-action-plan__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.card-action-plan__horizon {
  font-size: 0.75rem;
  color: var(--color-text-muted, #666);
}
</style>
