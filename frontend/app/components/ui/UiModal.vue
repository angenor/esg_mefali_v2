<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { useFocusTrap } from '~/composables/useFocusTrap'
import { useFieldId } from '~/composables/useFieldId'
import { useReducedMotion } from '~/composables/useReducedMotion'

interface Props {
  modelValue?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closeOnOverlay?: boolean
  closeOnEsc?: boolean
  persistent?: boolean
  initialFocus?: string
  returnFocus?: boolean
  ariaLabel?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  size: 'md',
  closeOnOverlay: true,
  closeOnEsc: true,
  persistent: false,
  initialFocus: undefined,
  returnFocus: true,
  ariaLabel: undefined,
  id: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'open'): void
  (e: 'close'): void
}>()

const modalId = props.id ?? useFieldId('ui-modal')
const headerId = `${modalId}-header`
const bodyId = `${modalId}-body`

const dialogRef = ref<HTMLElement | null>(null)
const reduced = useReducedMotion()

// Pile globale : seule la modale au sommet possède Esc + focus trap actif.
type ModalGlobals = { __uiModalStack?: number[]; __uiModalSeq?: number }
const g = globalThis as ModalGlobals
const stack: number[] = (g.__uiModalStack ??= [])
function nextStackId(): number {
  g.__uiModalSeq = (g.__uiModalSeq ?? 0) + 1
  return g.__uiModalSeq
}
let myStackId = -1

const trap = useFocusTrap(dialogRef, {
  initialFocus: props.initialFocus,
  returnFocus: props.returnFocus,
})

const allowEsc = computed(() => props.closeOnEsc && !props.persistent)
const allowOverlay = computed(() => props.closeOnOverlay && !props.persistent)

function isTopOfStack(): boolean {
  return stack.length > 0 && stack[stack.length - 1] === myStackId
}

function close(): void {
  emit('update:modelValue', false)
  emit('close')
}

function onOverlayClick(): void {
  if (allowOverlay.value && isTopOfStack()) close()
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && allowEsc.value && isTopOfStack()) {
    e.preventDefault()
    close()
  }
}

async function animateOpen(): Promise<void> {
  if (reduced.value) return
  if (typeof window === 'undefined') return
  try {
    const { gsap } = await import('gsap')
    const dialog = dialogRef.value
    if (!dialog) return
    gsap.fromTo(
      dialog,
      { autoAlpha: 0, scale: 0.96 },
      { autoAlpha: 1, scale: 1, duration: 0.18, ease: 'power2.out' },
    )
  } catch {
    // gsap optionnel — silently no-op si import échoue
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (typeof document === 'undefined') return
    if (open) {
      myStackId = nextStackId()
      stack.push(myStackId)
      document.addEventListener('keydown', onKeydown, true)
      emit('open')
      void nextTick().then(() => {
        trap.activate()
        void animateOpen()
      })
    } else {
      const idx = stack.indexOf(myStackId)
      if (idx >= 0) stack.splice(idx, 1)
      myStackId = -1
      trap.deactivate()
      document.removeEventListener('keydown', onKeydown, true)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  const idx = stack.indexOf(myStackId)
  if (idx >= 0) stack.splice(idx, 1)
  trap.deactivate()
  if (typeof document !== 'undefined') {
    document.removeEventListener('keydown', onKeydown, true)
  }
})
</script>

<template>
  <Teleport v-if="modelValue" to="body">
    <div class="ui-modal" :data-size="size" :data-reduced="reduced || undefined">
      <div class="ui-modal__overlay" @click="onOverlayClick" />
      <div
        ref="dialogRef"
        :id="modalId"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="$slots.header ? headerId : undefined"
        :aria-label="!$slots.header ? ariaLabel : undefined"
        :aria-describedby="bodyId"
        tabindex="-1"
        class="ui-modal__dialog"
      >
        <header v-if="$slots.header" :id="headerId" class="ui-modal__header">
          <slot name="header" />
        </header>
        <div :id="bodyId" class="ui-modal__body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="ui-modal__footer">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ui-modal {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans);
}
.ui-modal__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
}
.ui-modal__dialog {
  position: relative;
  background: var(--color-surface);
  color: var(--color-text);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  width: min(100% - 2rem, 32rem);
  outline: none;
}
.ui-modal[data-size='sm'] .ui-modal__dialog { width: min(100% - 2rem, 24rem); }
.ui-modal[data-size='lg'] .ui-modal__dialog { width: min(100% - 2rem, 48rem); }
.ui-modal[data-size='xl'] .ui-modal__dialog { width: min(100% - 2rem, 64rem); }
.ui-modal__header,
.ui-modal__footer {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}
.ui-modal__footer {
  border-top: 1px solid var(--color-border);
  border-bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
.ui-modal__body {
  padding: var(--space-6);
  overflow-y: auto;
  flex: 1;
}
</style>
