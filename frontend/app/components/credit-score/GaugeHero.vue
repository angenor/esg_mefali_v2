<!--
  F48 US1 — GaugeHero
  Gauge SVG 0-100 + classification + delta vs N-1.
  Animation gsap au changement de score (respecte prefers-reduced-motion).
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { animateGaugeTransition } from '~/lib/animateGaugeTransition'
import { useReducedMotion } from '~/composables/useReducedMotion'
import ClassificationLabel from './ClassificationLabel.vue'
import type { ClassificationView } from '~/types/creditScore'

interface Props {
  score: number
  scorePrev: number | null
  classification: ClassificationView
  computedAt: Date | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

defineEmits<{
  (e: 'recalc-clicked'): void
}>()

const reducedMotion = useReducedMotion()

// Valeur animée (proxy gsap).
const proxy = reactive({ value: props.score ?? 0 })
const tweenRef = ref<gsap.core.Tween | null>(null)

watch(
  () => props.score,
  (next, prev) => {
    if (typeof next !== 'number') return
    const from = typeof prev === 'number' ? prev : proxy.value
    tweenRef.value?.kill()
    tweenRef.value = animateGaugeTransition(proxy, from, next, {
      reducedMotion: reducedMotion.value,
    })
  },
  { immediate: false },
)

onBeforeUnmount(() => {
  tweenRef.value?.kill()
})

// SVG gauge (demi-cercle de rayon 90, angle 0..180°).
const RADIUS = 90
const CIRCUMFERENCE_HALF = Math.PI * RADIUS // longueur du demi-cercle
const offset = computed<number>(() => {
  const v = Math.max(0, Math.min(100, proxy.value))
  return CIRCUMFERENCE_HALF * (1 - v / 100)
})

const strokeColor = computed<string>(() => {
  switch (props.classification.colorToken) {
    case 'danger':
      return '#dc2626'
    case 'warning':
      return '#f59e0b'
    case 'success':
      return '#10b981'
    case 'success-strong':
      return '#15803d'
    default:
      return '#64748b'
  }
})

const displayedValue = computed<number>(() => Math.round(proxy.value))

const deltaInfo = computed<{ value: number | null; sign: '+' | '−' | '' }>(() => {
  if (props.scorePrev === null || props.scorePrev === undefined) {
    return { value: null, sign: '' }
  }
  const delta = props.score - props.scorePrev
  if (delta === 0) return { value: 0, sign: '' }
  return {
    value: Math.abs(delta),
    sign: delta > 0 ? '+' : '−',
  }
})

const computedAtLabel = computed<string>(() => {
  if (!props.computedAt) return ''
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(props.computedAt)
})
</script>

<template>
  <section
    class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
    aria-labelledby="gauge-hero-title"
  >
    <header class="mb-4 flex items-center justify-between">
      <h2 id="gauge-hero-title" class="text-lg font-semibold text-slate-900">
        Score crédit ESG
      </h2>
      <button
        type="button"
        class="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
        :disabled="loading"
        @click="$emit('recalc-clicked')"
      >
        Recalculer maintenant
      </button>
    </header>

    <div class="flex flex-col items-center gap-4 md:flex-row md:items-end md:justify-around">
      <div
        class="relative"
        role="img"
        :aria-label="`Score crédit ${displayedValue} sur 100`"
      >
        <svg
          width="220"
          height="130"
          viewBox="0 0 220 130"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Arc de fond -->
          <path
            d="M 20 110 A 90 90 0 0 1 200 110"
            fill="none"
            stroke="#e2e8f0"
            stroke-width="14"
            stroke-linecap="round"
          />
          <!-- Arc de score -->
          <path
            d="M 20 110 A 90 90 0 0 1 200 110"
            fill="none"
            :stroke="strokeColor"
            stroke-width="14"
            stroke-linecap="round"
            :stroke-dasharray="CIRCUMFERENCE_HALF"
            :stroke-dashoffset="offset"
            style="transition: stroke 240ms ease;"
          />
          <text
            x="110"
            y="100"
            text-anchor="middle"
            class="fill-slate-900"
            style="font-size: 36px; font-weight: 700;"
          >
            {{ displayedValue }}
          </text>
          <text
            x="110"
            y="120"
            text-anchor="middle"
            class="fill-slate-500"
            style="font-size: 12px;"
          >
            / 100
          </text>
        </svg>
      </div>

      <div class="flex flex-col items-center gap-2 md:items-start">
        <ClassificationLabel :classification="classification" size="lg" />

        <p
          v-if="deltaInfo.value === null"
          class="text-sm text-slate-500"
        >
          Premier calcul
        </p>
        <p
          v-else-if="deltaInfo.value === 0"
          class="text-sm text-slate-600"
        >
          Stable vs précédent
        </p>
        <p
          v-else
          class="text-sm font-medium"
          :class="deltaInfo.sign === '+' ? 'text-emerald-700' : 'text-red-700'"
        >
          {{ deltaInfo.sign }}{{ deltaInfo.value }} points vs précédent
        </p>

        <p v-if="computedAtLabel" class="text-xs text-slate-400">
          Dernier calcul : {{ computedAtLabel }}
        </p>
      </div>
    </div>
  </section>
</template>
