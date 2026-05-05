<script setup lang="ts">
// F44 T037 — Carte Plan d'action (US2) avec checkbox "marquer comme terminée".
//
// - Optimistic update : étape grisée + spinner mini pendant le PATCH.
// - Erreur 5xx : revert visuel + toast (gestion via useActionStepToggle).
// - Émet `action_step:completed` sur le bus avec source: 'dashboard' ; le
//   garde-fou anti-loop (registre bus + summary) évite le double-fetch.
import { ref } from "vue"
import UiCard from "~/components/ui/UiCard.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import { useActionStepToggle } from "~/composables/useActionStepToggle"
import type { CardKind, ActionPlanCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<ActionPlanCardData>
}

const props = defineProps<Props>()
const { t } = useT()
const { pendingId, complete } = useActionStepToggle()

// Set local des étapes "optimistically completed" (masquées pendant la requête,
// rétablies si erreur). Indépendant du store pour éviter de polluer.
const completedLocal = ref<Set<string>>(new Set())

const PRIORITY_TO_SEVERITY: Record<"haute" | "moyenne" | "basse", "error" | "warning" | "info"> = {
  haute: "error",
  moyenne: "warning",
  basse: "info",
}

function formatDate(d: Date): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(d)
}

async function onComplete(stepId: string): Promise<void> {
  if (completedLocal.value.has(stepId)) return
  completedLocal.value.add(stepId)
  try {
    await complete(stepId)
    // Succès : on garde l'étape masquée jusqu'au refresh du store qui rendra
    // le nouveau VM (sans cette étape). Pas de cleanup nécessaire.
  } catch {
    // Revert : retirer du set pour réafficher l'étape.
    completedLocal.value.delete(stepId)
  }
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
      <li
        v-for="step in props.vm.data.steps"
        :key="step.id"
        :class="{ 'is-completing': completedLocal.has(step.id) }"
        :aria-busy="pendingId === step.id || undefined"
        data-testid="action-step"
      >
        <label class="card-action-plan__row">
          <input
            type="checkbox"
            :checked="completedLocal.has(step.id)"
            :disabled="completedLocal.has(step.id)"
            :aria-label="t('dashboard.cards.action_plan.complete_aria')"
            data-testid="action-step-check"
            @change="onComplete(step.id)"
          />
          <span class="card-action-plan__title">{{ step.title }}</span>
          <span
            v-if="pendingId === step.id"
            class="card-action-plan__spinner"
            role="status"
            aria-live="polite"
            data-testid="action-step-spinner"
          />
        </label>
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
  transition: opacity 0.15s ease-out;
}
.card-action-plan__list li.is-completing {
  opacity: 0.5;
}
.card-action-plan__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}
.card-action-plan__title {
  font-size: 0.875rem;
  font-weight: 500;
  flex: 1;
}
.card-action-plan__spinner {
  width: 0.875rem;
  height: 0.875rem;
  border: 2px solid var(--color-border, #ddd);
  border-top-color: var(--color-primary, #0a7d4d);
  border-radius: 50%;
  animation: card-action-plan__spin 0.7s linear infinite;
}
@media (prefers-reduced-motion: reduce) {
  .card-action-plan__spinner {
    animation: none;
  }
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
@keyframes card-action-plan__spin {
  to { transform: rotate(360deg); }
}
</style>
