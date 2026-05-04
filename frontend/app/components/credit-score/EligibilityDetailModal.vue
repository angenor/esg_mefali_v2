<!--
  F48 US3 — EligibilityDetailModal
  Modal détail : description + tableau exhaustif des critères + bouton matching.
  Routage interne `/matching?{matching_offer_query}` (pas de nouvel onglet).
-->
<script setup lang="ts">
import { computed } from 'vue'
import UiModal from '~/components/ui/UiModal.vue'
import VizSourcePin from '~/components/viz/VizSourcePin.vue'
import { useT } from '~/composables/useT'
import type { EligibilityBadgeView } from '~/types/creditScore'

interface Props {
  badge: EligibilityBadgeView | null
  open: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
}>()

const { t } = useT()

const matchingHref = computed<string>(() => {
  if (!props.badge) return '/matching'
  const q = props.badge.matchingOfferQuery || ''
  return q ? `/matching?${q}` : '/matching'
})

function close() {
  emit('update:open', false)
}
</script>

<template>
  <UiModal
    :model-value="open"
    size="lg"
    :aria-label="badge?.label ?? t('credit_score.eligibility.modal.title')"
    @close="close"
    @update:model-value="emit('update:open', $event)"
  >
    <template v-if="badge">
      <div class="space-y-4 p-1">
        <header class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">
              {{ badge.label }}
            </h2>
            <p class="mt-1 text-sm text-slate-600">
              {{ badge.description }}
            </p>
          </div>
          <VizSourcePin
            v-if="badge.sourceId"
            :source_id="badge.sourceId"
          />
        </header>

        <section>
          <h3 class="mb-2 text-sm font-semibold text-slate-800">
            {{ t('credit_score.eligibility.modal.criteria_title') }}
          </h3>
          <div class="overflow-x-auto rounded-lg ring-1 ring-slate-200">
            <table class="min-w-full divide-y divide-slate-200 text-sm">
              <thead class="bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-600">
                <tr>
                  <th class="px-3 py-2 text-left">
                    {{ t('credit_score.eligibility.modal.col_label') }}
                  </th>
                  <th class="px-3 py-2 text-left">
                    {{ t('credit_score.eligibility.modal.col_threshold') }}
                  </th>
                  <th class="px-3 py-2 text-left">
                    {{ t('credit_score.eligibility.modal.col_actual') }}
                  </th>
                  <th class="px-3 py-2 text-left">
                    {{ t('credit_score.eligibility.modal.col_met') }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 bg-white">
                <tr
                  v-for="c in badge.criteria"
                  :key="c.code"
                  :class="c.blocking && !c.met ? 'bg-red-50/40' : ''"
                >
                  <td class="px-3 py-2 text-slate-800">
                    {{ c.label }}
                  </td>
                  <td class="px-3 py-2 text-slate-600">
                    {{ c.threshold ?? '—' }}
                  </td>
                  <td class="px-3 py-2 text-slate-700">
                    {{ c.actual ?? '—' }}
                  </td>
                  <td class="px-3 py-2">
                    <span
                      v-if="c.met"
                      class="inline-flex items-center gap-1 text-xs font-medium text-emerald-700"
                    >✓ {{ t('credit_score.eligibility.modal.met') }}</span>
                    <span
                      v-else
                      class="inline-flex items-center gap-1 text-xs font-medium text-red-700"
                    >✗ {{ t('credit_score.eligibility.modal.not_met') }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <footer class="flex flex-wrap items-center justify-end gap-2 pt-2">
          <button
            type="button"
            class="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            @click="close"
          >
            {{ t('credit_score.eligibility.modal.close') }}
          </button>
          <a
            v-if="badge.status === 'eligible'"
            :href="matchingHref"
            class="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            {{ t('credit_score.eligibility.modal.matching_cta') }}
          </a>
        </footer>
      </div>
    </template>
  </UiModal>
</template>
