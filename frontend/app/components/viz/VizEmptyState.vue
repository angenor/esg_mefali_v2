<!-- F40 T022 — EmptyState partagé : illustration sobre + message FR par défaut. -->
<script setup lang="ts">
interface Props {
  message?: string
  height?: string
}
const props = withDefaults(defineProps<Props>(), {
  message: 'Aucune donnée disponible',
  height: '8rem',
})
</script>

<template>
  <div
    class="viz-empty"
    :style="{ minHeight: props.height }"
    role="status"
    aria-live="polite"
  >
    <svg
      class="viz-empty__icon"
      viewBox="0 0 24 24"
      width="32"
      height="32"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5zm2 0v14h14V5H5zm2 4h10v2H7V9zm0 4h6v2H7v-2z"
        opacity="0.5"
      />
    </svg>
    <p class="viz-empty__message">{{ props.message }}</p>
  </div>
</template>

<style scoped>
.viz-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--color-neutral-500, #737373);
  background: var(--color-neutral-50, #fafafa);
  border-radius: 0.5rem;
}
.viz-empty__icon { color: var(--color-neutral-400, #a3a3a3); }
.viz-empty__message { margin: 0; font-size: 0.875rem; text-align: center; }
</style>
