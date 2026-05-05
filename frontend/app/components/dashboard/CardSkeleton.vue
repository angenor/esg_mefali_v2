<script setup lang="ts">
// F44 T013 — Skeleton générique pour cartes dashboard (cf. C-COMP-6).
import { computed } from "vue"
import UiSkeleton from "~/components/ui/UiSkeleton.vue"
import { useReducedMotion } from "~/composables/useReducedMotion"

interface Props {
  lines?: number
  withChart?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  lines: 3,
  withChart: false,
})

const reducedMotion = useReducedMotion()
const animationClass = computed(() => (reducedMotion.value ? "no-pulse" : "pulse"))
</script>

<template>
  <div
    class="card-skeleton"
    :class="animationClass"
    aria-busy="true"
    aria-live="polite"
    data-testid="card-skeleton"
  >
    <UiSkeleton shape="line" width="60%" height="1.25rem" />
    <UiSkeleton :lines="props.lines" />
    <div v-if="props.withChart" class="card-skeleton__chart">
      <UiSkeleton shape="rect" width="100%" height="80px" />
    </div>
  </div>
</template>

<style scoped>
.card-skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem 0;
}
.card-skeleton.no-pulse :deep(.ui-skeleton) {
  animation: none;
}
.card-skeleton__chart {
  margin-top: 0.5rem;
}
</style>
