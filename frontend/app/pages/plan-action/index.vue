<script setup lang="ts">
// F45 T024-T070 — Page /plan-action (timeline + filtres + liste + progress
// + régénération + horizon toggle + empty states + export).
import { computed, ref } from "vue"
import { useActionPlan } from "~/composables/useActionPlan"
import { useActionPlanStore } from "~/stores/actionPlan"
import { useActionPlanFilters } from "~/composables/useActionPlanFilters"
import { useActionPlanCompletion } from "~/composables/useActionPlanCompletion"
import { useActionStepToggle } from "~/composables/useActionStepToggle"
import { useReducedMotion } from "~/composables/useReducedMotion"
import { useT } from "~/composables/useT"
import { useToast } from "~/composables/useToast"
import { useChatEventBus } from "~/composables/useChatEventBus"
import {
  TIMELINE_BUCKET_LABELS,
  TIMELINE_BUCKET_ORDER,
  bucketOf,
} from "~/lib/mapPlanToTimelineBuckets"
import { mapStepToCardViewModel } from "~/lib/mapStepToCardViewModel"
import TimelineHorizontal from "~/components/plan-action/TimelineHorizontal.vue"
import StepFilters from "~/components/plan-action/StepFilters.vue"
import StepCard from "~/components/plan-action/StepCard.vue"
import EditStatusSheet from "~/components/plan-action/EditStatusSheet.vue"
import ProgressHeader from "~/components/plan-action/ProgressHeader.vue"
import RegenerateModal from "~/components/plan-action/RegenerateModal.vue"
import HorizonToggle from "~/components/plan-action/HorizonToggle.vue"
import EmptyNoScoring from "~/components/plan-action/EmptyNoScoring.vue"
import EmptyNoGaps from "~/components/plan-action/EmptyNoGaps.vue"
import ExportPlanButton from "~/components/plan-action/ExportPlanButton.vue"
import type {
  ActionStep,
  ActionStepPatchPayload,
  Horizon,
  StepCardViewModel,
  TimelineBucketViewModel,
} from "~/types/actionPlan"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Plan d'action" }],
  title: "Plan d'action",
})

const { t } = useT()
const { plan, loading, error, emptyKind } = useActionPlan()
const planStore = useActionPlanStore()
const { filters, setFilters, resetFilters, hasActive } = useActionPlanFilters()
const completion = useActionPlanCompletion()
const toggleApi = useActionStepToggle()
const { reducedMotion } = useReducedMotion()
const toast = useToast()
const chatBus = useChatEventBus()

const editingStepId = ref<string | null>(null)
const regenerateOpen = ref(false)

const editingStep = computed<ActionStep | null>(() => {
  const id = editingStepId.value
  if (!id || !plan.value) return null
  return plan.value.steps.find((s) => s.id === id) ?? null
})

const horizonView = computed<Horizon>({
  get: () => planStore.horizonView,
  set: (h: Horizon) => planStore.setHorizonView(h),
})

function ctxFor(step: ActionStep): StepCardViewModel {
  const ui = planStore.stepStates[step.id]
  return mapStepToCardViewModel(step, {
    generatedAt: plan.value?.generated_at ?? new Date().toISOString(),
    reducedMotion: reducedMotion.value,
    t,
    uiState: {
      loading: ui?.loading ?? false,
      error: ui?.error ?? null,
      overlay: ui?.optimisticOverlay ?? null,
    },
  })
}

const visibleViewModels = computed<StepCardViewModel[]>(() => {
  return planStore.visibleSteps
    .map(ctxFor)
    .sort((a, b) => {
      const prio = { haute: 0, moyenne: 1, basse: 2 }
      const dPrio =
        prio[a.priorityLabel.toLowerCase() as keyof typeof prio] -
          prio[b.priorityLabel.toLowerCase() as keyof typeof prio] || 0
      if (dPrio !== 0) return dPrio
      const ah = a.horizonAt ?? "9999-12-31"
      const bh = b.horizonAt ?? "9999-12-31"
      return ah.localeCompare(bh)
    })
})

const timelineBuckets = computed<TimelineBucketViewModel[]>(() => {
  if (!plan.value) return []
  const generatedAt = plan.value.generated_at
  const groups: Record<string, StepCardViewModel[]> = {
    lt3m: [],
    "3to6m": [],
    "6to12m": [],
    "12to24m": [],
    unscheduled: [],
  }
  for (const step of planStore.visibleSteps) {
    const b = bucketOf(step, generatedAt)
    groups[b]!.push(ctxFor(step))
  }
  return TIMELINE_BUCKET_ORDER.map((b) => ({
    bucket: b,
    label: TIMELINE_BUCKET_LABELS[b],
    rangeStart: null,
    rangeEnd: null,
    steps: groups[b] ?? [],
  }))
})

async function onToggle(stepId: string, nextStatus: "todo" | "done"): Promise<void> {
  try {
    await toggleApi.toggle(stepId, nextStatus)
  } catch {
    /* toast déjà émis dans toggle */
  }
}

