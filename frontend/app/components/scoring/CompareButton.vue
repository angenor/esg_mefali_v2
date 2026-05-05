<script setup lang="ts">
// F46 T043 [US2] — Bouton "Comparer" qui ouvre <CompareDrawer>.
import { computed, ref } from "vue"
import CompareDrawer from "~/components/scoring/CompareDrawer.vue"
import { useScoringStore } from "~/stores/scoring"
import { useT } from "~/composables/useT"

interface Props {
  disabled?: boolean
}

withDefaults(defineProps<Props>(), { disabled: false })

const { t } = useT()
const store = useScoringStore()

const open = ref<boolean>(false)

const summaries = computed(() => Object.values(store.summariesByRef))
const defaultSelected = computed<string[]>(() =>
  store.currentReferentielCode ? [store.currentReferentielCode] : [],
)

function onOpen(): void {
  open.value = true
}

function onClose(): void {
  open.value = false
}
</script>

<template>
  <button
    type="button"
    class="compare-btn"
    data-testid="compare-button"
    :disabled="disabled || summaries.length < 2"
    @click="onOpen"
  >
    {{ t("scoring.buttons.compare") }}
  </button>
  <CompareDrawer
    :available-summaries="summaries"
    :default-selected="defaultSelected"
    :open="open"
    @close="onClose"
  />
</template>

<style scoped>
.compare-btn {
  font-family: inherit;
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 500;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  background: var(--color-surface, #fff);
  cursor: pointer;
  transition: background 120ms;
}
.compare-btn:hover:not(:disabled) {
  background: var(--color-neutral-50, #fafafa);
}
.compare-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
