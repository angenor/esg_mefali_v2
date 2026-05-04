<script setup lang="ts">
// F46 T028 [US1] — Empty state : aucun calcul de score pour ce référentiel.
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §EmptyNoCalculation.
import UiEmptyState from "~/components/ui/UiEmptyState.vue"
import { useT } from "~/composables/useT"

interface Props {
  referentielCode: string
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  (e: "start"): void
}>()

const { t } = useT()

function onStart(): void {
  emit("start")
}
</script>

<template>
  <UiEmptyState
    severity="info"
    :title="t('scoring.buttons.startDiagnostic')"
    :description="t('scoring.empty.noCalculation')"
    data-testid="scoring-empty-no-calc"
  >
    <template #action>
      <button
        type="button"
        class="empty-no-calc__cta"
        :disabled="loading"
        :aria-busy="loading"
        data-testid="scoring-empty-no-calc-cta"
        @click="onStart"
      >
        {{ t("scoring.buttons.startDiagnostic") }}
      </button>
    </template>
  </UiEmptyState>
</template>

<style scoped>
.empty-no-calc__cta {
  background: var(--color-brand-500, #16a34a);
  color: #fff;
  border: 0;
  border-radius: var(--radius-md, 8px);
  padding: 8px 16px;
  cursor: pointer;
  min-height: 44px;
  font-size: var(--font-size-sm);
}
.empty-no-calc__cta:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.empty-no-calc__cta:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
</style>
