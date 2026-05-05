<!-- F40 T021 — État loading partagé : skeleton shimmer + reduced-motion respecté. -->
<script setup lang="ts">
import { computed } from 'vue'
import { useReducedMotion } from '~/composables/useReducedMotion'

interface Props {
  height?: string
  ariaLabel?: string
}
const props = withDefaults(defineProps<Props>(), {
  height: '8rem',
  ariaLabel: 'Chargement en cours',
})
const reduced = useReducedMotion()
const shimmerClass = computed(() => (reduced.value ? 'viz-skeleton' : 'viz-skeleton viz-skeleton--shimmer'))
</script>

<template>
  <div
    :class="shimmerClass"
    :style="{ height: props.height }"
    role="status"
    :aria-label="props.ariaLabel"
    aria-live="polite"
  >
    <span class="sr-only">{{ props.ariaLabel }}</span>
  </div>
</template>

<style scoped>
.viz-skeleton {
  width: 100%;
  background: var(--color-neutral-100, #f5f5f5);
  border-radius: 0.5rem;
  position: relative;
  overflow: hidden;
}
.viz-skeleton--shimmer::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.6) 50%,
    transparent 100%
  );
  animation: viz-skeleton-sweep 1.4s linear infinite;
}
@keyframes viz-skeleton-sweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
