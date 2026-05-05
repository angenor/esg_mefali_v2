<script setup lang="ts">
// F45 T028 — Barre de filtres priorité / statut / responsable.
import { computed } from "vue"
import { useT } from "~/composables/useT"
import type {
  PlanFilters,
  Priority,
  ResponsibleOption,
  StepStatus,
} from "~/types/actionPlan"

interface Props {
  filters: PlanFilters
  responsibleOptions: ResponsibleOption[]
  hasActive?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "change", next: Partial<PlanFilters>): void
  (e: "reset"): void
}>()
const { t } = useT()

const PRIORITIES: Priority[] = ["haute", "moyenne", "basse"]
const STATUSES: StepStatus[] = ["todo", "doing", "done", "postponed"]

function togglePriority(p: Priority): void {
  const set = new Set(props.filters.priority)
  if (set.has(p)) set.delete(p)
  else set.add(p)
  emit("change", { priority: Array.from(set) })
}

function toggleStatus(s: StepStatus): void {
  const set = new Set(props.filters.status)
  if (set.has(s)) set.delete(s)
  else set.add(s)
  emit("change", { status: Array.from(set) })
}

function changeResponsible(e: Event): void {
  const v = (e.target as HTMLSelectElement).value
  emit("change", { responsibleUserId: v === "" ? null : v })
}

const showReset = computed(() => Boolean(props.hasActive))
</script>

<template>
  <section class="pa-filters" role="group" :aria-label="t('planAction.filters.title')">
    <div class="pa-filters__group" role="group" :aria-label="t('planAction.filters.priority.label')">
      <span class="pa-filters__label">{{ t("planAction.filters.priority.label") }}</span>
      <button
        v-for="p in PRIORITIES"
        :key="p"
        type="button"
        class="pa-filters__chip"
        :aria-pressed="filters.priority.includes(p)"
        @click="togglePriority(p)"
      >
        {{ t(`planAction.filters.priority.${p}`) }}
      </button>
    </div>
    <div class="pa-filters__group" role="group" :aria-label="t('planAction.filters.status.label')">
      <span class="pa-filters__label">{{ t("planAction.filters.status.label") }}</span>
      <button
        v-for="s in STATUSES"
        :key="s"
        type="button"
        class="pa-filters__chip"
        :aria-pressed="filters.status.includes(s)"
        @click="toggleStatus(s)"
      >
        {{ t(`planAction.filters.status.${s}`) }}
      </button>
    </div>
    <label v-if="responsibleOptions.length" class="pa-filters__group">
      <span class="pa-filters__label">{{ t("planAction.filters.responsible.label") }}</span>
      <select :value="filters.responsibleUserId ?? ''" @change="changeResponsible">
        <option value="">—</option>
        <option v-for="opt in responsibleOptions" :key="opt.id" :value="opt.id">
          {{ opt.label }}
        </option>
      </select>
    </label>
    <button v-if="showReset" type="button" class="pa-filters__reset" @click="emit('reset')">
      {{ t("planAction.filters.reset") }}
    </button>
  </section>
</template>

<style scoped>
.pa-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}
.pa-filters__group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-surface-subtle, #f9fafb);
  border-radius: var(--radius-md, 8px);
}
.pa-filters__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary, #4b5563);
}
.pa-filters__chip {
  border: 1px solid var(--color-border, #e5e7eb);
  background: white;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: var(--font-size-sm);
}
.pa-filters__chip[aria-pressed="true"] {
  background: var(--color-primary-100, #dbeafe);
  border-color: var(--color-primary-500, #3b82f6);
  color: var(--color-primary-700, #1d4ed8);
}
.pa-filters__reset {
  background: transparent;
  border: 0;
  color: var(--color-primary-600, #2563eb);
  cursor: pointer;
  text-decoration: underline;
}
</style>
