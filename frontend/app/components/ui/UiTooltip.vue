<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Placement } from '@floating-ui/vue'
import { useFloating } from '~/composables/useFloating'
import { useFieldId } from '~/composables/useFieldId'

interface Props {
  placement?: Placement
  delay?: number
  disabled?: boolean
  offsetPx?: number
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  placement: 'top',
  delay: 100,
  disabled: false,
  offsetPx: 6,
  id: undefined,
})

const emit = defineEmits<{
  (e: 'open'): void
  (e: 'close'): void
}>()

const open = ref(false)
const tooltipId = props.id ?? useFieldId('ui-tooltip')

const { referenceRef, floatingRef, floatingStyles, placement: actualPlacement } = useFloating({
  placement: props.placement,
  offsetPx: props.offsetPx,
  open,
})

let timer: ReturnType<typeof setTimeout> | null = null

function show(): void {
  if (props.disabled) return
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    open.value = true
  }, props.delay)
}

function hide(): void {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    open.value = false
  }, 50)
}

watch(open, (v) => {
  if (v) emit('open')
  else emit('close')
})
</script>

<template>
  <span
    ref="referenceRef"
    class="ui-tooltip__trigger"
    :aria-describedby="open ? tooltipId : undefined"
    @mouseenter="show"
    @mouseleave="hide"
    @focusin="show"
    @focusout="hide"
  >
    <slot />
    <Teleport v-if="open" to="body">
      <span
        ref="floatingRef"
        :id="tooltipId"
        role="tooltip"
        class="ui-tooltip"
        :data-placement="actualPlacement"
        :style="floatingStyles"
      >
        <slot name="content" />
      </span>
    </Teleport>
  </span>
</template>

<style scoped>
.ui-tooltip__trigger {
  display: inline-flex;
}
.ui-tooltip {
  background: var(--color-text);
  color: var(--color-surface);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-family: var(--font-sans);
  pointer-events: none;
  z-index: 1100;
  max-width: 16rem;
}
</style>
