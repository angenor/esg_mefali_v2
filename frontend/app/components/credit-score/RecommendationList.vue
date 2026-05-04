<!--
  F48 US4 — RecommendationList
  Liste 3-5 recommandations triées desc par impact (filet de tri front via store).
  Cas vide : message FR doux pour empty state.
-->
<script setup lang="ts">
import { useT } from '~/composables/useT'
import RecommendationCard from './RecommendationCard.vue'
import type { RecommendationView } from '~/types/creditScore'

interface Props {
  items: RecommendationView[]
  loading?: boolean
}

withDefaults(defineProps<Props>(), { loading: false })

const { t } = useT()
</script>

<template>
  <section
    class="space-y-3"
    aria-labelledby="reco-list-title"
  >
    <header class="flex items-baseline justify-between gap-2">
      <h2
        id="reco-list-title"
        class="text-base font-semibold text-slate-900"
      >
        {{ t('credit_score.recommendations.section_title') }}
      </h2>
      <p class="text-xs text-slate-500">
        {{ t('credit_score.recommendations.section_hint') }}
      </p>
    </header>

    <div
      v-if="loading && items.length === 0"
      class="rounded-2xl bg-white p-4 text-center text-sm text-slate-500 ring-1 ring-slate-200"
    >
      {{ t('credit_score.recommendations.loading') }}
    </div>

    <div
      v-else-if="items.length === 0"
      class="rounded-2xl bg-slate-50 p-4 text-center text-sm text-slate-600 ring-1 ring-slate-200"
    >
      {{ t('credit_score.recommendations.empty') }}
    </div>

    <div
      v-else
      class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
    >
      <RecommendationCard
        v-for="r in items"
        :key="r.stepId"
        :reco="r"
      />
    </div>
  </section>
</template>
