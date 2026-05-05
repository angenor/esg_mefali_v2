<!--
  F48 Polish (FR-012a + clarif Q4) — PartialCoverageBanner
  Bandeau d'avertissement quand au moins un sous-score est `null`.
  CTA « Compléter mes données » → ouvre le drawer d'édition (parent gère).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useT } from '~/composables/useT'
import type { SubscoreBucket, SubscoresView } from '~/types/creditScore'

interface Props {
  subscores: SubscoresView
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'complete-clicked'): void
}>()

const { t } = useT()

const ORDER: SubscoreBucket[] = [
  'solidite_financiere',
  'performance_operationnelle',
  'engagement_esg',
  'gouvernance',
]

const missingLabels = computed<string[]>(() =>
  ORDER.filter((k) => props.subscores[k] === null).map((k) =>
    t(`credit_score.subscores.${k}` as const),
  ),
)
</script>

<template>
  <aside
    v-if="missingLabels.length > 0"
    class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-amber-50 px-4 py-3 ring-1 ring-amber-200"
    role="status"
  >
    <div class="flex items-start gap-2 text-sm text-amber-900">
      <svg
        class="mt-0.5 h-4 w-4 shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 9v4m0 4h.01M5 19h14a2 2 0 002-2L13 5a2 2 0 00-2 0L3 17a2 2 0 002 2z"
        />
      </svg>
      <p>
        {{ t('credit_score.partial_coverage.text') }}
        <span class="font-medium">{{ missingLabels.join(', ') }}</span>.
      </p>
    </div>
    <button
      type="button"
      class="shrink-0 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
      @click="$emit('complete-clicked')"
    >
      {{ t('credit_score.complete_data_cta') }}
    </button>
  </aside>
</template>
