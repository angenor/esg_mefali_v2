<!--
  F48 US3 — EligibilityBadge
  Badge dispositif : libellé + statut (icône + couleur + texte) + raison principale.
  Pastille source via VizSourcePin. Émet `details-clicked`.
  Texte toujours présent (FR-015 / R-10 daltonien-friendly).
  Raison principale uniquement (clarif Q5).
-->
<script setup lang="ts">
import { computed } from 'vue'
import VizSourcePin from '~/components/viz/VizSourcePin.vue'
import { useT } from '~/composables/useT'
import type { EligibilityBadgeView } from '~/types/creditScore'

interface Props {
  badge: EligibilityBadgeView
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'details-clicked'): void
}>()

const { t } = useT()

const statusMeta = computed(() => {
  switch (props.badge.status) {
    case 'eligible':
      return {
        label: t('credit_score.eligibility.status.eligible'),
        ring: 'ring-emerald-300',
        bg: 'bg-emerald-50',
        text: 'text-emerald-800',
        dot: 'bg-emerald-500',
        icon: 'M5 13l4 4L19 7',
      }
    case 'not_eligible':
      return {
        label: t('credit_score.eligibility.status.not_eligible'),
        ring: 'ring-red-300',
        bg: 'bg-red-50',
        text: 'text-red-800',
        dot: 'bg-red-500',
        icon: 'M6 18L18 6M6 6l12 12',
      }
    case 'incomplete':
    default:
      return {
        label: t('credit_score.eligibility.status.incomplete'),
        ring: 'ring-amber-300',
        bg: 'bg-amber-50',
        text: 'text-amber-800',
        dot: 'bg-amber-500',
        icon: 'M12 9v4m0 4h.01',
      }
  }
})
</script>

<template>
  <button
    type="button"
    class="flex w-full flex-col gap-2 rounded-xl p-4 text-left ring-1 transition hover:ring-2"
    :class="[statusMeta.bg, statusMeta.ring]"
    :data-code="badge.code"
    :aria-label="`${badge.label} — ${statusMeta.label}`"
    @click="$emit('details-clicked')"
  >
    <header class="flex items-start justify-between gap-2">
      <div class="flex min-w-0 flex-1 items-start gap-2">
        <span
          class="mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full"
          :class="statusMeta.dot"
          aria-hidden="true"
        />
        <div class="min-w-0 flex-1">
          <h3 class="truncate text-sm font-semibold text-slate-900">
            {{ badge.label }}
          </h3>
          <p
            class="mt-0.5 inline-flex items-center gap-1 text-xs font-medium"
            :class="statusMeta.text"
          >
            <svg
              class="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                :d="statusMeta.icon"
              />
            </svg>
            {{ statusMeta.label }}
          </p>
        </div>
      </div>
      <VizSourcePin
        v-if="badge.sourceId"
        :source_id="badge.sourceId"
      />
    </header>

    <p
      v-if="badge.primaryReason"
      class="line-clamp-2 text-xs text-slate-700"
    >
      {{ badge.primaryReason }}
    </p>

    <footer class="mt-1 text-xs font-medium text-slate-600 hover:text-slate-900">
      {{ t('credit_score.eligibility.details_cta') }} →
    </footer>
  </button>
</template>
