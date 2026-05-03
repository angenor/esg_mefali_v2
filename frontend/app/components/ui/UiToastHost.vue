<script setup lang="ts">
import { useToast } from '~/composables/useToast'
import UiToast from './UiToast.vue'

const { toasts, dismiss } = useToast()

function onAction(id: string): void {
  const t = toasts.value.find((x) => x.id === id)
  t?.onAction?.()
  dismiss(id)
}
</script>

<template>
  <Teleport to="body">
    <div
      role="region"
      aria-label="Notifications"
      class="ui-toast-host"
      :data-count="toasts.length"
    >
      <UiToast
        v-for="t in toasts"
        :key="t.id"
        :id="t.id"
        :severity="t.severity"
        :title="t.title"
        :message="t.message"
        :duration="t.duration"
        :action-label="t.actionLabel"
        @dismiss="(id) => id && dismiss(id)"
        @action="(id) => id && onAction(id)"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.ui-toast-host {
  position: fixed;
  inset: auto var(--space-4) var(--space-4) auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  z-index: 9999;
  pointer-events: none;
  max-width: min(100% - 2rem, 24rem);
}
</style>