function onEdit(stepId: string): void {
  editingStepId.value = stepId
}

function closeEdit(): void {
  editingStepId.value = null
}

async function onSubmitEdit(payload: ActionStepPatchPayload): Promise<void> {
  const id = editingStepId.value
  if (!id) return
  try {
    planStore.trackLocalEmit(id)
    await planStore.applyOptimisticPatch(id, payload)
    chatBus.emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_step",
      entityId: id,
      fieldsUpdated: Object.keys(payload),
      source: "manual",
      ts: new Date().toISOString(),
    })
    closeEdit()
  } catch {
    toast.push({ severity: "error", message: t("planAction.errors.editFailed") })
  }
}

async function onRegenerate(h: Horizon): Promise<void> {
  try {
    await planStore.regenerate(h)
    if (planStore.plan) {
      chatBus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "action_plan",
        entityId: planStore.plan.id,
        fieldsUpdated: ["version"],
        source: "manual",
        ts: new Date().toISOString(),
      })
    }
    regenerateOpen.value = false
  } catch {
    toast.push({ severity: "error", message: t("planAction.errors.regenerateFailed") })
  }
}

const responsibleOptions = computed(() => planStore.responsibleOptions)
const filteredOut = computed(
  () => plan.value !== null && plan.value.steps.length > 0 && visibleViewModels.value.length === 0,
)
</script>

<template>
  <main class="pa-page" data-testid="plan-action-page">
    <header class="pa-page__header">
      <h1>{{ t("planAction.title") }}</h1>
      <p class="pa-page__subtitle">{{ t("planAction.subtitle") }}</p>
    </header>

    <section v-if="loading && !plan" aria-busy="true" class="pa-page__loading">
      <p>Chargement…</p>
    </section>

    <template v-else-if="!plan && emptyKind === 'no_scoring'">
      <EmptyNoScoring />
    </template>

    <template v-else-if="!plan && emptyKind === 'no_gaps'">
      <EmptyNoGaps />
    </template>

    <section
      v-else-if="error && !plan && emptyKind === 'error'"
      role="alert"
      class="pa-page__error"
    >
      <p>{{ t("planAction.errors.loadFailed") }}</p>
    </section>

    <template v-else-if="plan">
      <ProgressHeader :stats="completion" :version="plan.version" />

      <div class="pa-page__actions">
        <HorizonToggle v-model="horizonView" />
        <button
          type="button"
          class="pa-page__regenerate"
          data-testid="pa-regenerate-cta"
          :disabled="planStore.regenerating"
          @click="regenerateOpen = true"
        >
          {{ t("planAction.regenerate.cta") }}
        </button>
        <ExportPlanButton />
      </div>

      <TimelineHorizontal
        :buckets="timelineBuckets"
        :reduced-motion="reducedMotion"
        @select-step="onEdit"
      />

      <StepFilters
        :filters="filters"
        :responsible-options="responsibleOptions"
        :has-active="hasActive"
        @change="setFilters"
        @reset="resetFilters"
      />

      <ul v-if="visibleViewModels.length" class="pa-page__list">
        <StepCard
          v-for="vm in visibleViewModels"
          :key="vm.id"
          :step="vm"
          @toggle-status="onToggle"
          @open-edit="onEdit"
        />
      </ul>

      <section v-if="filteredOut" class="pa-page__empty" role="status">
        <p>{{ t("planAction.empty.filteredOut.title") }}</p>
        <button type="button" @click="resetFilters">
          {{ t("planAction.empty.filteredOut.cta") }}
        </button>
      </section>
    </template>

    <EditStatusSheet
      :open="editingStepId !== null"
      :step="editingStep"
      :responsible-options="responsibleOptions"
      @submit="onSubmitEdit"
      @close="closeEdit"
    />

    <RegenerateModal
      :open="regenerateOpen"
      :default-horizon="plan?.horizon_months ?? 12"
      :busy="planStore.regenerating"
      @confirm="onRegenerate"
      @cancel="regenerateOpen = false"
    />
  </main>
</template>

<style scoped>
.pa-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}
.pa-page__header h1 {
  margin: 0;
  font-size: var(--font-size-2xl);
}
.pa-page__subtitle {
  margin: 0;
  color: var(--color-text-secondary, #4b5563);
}
.pa-page__actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex-wrap: wrap;
}
.pa-page__regenerate {
  border: 1px solid var(--color-primary-600, #2563eb);
  background: var(--color-primary-600, #2563eb);
  color: white;
  padding: 6px 14px;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: var(--font-size-sm);
  min-height: 36px;
}
.pa-page__regenerate[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}
.pa-page__list {
  list-style: none;
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  margin: 0;
  padding: 0;
}
.pa-page__empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-secondary, #4b5563);
}
.pa-page__loading,
.pa-page__error {
  padding: var(--space-4);
  text-align: center;
}
</style>
