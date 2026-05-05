<script setup lang="ts">
import { ref } from 'vue'
import type { UiSeverity } from '~/types/ui'

interface Props {
  id?: string
  severity?: UiSeverity
  title?: string
  message: string
  duration?: number
  actionLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  id: undefined,
  severity: 'info',
  title: undefined,
  duration: 5000,
  actionLabel: undefined,
})

const emit = defineEmits<{
  (e: 'dismiss', id: string | undefined): void
  (e: 'action', id: string | undefined): void
}>()

const dragX = ref(0)
let pointerStartX: number | null = null

function onPointerDown(e: PointerEvent): void {
  pointerStartX = e.clientX
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent): void {
  if (pointerStartX === null) return
  dragX.value = e.clientX - pointerStartX
}

function onPointerUp(): void {
  if (Math.abs(dragX.value) > 80) {
    emit('dismiss', props.id)
  }
  pointerStartX = null
  dragX.value = 0
}
</script>

<template>
  <div
    :role="severity === 'error' ? 'alert' : 'status'"
    :aria-live="severity === 'error' ? 'assertive' : 'polite'"
    class="ui-toast"
    :data-severity="severity"
    :style="{ transform: `translateX(${dragX}px)` }"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  >
    <div class="ui-toast__body">
      <strong v-if="title" class="ui-toast__title">{{ title }}</strong>
      <span class="ui-toast__msg">
        <slot>{{ message }}</slot>
      </span>
    </div>
    <button
      v-if="actionLabel"
      type="button"
      class="ui-toast__action"
      @click="emit('action', id)"
    >
      <slot name="action">{{ actionLabel }}</slot>
    </button>
    <button type="button" aria-label="Fermer" class="ui-toast__close" @click="emit('dismiss', id)">
      ×
    </button>
  </div>
</template>

<style scoped>
.ui-toast {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  pointer-events: auto;
  font-family: var(--font-sans);
  color: var(--color-text);
  min-width: 18rem;
  touch-action: pan-y;
}
.ui-toast[data-severity='error'] { border-color: var(--color-danger-500); }
.ui-toast[data-severity='success'] { border-color: var(--color-success-500); }
.ui-toast[data-severity='warning'] { border-color: var(--color-warning-500); }
.ui-toast__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.ui-toast__title {
  font-weight: var(--font-weight-medium);
}
.ui-toast__msg {
  font-size: var(--font-size-sm);
}
.ui-toast__action {
  background: none;
  border: 0;
  cursor: pointer;
  color: var(--color-brand-600);
  font-weight: var(--font-weight-medium);
}
.ui-toast__close {
  background: none;
  border: 0;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: var(--font-size-lg);
  min-width: 24px;
  min-height: 24px;
}
.ui-toast__close:focus-visible,
.ui-toast__action:focus-visible {
  outline: 2px solid var(--color-focus-ring);
}
</style>
