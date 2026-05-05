<!--
  F48 — /credit-score (US1 → US10 + Polish)
  Page d'entrée du score crédit ESG : gauge synthèse, sous-scores, badges
  d'éligibilité, recommandations, recalcul, édition financière, historique,
  wizard empty-state, export PDF (placeholder), banner couverture partielle.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useCreditScore } from '~/composables/useCreditScore'
import { useCreditEligibility } from '~/composables/useCreditEligibility'
import { useCreditHistory } from '~/composables/useCreditHistory'
import { useCreditScoreStore } from '~/stores/creditScore'
import { useChatEventBus } from '~/composables/useChatEventBus'
import { useToast } from '~/composables/useToast'
import { useT } from '~/composables/useT'
import GaugeHero from '~/components/credit-score/GaugeHero.vue'
import SubScoreGrid from '~/components/credit-score/SubScoreGrid.vue'
import EligibilityBadge from '~/components/credit-score/EligibilityBadge.vue'
import EligibilityDetailModal from '~/components/credit-score/EligibilityDetailModal.vue'
import RecommendationList from '~/components/credit-score/RecommendationList.vue'
import RecalcStrip from '~/components/credit-score/RecalcStrip.vue'
import CreditDataDrawer from '~/components/credit-score/CreditDataDrawer.vue'
import ScoreHistoryChart from '~/components/credit-score/ScoreHistoryChart.vue'
import EmptyStateWizard from '~/components/credit-score/EmptyStateWizard.vue'
import PartialCoverageBanner from '~/components/credit-score/PartialCoverageBanner.vue'
import ExportPdfButton from '~/components/credit-score/ExportPdfButton.vue'
import type { EligibilityBadgeView } from '~/types/creditScore'

// SSR désactivé via routeRules dans nuxt.config.ts (Nuxt 4 ignore
// `ssr: false` dans definePageMeta) — cf. commentaire dans nuxt.config.ts.

const { score, loading, error, refresh } = useCreditScore()
const eligibility = useCreditEligibility()
const history = useCreditHistory({ limit: 6 })
const store = useCreditScoreStore()
const bus = useChatEventBus()
const toast = useToast()
const { t } = useT()

const recalcLoading = computed<boolean>(() => loading.value)

// US3 — modal détail éligibilité
const detailOpen = ref<boolean>(false)
const detailBadge = ref<EligibilityBadgeView | null>(null)

function onBadgeClick(badge: EligibilityBadgeView) {
  detailBadge.value = badge
  detailOpen.value = true
}

// US5 — drawer édition financière
const editOpen = ref<boolean>(false)
function openEdit() {
  editOpen.value = true
}

// US4 — chargement recommandations + abonnement EventBus
function refreshRecos() {
  void store.refreshRecommendations({ force: true })
}

let off: (() => void) | null = null
onMounted(() => {
  void store.refreshRecommendations()
  off = bus.on('entity_updated', (e) => {
    if (e.entityType === 'credit_score' || e.entityType === 'plan_action_item') {
      refreshRecos()
    }
  })
})

onBeforeUnmount(() => {
  if (off) off()
})

// US6 — recalcul global
async function handleRecalcClick() {
  const previousScore = store.rawScore?.combine ?? null
  try {
    const fresh = await import('~/services/api/creditScore').then(m =>
      m.creditScoreApi.recompute(),
    )
    store.applyRecomputeResult(fresh)
    await store.refreshHistory({ force: true })
    if (previousScore !== null) {
      const delta = fresh.combine - previousScore
      const sign = delta > 0 ? '+' : delta < 0 ? '−' : ''
      const abs = Math.abs(delta)
      if (delta !== 0) {
        toast.push({
          severity: 'success',
          message: t('credit_score.recalc.toast_delta', { sign, value: abs }),
          duration: 3500,
        })
      }
      else {
        toast.push({
          severity: 'info',
          message: t('credit_score.recalc.toast_stable'),
          duration: 3000,
        })
      }
    }
    bus.emit('entity_updated', {
      eventType: 'entity_updated',
      entityType: 'credit_score',
      entityId: fresh.id,
      fieldsUpdated: ['combine'],
      source: 'manual',
      ts: new Date().toISOString(),
    })
  }
  catch {
    toast.push({
      severity: 'error',
      message: t('credit_score.recalc.toast_error'),
      duration: 5000,
    })
    await refresh()
  }
}
</script>

