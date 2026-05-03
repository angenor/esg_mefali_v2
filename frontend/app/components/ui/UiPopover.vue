<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import type { Placement } from '@floating-ui/vue'
import { useFloating } from '~/composables/useFloating'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  modelValue?: boolean
  placement?: Placement
  triggerOn?: 'click' | 'hover' | 'manual'
  offsetPx?: number
  id?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  placement: 'bottom-start',
  triggerOn: 'click',
  offsetPx: 6,
  id: undefined,
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'open'): void
  (e: 'close'): void
}>()

const popId = props.id ?? useFieldId('ui-popover')
const localOpen = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => {
    localOpen.value = v
  },
)

const { referenceRef, floatingRef, floatingStyles, placement: actualPlacement } = useFloating({
  placement: props.placement,
  offsetPx: props.offsetPx,
  open: localOpen,
})

function setOpen(v: boolean): void {
  if (props.disabled) return
  localOpen.value = v
  emit('update:modelValue', v)
  emit(v ? 'open' : 'close')
}

function toggle(): void {
  setOpen(!localOpen.value)
}

function onTriggerClick(): void {
  if (props.triggerOn === 'click') toggle()
}

function onMouseEnter(): void {
  if (props.triggerOn === 'hover') setOpen(true)
}

function onMouseLeave(): void {
  if (props.triggerOn === 'hover') setOpen(false)
}

function onDocClick(e: MouseEvent): void {
  if (!localOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  if (
    referenceRef.value?.contains(target) ||
    floatingRef.value?.contains(target)
  ) {
    return
  }
  setOpen(false)
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && localOpen.value) {
    e.preventDefault()
    setOpen(false)
  }
}

watch(
  localOpen,
  (open) => {
    if (typeof document === 'undefined') return
    if (open) {
      document.addEventListener('click', onDocClick, true)
      document.addEventListener('keydown', onKeydown, true)
    } else {
      document.removeEventListener('click', onDocClick, true)
      document.removeEventListener('keydown', onKeydown, true)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (typeof document === 'undefined') return
  document.removeEventListener('click', onDocClick, true)
  document.removeEventListener('keydown', onKeydown, true)
})

defineExpose({
  open: () => setOpen(true),
  close: () => setOpen(false),
  toggle,
})
</script>

<template>
  <span class="ui-popover__wrapper">
    <span
      ref="referenceRef"
      class="ui-popover__trigger"
      :aria-expanded="localOpen"
      :aria-controls="popId"
      @click="onTriggerClick"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <slot name="trigger" />
    </span>
    <Teleport v-if="localOpen" to="body">
      <div
        ref="floatingRef"
        :id="popId"
        role="dialog"
        class="ui-popover"
        :data-placement="actualPlacement"
        :style="floatingStyles"
      >
        <slot name="content" />
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.ui-popover__wrapper {
  display: inline-flex;
}
.ui-popover {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-3);
  min-width: 12rem;
  z-index: 1050;
  font-family: var(--font-sans);
}
</style>
