<script setup lang="ts">
// F45 T049 — Toggle horizon affiché (6 / 12 / 24 mois).
import { useT } from "~/composables/useT"
import type { Horizon } from "~/types/actionPlan"

interface Props {
  modelValue: Horizon
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "update:modelValue", v: Horizon): void
}>()

const { t } = useT()
const HORIZONS: Horizon[] = [6, 12, 24]

function pick(h: Horizon): void {
  if (h === props.modelValue) return
  emit("update:modelValue", h)
}
</script>

<template>
  <div class="pa-horizon" role="tablist" :aria-label="t('planAction.horizonToggle.label')">
    <button
      v-for="h in HORIZONS"
      :key="h"
      type="button"
      role="tab"
      class="pa-horizon__btn"
      :aria-pressed="modelValue === h"
      :aria-selected="modelValue === h"
      :data-active="modelValue === h || undefined"
      @click="pick(h)"
    >
      {{ t(`planAction.horizonToggle.options.${h}` as const) }}
    </button>
  </div>
</template>

<style scoped>
.pa-horizon {
  display: inline-flex;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 999px;
  padding: 2px;
  background: var(--color-surface-subtle, #f9fafb);
}
.pa-horizon__btn {
  border: 0;
  background: transparent;
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--font-size-sm);
  min-height: 36px;
}
.pa-horizon__btn[data-active] {
  background: var(--color-primary-600, #2563eb);
  color: white;
  font-weight: var(--font-weight-medium);
}
</style>
