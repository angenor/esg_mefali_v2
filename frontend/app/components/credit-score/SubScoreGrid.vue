<!--
  F48 US2 — SubScoreGrid
  Grille 2×2 desktop / pile mobile des 4 sous-scores.
  Ordre stable : Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance.
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useT } from '~/composables/useT'
import SubScoreCard from './SubScoreCard.vue'
import type { SubscoreBucket, SubscoresView } from '~/types/creditScore'

interface Props {
  subscores: SubscoresView
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'complete-clicked', bucket: SubscoreBucket): void
}>()

const { t } = useT()

const ORDER: SubscoreBucket[] = [
  'solidite_financiere',
  'performance_operationnelle',
  'engagement_esg',
  'gouvernance',
]

const items = computed(() =>
  ORDER.map((bucket) => ({
    bucket,
    label: t(`credit_score.subscores.${bucket}` as const),
    value: props.subscores[bucket],
  })),
)
</script>

<template>
  <section
    class="space-y-3"
    aria-labelledby="subscore-grid-title"
  >
    <h2
      id="subscore-grid-title"
      class="text-base font-semibold text-slate-900"
    >
      {{ t('credit_score.subscores.section_title') }}
    </h2>
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <SubScoreCard
        v-for="item in items"
        :key="item.bucket"
        :bucket="item.bucket"
        :value="item.value"
        :label="item.label"
        @complete-clicked="$emit('complete-clicked', item.bucket)"
      />
    </div>
  </section>
</template>
