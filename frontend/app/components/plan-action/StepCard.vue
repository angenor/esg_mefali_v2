<script setup lang="ts">
// F45 T035 — Card d'une étape du plan d'action.
import { computed } from "vue"
import { useT } from "~/composables/useT"
import UiBadge from "~/components/ui/UiBadge.vue"
import type { StepCardViewModel } from "~/types/actionPlan"

interface Props {
  step: StepCardViewModel
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "toggle-status", id: string, next: "todo" | "done"): void
  (e: "open-edit", id: string): void
  (e: "open-source", indicateurId: string): void
}>()

const { t } = useT()

const checked = computed(() => props.step.status === "done")
const priorityToSeverity = computed(() => {
  switch (props.step.priorityTone) {
    case "danger":
      return "error"
    case "warning":
      return "warning"
    default:
      return "info"
  }
})

function onCheckboxChange(e: Event): void {
  if (props.step.isLoading) return
  const target = e.target as HTMLInputElement
  emit("toggle-status", props.step.id, target.checked ? "done" : "todo")
}

function onSourceClick(e: MouseEvent): void {
  if (!props.step.indicateurId) return
  e.preventDefault()
  emit("open-source", props.step.indicateurId)
}
</script>

<template>
  <article
    class="pa-step"
    :data-status="step.status"
    :aria-busy="step.isLoading || undefined"
    :data-loading="step.isLoading || undefined"
  >
    <header class="pa-step__header">
      <label class="pa-step__check">
        <input
          type="checkbox"
          :checked="checked"
          :disabled="step.isLoading"
          :aria-label="checked ? t('planAction.card.toggleTodo') : t('planAction.card.toggleDone')"
          @change="onCheckboxChange"
        />
      </label>
      <h3 class="pa-step__title">{{ step.title }}</h3>
      <UiBadge :severity="priorityToSeverity">{{ step.priorityLabel }}</UiBadge>
    </header>

    <p v-if="step.description" class="pa-step__desc">{{ step.description }}</p>
    <p v-else class="pa-step__desc pa-step__desc--muted">
      {{ t("planAction.card.notProvided") }}
    </p>

    <dl class="pa-step__meta">
      <div>
        <dt>{{ t("planAction.editSheet.statusLabel") }}</dt>
        <dd>{{ step.statusLabel }}</dd>
      </div>
      <div>
        <dt>{{ t("planAction.card.horizonRelative", { n: 0 }) }}</dt>
        <dd>{{ step.horizonRelative }}</dd>
      </div>
      <div>
        <dt>{{ t("planAction.editSheet.responsibleLabel") }}</dt>
        <dd>{{ step.responsibleLabel }}</dd>
      </div>
    </dl>

    <footer class="pa-step__footer">
      <a
        v-if="step.sourceLink"
        :href="step.sourceLink.href"
        class="pa-step__source"
        @click="onSourceClick"
      >
        {{ step.sourceLink.label }}
      </a>
      <span v-else class="pa-step__source pa-step__source--muted">
        {{ t("planAction.card.sourceUnavailable") }}
      </span>
      <button
        type="button"
        class="pa-step__edit"
        aria-haspopup="dialog"
        @click="emit('open-edit', step.id)"
      >
        {{ t("planAction.card.editStatus") }}
      </button>
    </footer>

    <p v-if="step.error" class="pa-step__error" role="alert">
      {{ step.error }}
    </p>
  </article>
</template>

<style scoped>
.pa-step {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-lg, 12px);
  background: white;
}
.pa-step[data-loading] { opacity: 0.7; }
.pa-step__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.pa-step__title {
  margin: 0;
  font-size: var(--font-size-md);
  flex: 1;
}
.pa-step__desc {
  margin: 0;
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--font-size-sm);
}
.pa-step__desc--muted { font-style: italic; opacity: 0.7; }
.pa-step__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-xs);
}
.pa-step__meta dt {
  color: var(--color-text-secondary, #6b7280);
}
.pa-step__meta dd { margin: 0; font-weight: var(--font-weight-medium); }
.pa-step__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.pa-step__source {
  color: var(--color-primary-600, #2563eb);
  text-decoration: underline;
  font-size: var(--font-size-sm);
}
.pa-step__source--muted {
  color: var(--color-text-secondary, #6b7280);
  text-decoration: none;
  font-style: italic;
}
.pa-step__edit {
  background: transparent;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-sm, 6px);
  padding: 4px 10px;
  cursor: pointer;
}
.pa-step__error {
  margin: 0;
  color: var(--color-danger-700, #b91c1c);
  font-size: var(--font-size-xs);
}
</style>