<template>
  <div class="mx-auto w-full max-w-5xl space-y-6 px-4 py-6">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">
        {{ t('credit_score.page_title') }}
      </h1>
      <p class="mt-1 text-sm text-slate-600">
        {{ t('credit_score.page_subtitle') }}
      </p>
    </header>

    <div
      v-if="loading && !score"
      class="rounded-2xl bg-white p-6 text-center text-slate-500 shadow-sm ring-1 ring-slate-200"
    >
      {{ t('credit_score.loading') }}
    </div>

    <div
      v-else-if="error && !score"
      class="rounded-2xl bg-red-50 p-6 text-center text-red-700 ring-1 ring-red-200"
      role="alert"
    >
      <p>{{ error }}</p>
      <button
        type="button"
        class="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        @click="refresh()"
      >
        {{ t('credit_score.error.retry') }}
      </button>
    </div>

    <!-- US8 — Wizard empty-state si aucun score -->
    <EmptyStateWizard
      v-else-if="!score"
      @submitted="refresh()"
    />

    <template v-else>
      <!-- Polish — Banner couverture partielle (FR-012a / clarif Q4) -->
      <PartialCoverageBanner
        v-if="score.partialCoverage"
        :subscores="score.subscores"
        @complete-clicked="openEdit"
      />

      <!-- US1 — Gauge synthèse -->
      <GaugeHero
        :score="score.combine"
        :score-prev="score.combinePrev"
        :classification="score.classification"
        :computed-at="score.computedAt"
        :loading="recalcLoading"
        @recalc-clicked="handleRecalcClick"
      />

      <!-- US6 — Bandeau recalcul + bouton édition -->
      <div class="flex flex-wrap items-center justify-between gap-3">
        <RecalcStrip
          class="flex-1 min-w-[260px]"
          :computed-at="score.computedAt"
          :loading="recalcLoading"
          @recompute="handleRecalcClick"
        />
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-emerald-700 shadow-sm ring-1 ring-emerald-300 hover:bg-emerald-50"
          @click="openEdit"
        >
          {{ t('credit_score.edit.open_cta') }}
        </button>
      </div>

      <!-- US2 — Sous-scores -->
      <SubScoreGrid
        :subscores="score.subscores"
        @complete-clicked="openEdit"
      />

      <!-- US3 — Badges éligibilité -->
      <section
        class="space-y-3"
        aria-labelledby="eligibility-title"
      >
        <header class="flex items-baseline justify-between gap-2">
          <h2
            id="eligibility-title"
            class="text-base font-semibold text-slate-900"
          >
            {{ t('credit_score.eligibility.section_title') }}
          </h2>
          <p class="text-xs text-slate-500">
            {{ t('credit_score.eligibility.section_hint') }}
          </p>
        </header>
        <div
          v-if="eligibility.loading.value && eligibility.items.value.length === 0"
          class="rounded-2xl bg-white p-4 text-center text-sm text-slate-500 ring-1 ring-slate-200"
        >
          {{ t('credit_score.eligibility.loading') }}
        </div>
        <div
          v-else-if="eligibility.items.value.length === 0"
          class="rounded-2xl bg-slate-50 p-4 text-center text-sm text-slate-600 ring-1 ring-slate-200"
        >
          {{ t('credit_score.eligibility.empty') }}
        </div>
        <div
          v-else
          class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <EligibilityBadge
            v-for="b in eligibility.items.value"
            :key="b.code"
            :badge="b"
            @details-clicked="onBadgeClick(b)"
          />
        </div>
      </section>

      <!-- US4 — Recommandations -->
      <RecommendationList
        :items="store.recommendations"
        :loading="store.loading.recommendations"
      />

      <!-- US7 — Historique -->
      <ScoreHistoryChart
        :entries="history.entries.value"
        :loading="history.loading.value"
      />
    </template>

    <footer class="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs text-slate-400">
      <a
        href="/methodologie/credit-scoring"
        class="hover:underline"
        target="_blank"
        rel="noopener"
      >{{ t('credit_score.methodology_link') }}</a>
      <!-- US10 (P2) — Export PDF placeholder -->
      <ExportPdfButton />
    </footer>

    <!-- US3 modal détail -->
    <EligibilityDetailModal
      :badge="detailBadge"
      :open="detailOpen"
      @update:open="detailOpen = $event"
    />

    <!-- US5 drawer édition -->
    <CreditDataDrawer
      :open="editOpen"
      @update:open="editOpen = $event"
      @submitted="refreshRecos"
    />
  </div>
</template>
