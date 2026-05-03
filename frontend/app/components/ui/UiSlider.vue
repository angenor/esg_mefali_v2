<script setup lang="ts">
import { computed } from 'vue'
import type { UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'

type SliderValue = number | [number, number]

interface Props {
  modelValue?: SliderValue
  min?: number
  max?: number
  step?: number
  range?: boolean
  size?: UiSize
  disabled?: boolean
  ariaLabel?: string
  ariaLabelMin?: string
  ariaLabelMax?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 0,
  min: 0,
  max: 100,
  step: 1,
  range: false,
  size: 'md',
  disabled: false,
  ariaLabel: undefined,
  ariaLabelMin: 'Borne minimale',
  ariaLabelMax: 'Borne maximale',
  id: undefined,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: SliderValue): void
  (e: 'change', v: SliderValue): void
}>()

const sliderId = props.id ?? useFieldId('ui-slider')

const lowValue = computed(() =>
  props.range ? (props.modelValue as [number, number])[0] : (props.modelValue as number),
)
const highValue = computed(() =>
  props.range ? (props.modelValue as [number, number])[1] : (props.modelValue as number),
)

function clamp(v: number): number {
  return Math.max(props.min, Math.min(props.max, v))
}

function snapToStep(v: number): number {
  const step = props.step || 1
  return Math.round((v - props.min) / step) * step + props.min
}

function emitChange(low: number, high: number): void {
  if (props.range) {
    const next: [number, number] = [low, high]
    emit('update:modelValue', next)
    emit('change', next)
  } else {
    // En mode single, seul le thumb "high" existe et représente la valeur.
    emit('update:modelValue', high)
    emit('change', high)
  }
}

function moveLow(delta: number): void {
  if (props.disabled) return
  const next = clamp(snapToStep(lowValue.value + delta))
  if (props.range && next > highValue.value) return
  emitChange(next, highValue.value)
}

function moveHigh(delta: number): void {
  if (props.disabled) return
  const next = clamp(snapToStep(highValue.value + delta))
  if (props.range && next < lowValue.value) return
  emitChange(lowValue.value, next)
}

function setLow(v: number): void {
  if (props.disabled) return
  const next = clamp(snapToStep(v))
  if (props.range && next > highValue.value) return
  emitChange(next, highValue.value)
}

function setHigh(v: number): void {
  if (props.disabled) return
  const next = clamp(snapToStep(v))
  if (props.range && next < lowValue.value) return
  emitChange(lowValue.value, next)
}

function pageStep(): number {
  return Math.max(props.step || 1, (props.max - props.min) / 10)
}

function onKeydownLow(e: KeyboardEvent): void {
  switch (e.key) {
    case 'ArrowRight':
    case 'ArrowUp':
      e.preventDefault()
      moveLow(props.step)
      break
    case 'ArrowLeft':
    case 'ArrowDown':
      e.preventDefault()
      moveLow(-props.step)
      break
    case 'PageUp':
      e.preventDefault()
      moveLow(pageStep())
      break
    case 'PageDown':
      e.preventDefault()
      moveLow(-pageStep())
      break
    case 'Home':
      e.preventDefault()
      setLow(props.min)
      break
    case 'End':
      e.preventDefault()
      setLow(props.range ? highValue.value : props.max)
      break
  }
}

function onKeydownHigh(e: KeyboardEvent): void {
  switch (e.key) {
    case 'ArrowRight':
    case 'ArrowUp':
      e.preventDefault()
      moveHigh(props.step)
      break
    case 'ArrowLeft':
    case 'ArrowDown':
      e.preventDefault()
      moveHigh(-props.step)
      break
    case 'PageUp':
      e.preventDefault()
      moveHigh(pageStep())
      break
    case 'PageDown':
      e.preventDefault()
      moveHigh(-pageStep())
      break
    case 'Home':
      e.preventDefault()
      // En range, le thumb high s'arrête au low ; en single, on va au min.
      setHigh(props.range ? lowValue.value : props.min)
      break
    case 'End':
      e.preventDefault()
      setHigh(props.max)
      break
  }
}

function pct(v: number): string {
  const pct = ((v - props.min) / (props.max - props.min)) * 100
  return `${pct}%`
}
</script>

<template>
  <div
    :id="sliderId"
    class="ui-slider"
    :data-size="size"
    :data-disabled="disabled || undefined"
    :data-range="range || undefined"
  >
    <div class="ui-slider__track" aria-hidden="true">
      <div
        class="ui-slider__fill"
        :style="{
          left: range ? pct(lowValue) : '0%',
          right: `calc(100% - ${pct(highValue)})`,
        }"
      />
    </div>
    <span
      v-if="range"
      role="slider"
      tabindex="0"
      :aria-label="ariaLabelMin"
      :aria-valuemin="min"
      :aria-valuemax="max"
      :aria-valuenow="lowValue"
      :aria-disabled="disabled || undefined"
      class="ui-slider__thumb"
      :style="{ left: pct(lowValue) }"
      @keydown="onKeydownLow"
    />
    <span
      role="slider"
      tabindex="0"
      :aria-label="range ? ariaLabelMax : ariaLabel"
      :aria-valuemin="min"
      :aria-valuemax="max"
      :aria-valuenow="highValue"
      :aria-disabled="disabled || undefined"
      class="ui-slider__thumb"
      :style="{ left: pct(highValue) }"
      @keydown="onKeydownHigh"
    />
  </div>
</template>

<style scoped>
.ui-slider {
  position: relative;
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  font-family: var(--font-sans);
}
.ui-slider__track {
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-border);
  border-radius: 999px;
  top: 50%;
  transform: translateY(-50%);
}
.ui-slider__fill {
  position: absolute;
  top: 0;
  bottom: 0;
  background: var(--color-brand-500);
  border-radius: 999px;
}
.ui-slider__thumb {
  position: absolute;
  width: 20px;
  height: 20px;
  background: #fff;
  border: 2px solid var(--color-brand-500);
  border-radius: 50%;
  transform: translate(-50%, 0);
  cursor: pointer;
  top: 50%;
  margin-top: -10px;
}
.ui-slider__thumb:focus-visible {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}
.ui-slider[data-disabled] {
  opacity: 0.6;
  pointer-events: none;
}
</style>
