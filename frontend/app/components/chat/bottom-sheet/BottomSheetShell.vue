<script setup lang="ts">
/**
 * BottomSheetShell — layout commun du moteur F39.
 * - role="dialog" aria-modal="true" + focus trap (FR-016)
 * - bouton sticky « Répondre librement » (FR-004, P10)
 * - ESC → émet `dismiss-for-freetext` (FR-005)
 * - reduced-motion neutralisé via useBottomSheetAnimation
 * - inFlight bloque le bouton Valider (FR-018)
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { useBottomSheetAnimation } from '~/composables/useBottomSheetAnimation'
import { useFocusTrap } from '~/composables/useFocusTrap'

interface Props {
  title: string
  description?: string
  submitLabel?: string
  /** désactive le bouton Valider (validation locale échouée) */
  submitDisabled?: boolean
  /** soumission en cours */
  inFlight?: boolean
  /** message d'erreur inline (POST 4xx/5xx) */
  errorMessage?: string | null
  /** masque le footer (utilisé par show_summary_card qui gère ses propres actions) */
  hideFooter?: boolean
  /** masque le bouton « Répondre librement » (très rare — laisser true par défaut) */
  hideFreeText?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  description: undefined,
  submitLabel: 'Valider',
  submitDisabled: false,
  inFlight: false,
  errorMessage: null,
  hideFooter: false,
  hideFreeText: false,
})

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'dismiss-for-freetext'): void
  (e: 'opened'): void
  (e: 'closed'): void
}>()

const titleId = useId()
const descriptionId = useId()
const sheetRef = ref<HTMLElement | null>(null)
const { slideUp, slideDown } = useBottomSheetAnimation()
const trap = useFocusTrap(sheetRef, { returnFocus: true })

const ariaDescribedBy = computed(() => (props.description ? descriptionId : undefined))

function onKeydown(e: KeyboardEvent): void {
  if (e.key !== 'Escape') return
  if (props.inFlight) {
    // ignoré pendant un POST — voir data-model state machine.
    e.preventDefault()
    return
  }
  e.preventDefault()
  requestFreeText()
}

function requestFreeText(): void {
  emit('dismiss-for-freetext')
}

function onSubmitClick(): void {
  if (props.submitDisabled || props.inFlight) return
  emit('submit')
}

async function close(): Promise<void> {
  await slideDown(sheetRef.value)
  trap.deactivate()
  emit('closed')
}

defineExpose({ close })

onMounted(async () => {
  await nextTick()
  document.addEventListener('keydown', onKeydown)
  trap.activate()
  await slideUp(sheetRef.value)
  emit('opened')
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  trap.deactivate()
})
</script>

<template>
  <div class="bottom-sheet__backdrop" aria-hidden="true" />
  <section
    ref="sheetRef"
    class="bottom-sheet"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="ariaDescribedBy"
    data-testid="chat-bottom-sheet"
  >
    <header class="bottom-sheet__header">
      <h2 :id="titleId" class="bottom-sheet__title">{{ title }}</h2>
      <p v-if="description" :id="descriptionId" class="bottom-sheet__description">{{ description }}</p>
    </header>

    <div class="bottom-sheet__body">
      <slot />
    </div>

    <p v-if="errorMessage" class="bottom-sheet__error" role="alert">{{ errorMessage }}</p>

    <footer v-if="!hideFooter" class="bottom-sheet__footer">
      <button
        v-if="!hideFreeText"
        type="button"
        class="bottom-sheet__freetext"
        data-testid="chat-bottom-sheet-freetext"
        @click="requestFreeText"
      >
        Répondre librement
      </button>
      <button
        type="button"
        class="bottom-sheet__submit"
        data-testid="chat-bottom-sheet-submit"
        :disabled="submitDisabled || inFlight"
        :aria-busy="inFlight || undefined"
        @click="onSubmitClick"
      >
        {{ inFlight ? 'Envoi…' : submitLabel }}
      </button>
    </footer>
    <footer v-else-if="!hideFreeText" class="bottom-sheet__footer bottom-sheet__footer--freetext-only">
      <button
        type="button"
        class="bottom-sheet__freetext"
        data-testid="chat-bottom-sheet-freetext"
        @click="requestFreeText"
      >
        Répondre librement
      </button>
    </footer>
  </section>
</template>

<style scoped>
.bottom-sheet__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.32);
  z-index: 60;
}
.bottom-sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 61;
  display: flex;
  flex-direction: column;
  background: var(--color-surface, #fff);
  border-top-left-radius: var(--radius-lg, 16px);
  border-top-right-radius: var(--radius-lg, 16px);
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.12);
  max-height: 70vh;
  padding: var(--space-4, 16px);
  gap: var(--space-3, 12px);
}
@media (min-width: 768px) {
  .bottom-sheet {
    left: 50%;
    transform: translateX(-50%);
    max-width: 720px;
    max-height: 60vh;
    border-radius: var(--radius-lg, 16px);
    bottom: var(--space-4, 16px);
  }
}
.bottom-sheet__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.bottom-sheet__title {
  font-size: var(--font-size-lg, 1.125rem);
  font-weight: var(--font-weight-semibold, 600);
  margin: 0;
}
.bottom-sheet__description {
  font-size: var(--font-size-sm, 0.875rem);
  color: var(--color-text-muted, #64748b);
  margin: 0;
}
.bottom-sheet__body {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
}
.bottom-sheet__error {
  background: var(--color-danger-50, #fef2f2);
  color: var(--color-danger-700, #b91c1c);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  font-size: var(--font-size-sm, 0.875rem);
  margin: 0;
}
.bottom-sheet__footer {
  display: flex;
  gap: var(--space-2, 8px);
  align-items: center;
  justify-content: space-between;
  position: sticky;
  bottom: 0;
  background: var(--color-surface, #fff);
  padding-top: var(--space-2, 8px);
}
.bottom-sheet__footer--freetext-only {
  justify-content: flex-end;
}
.bottom-sheet__freetext {
  background: transparent;
  border: 1px solid var(--color-border, #e2e8f0);
  color: var(--color-text, #0f172a);
  padding: var(--space-2, 8px) var(--space-4, 16px);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  min-height: 44px;
}
.bottom-sheet__submit {
  background: var(--color-brand-500, #16a34a);
  color: #fff;
  border: 0;
  padding: var(--space-2, 8px) var(--space-5, 20px);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  min-height: 44px;
  font-weight: var(--font-weight-medium, 500);
}
.bottom-sheet__submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
