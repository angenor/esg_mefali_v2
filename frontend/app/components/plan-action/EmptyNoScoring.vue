<script setup lang="ts">
// F45 T053 — Empty state : pas encore de scoring.
import UiEmptyState from "~/components/ui/UiEmptyState.vue"
import { useT } from "~/composables/useT"

const { t } = useT()

const emit = defineEmits<{
  (e: "navigate"): void
}>()

function onAction(): void {
  emit("navigate")
}
</script>

<template>
  <UiEmptyState
    severity="info"
    :title="t('planAction.empty.noScoring.title')"
    :description="t('planAction.empty.noScoring.body')"
    @action="onAction"
  >
    <template #action>
      <NuxtLink to="/scoring" class="pa-empty__cta" data-testid="pa-empty-no-scoring-cta">
        {{ t("planAction.empty.noScoring.cta") }}
      </NuxtLink>
    </template>
  </UiEmptyState>
</template>

<style scoped>
.pa-empty__cta {
  display: inline-block;
  background: var(--color-primary-600, #2563eb);
  color: white;
  padding: 8px 16px;
  border-radius: var(--radius-md, 8px);
  text-decoration: none;
  min-height: 44px;
  line-height: 28px;
}
.pa-empty__cta:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
</style>
