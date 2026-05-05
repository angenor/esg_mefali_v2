<!--
  F48 US6 — RecalcStrip
  Bandeau "Dernier calcul + Recalculer maintenant" (formaté FR).
  Spinner pendant loading, désactivé pendant l'exécution.
  Respecte prefers-reduced-motion (spinner statique).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useT } from '~/composables/useT'
import { useReducedMotion } from '~/composables/useReducedMotion'

interface Props {
  computedAt: Date | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

defineEmits<{
  (e: 'recompute'): void
}>()

const { t } = useT()
const reducedMotion = useReducedMotion()

const formatted = computed<string | null>(() => {
  if (!props.computedAt) return null
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(props.computedAt)
  }
  catch {
    return null
  }
})
</script>

<template>
  <div
    class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-2.5 ring-1 ring-slate-200"
  >
    <p class="text-sm text-slate-600">
      <template v-if="formatted">
        {{ t('credit_score.recalc.last', { when: formatted }) }}
      </template>
      <template v-else>
        {{ t('credit_score.recalc.never') }}
      </template>
    </p>

    <div class="flex items-center gap-2">
      <span
        v-if="loading"
        class="text-xs text-slate-500"
        aria-live="polite"
      >
        {{ t('credit_score.recalc.running') }}
      </span>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        :aria-disabled="loading"
        @click="$emit('recompute')"
      >
        <svg
          v-if="loading"
          class="h-4 w-4"
          :class="reducedMotion ? '' : 'animate-spin'"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke-width="3"
            stroke-opacity="0.25"
          />
          <path
            stroke-linecap="round"
            stroke-width="3"
            d="M22 12a10 10 0 0 0-10-10"
          />
        </svg>
        {{ t('credit_score.recalc.button') }}
      </button>
    </div>
  </div>
</template>
