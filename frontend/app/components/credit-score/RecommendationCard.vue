<!--
  F48 US4 — RecommendationCard
  Carte recommandation : titre + description + impact estimé + mention « estimation ».
  Click → navigation interne `/plan-action#step-{stepId}`.
  Edge case (FR/dead link) géré par le parent (fallback `/plan-action`).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useT } from '~/composables/useT'
import type { RecommendationView, SubscoreBucket } from '~/types/creditScore'

interface Props {
  reco: RecommendationView
}

const props = defineProps<Props>()

const { t } = useT()

const subscoreLabel = computed<string>(() =>
  t(`credit_score.subscores.${props.reco.targetSubscore as SubscoreBucket}` as const),
)

const href = computed<string>(() =>
  props.reco.stepId ? `/plan-action#step-${encodeURIComponent(props.reco.stepId)}` : '/plan-action',
)
</script>

<template>
  <a
    :href="href"
    class="group flex flex-col gap-2 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 transition hover:ring-emerald-300"
    :data-step-id="reco.stepId"
  >
    <header class="flex items-start justify-between gap-2">
      <h3 class="text-sm font-semibold text-slate-900 group-hover:text-emerald-700">
        {{ reco.title }}
      </h3>
      <span
        class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200"
        :aria-label="t('credit_score.recommendations.impact_aria', { value: reco.estimatedPointsImpact })"
      >
        +{{ reco.estimatedPointsImpact }} pts
      </span>
    </header>

    <p
      v-if="reco.description"
      class="line-clamp-3 text-xs text-slate-600"
    >
      {{ reco.description }}
    </p>

    <footer class="mt-1 flex items-center justify-between text-xs">
      <span class="text-slate-500">
        {{ t('credit_score.recommendations.target_label') }} : <span class="font-medium text-slate-700">{{ subscoreLabel }}</span>
      </span>
      <span class="text-slate-400 italic">
        {{ t('credit_score.recommendations.estimation') }}
      </span>
    </footer>
  </a>
</template>
