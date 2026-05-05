<script setup lang="ts">
// F46 T073 [US6] — Bouton "Recalculer" avec spinner et anti double-clic.
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §RecalcButton.
import { computed } from "vue"
import { useScoringStore } from "~/stores/scoring"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"

interface Props {
  referentielCode: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), { disabled: false })

const store = useScoringStore()
const toast = useToast()
const { t } = useT()

const isRecomputing = computed<boolean>(
  () => store.recomputingByRef[props.referentielCode] === true,
)
const buttonDisabled = computed<boolean>(
  () => props.disabled || isRecomputing.value,
)

async function onClick(): Promise<void> {
  if (buttonDisabled.value) return
  try {
    await store.recompute(props.referentielCode)
    toast.push({
      severity: "success",
      message: t("scoring.recalc.success"),
      duration: 3000,
    })
  } catch (err: unknown) {
    if (err instanceof Error && err.message === "already_recomputing") return
    const reason = err instanceof Error ? err.message : "unknown"
    toast.push({
      severity: "error",
      message: t("scoring.errors.recomputeFailed", { reason }),
      duration: 5000,
    })
  }
}
</script>

<template>
  <button
    type="button"
    class="recalc-btn"
    data-testid="recalc-button"
    :disabled="buttonDisabled"
    :aria-busy="isRecomputing"
    @click="onClick"
  >
    <span v-if="isRecomputing" class="recalc-btn__spinner" aria-hidden="true" />
    <span>{{ t("scoring.buttons.recalc") }}</span>
  </button>
</template>

<style scoped>
.recalc-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  font-family: inherit;
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 500;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-primary, #3b82f6);
  background: var(--color-primary, #3b82f6);
  color: #fff;
  cursor: pointer;
  min-height: 36px;
}
.recalc-btn:hover:not(:disabled) {
  background: var(--color-primary-600, #2563eb);
}
.recalc-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.recalc-btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
.recalc-btn__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  border-top-color: #fff;
  border-radius: 50%;
  animation: recalc-spin 800ms linear infinite;
}
@media (prefers-reduced-motion: reduce) {
  .recalc-btn__spinner { animation: none; }
}
@keyframes recalc-spin {
  to { transform: rotate(360deg); }
}
</style>
