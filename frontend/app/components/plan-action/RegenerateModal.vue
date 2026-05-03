<script setup lang="ts">
// F45 T045 — Modale de confirmation de régénération du plan d'action.
//
// Réutilise <UiModal> (focus trap + Esc + clic extérieur + role="dialog").
import { ref, watch } from "vue"
import UiModal from "~/components/ui/UiModal.vue"
import { useT } from "~/composables/useT"
import type { Horizon } from "~/types/actionPlan"

interface Props {
  open: boolean
  defaultHorizon: Horizon
  busy: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "confirm", horizon: Horizon): void
  (e: "cancel"): void
}>()

const { t } = useT()
const HORIZONS: Horizon[] = [6, 12, 24]
const selected = ref<Horizon>(props.defaultHorizon)

watch(
  () => [props.open, props.defaultHorizon] as const,
  ([open, h]) => {
    if (open) selected.value = h
  },
)

function onConfirm(): void {
  if (props.busy) return
  emit("confirm", selected.value)
}

function onCancel(): void {
  emit("cancel")
}

function onModelUpdate(v: boolean): void {
  if (!v) onCancel()
}
</script>

<template>
  <UiModal
    :model-value="open"
    size="sm"
    :persistent="busy"
    :aria-label="t('planAction.regenerate.modal.title')"
    @update:model-value="onModelUpdate"
    @close="onCancel"
  >
    <template #header>
      <h2 class="pa-regen__title">{{ t("planAction.regenerate.modal.title") }}</h2>
    </template>

    <p class="pa-regen__warning" role="note">
      {{ t("planAction.regenerate.modal.warning") }}
    </p>

    <fieldset class="pa-regen__horizons">
      <legend>{{ t("planAction.regenerate.modal.horizonLabel") }}</legend>
      <label v-for="h in HORIZONS" :key="h" class="pa-regen__horizon">
        <input
          type="radio"
          name="pa-regen-horizon"
          :value="h"
          :checked="selected === h"
          :disabled="busy"
          @change="selected = h"
        />
        {{ t(`planAction.horizonToggle.options.${h}` as const) }}
      </label>
    </fieldset>

    <template #footer>
      <button
        type="button"
        class="pa-regen__cancel"
        :disabled="busy"
        @click="onCancel"
      >
        {{ t("planAction.regenerate.modal.cancel") }}
      </button>
      <button
        type="button"
        class="pa-regen__confirm"
        :disabled="busy"
        :aria-busy="busy || undefined"
        @click="onConfirm"
      >
        {{ t("planAction.regenerate.modal.confirm") }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.pa-regen__title {
  margin: 0;
  font-size: var(--font-size-lg);
}
.pa-regen__warning {
  margin: 0 0 var(--space-3) 0;
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--font-size-sm);
}
.pa-regen__horizons {
  border: 0;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.pa-regen__horizons legend {
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--space-2);
}
.pa-regen__horizon {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}
.pa-regen__cancel,
.pa-regen__confirm {
  border-radius: var(--radius-md, 8px);
  padding: 6px 14px;
  cursor: pointer;
  border: 1px solid var(--color-border, #e5e7eb);
  background: white;
}
.pa-regen__confirm {
  background: var(--color-primary-600, #2563eb);
  border-color: var(--color-primary-600, #2563eb);
  color: white;
}
.pa-regen__confirm[disabled],
.pa-regen__cancel[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
