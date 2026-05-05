<!--
  F48 US2 — SubScoreCard
  Carte sous-score : valeur 0-100 + barre + état "non calculé".
  Le libellé textuel est toujours présent (R-10, daltonien-friendly).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useT } from '~/composables/useT'
import type { SubscoreBucket } from '~/types/creditScore'

interface Props {
  bucket: SubscoreBucket
  value: number | null
  label: string
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'complete-clicked'): void
}>()

const { t } = useT()

const widthPct = computed<number>(() => {
  if (props.value === null) return 0
  return Math.max(0, Math.min(100, props.value))
})

const barClass = computed<string>(() => {
  if (props.value === null) return 'bg-slate-200'
  const v = props.value
  if (v >= 80) return 'bg-green-600'
  if (v >= 60) return 'bg-emerald-500'
  if (v >= 40) return 'bg-amber-500'
  return 'bg-red-500'
})

const ariaLabel = computed<string>(() =>
  props.value === null
    ? `${props.label} : ${t('credit_score.not_calculated')}`
    : `${props.label} : ${props.value} sur 100`,
)
</script>

<template>
  <article
    class="flex flex-col gap-2 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
    :data-bucket="bucket"
    :aria-label="ariaLabel"
  >
    <header class="flex items-baseline justify-between gap-2">
      <h3 class="text-sm font-medium text-slate-700">
        {{ label }}
      </h3>
      <span
        v-if="value !== null"
        class="text-2xl font-bold text-slate-900"
      >
        {{ value }}<span class="text-sm font-medium text-slate-500">/100</span>
      </span>
      <span
        v-else
        class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
      >
        {{ t('credit_score.not_calculated') }}
      </span>
    </header>

    <div
      class="relative h-2 w-full overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      :aria-valuenow="value ?? 0"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="h-full transition-all duration-300 ease-out"
        :class="barClass"
        :style="{ width: `${widthPct}%` }"
      />
    </div>

    <button
      v-if="value === null"
      type="button"
      class="self-start text-xs font-medium text-emerald-700 hover:text-emerald-800 hover:underline"
      @click="$emit('complete-clicked')"
    >
      {{ t('credit_score.complete_data_cta') }} →
    </button>
  </article>
</template>
