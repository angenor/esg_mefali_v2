<!--
  F48 US8 — EmptyStateWizard
  Wizard 4 étapes (Financier → ESG → Gouvernance → Récap) pour les comptes
  sans score initial. Persistance localStorage + reprise via TTL 7 jours.
  Soumission finale → POST credit-data + recompute → bascule vers la synthèse.
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  useCreditWizard,
  persistWizard,
  type WizardStepKey,
} from '~/composables/useCreditWizard'
import { useT } from '~/composables/useT'

interface Props {
  accountId?: string | null
  entrepriseId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  accountId: null,
  entrepriseId: null,
})

const emit = defineEmits<{
  (e: 'submitted'): void
}>()

const { t } = useT()
const wizard = useCreditWizard()

const FIN_FIELDS = [
  'chiffre_affaires',
  'ebe',
  'dette',
  'fonds_propres',
] as const

// Buffer local pour saisie financière (montant + devise par champ)
type FinKey = (typeof FIN_FIELDS)[number]
const buffer = ref<Record<FinKey, { amount: string; currency: 'XOF' | 'EUR' | 'USD' }>>({
  chiffre_affaires: { amount: '', currency: 'XOF' },
  ebe: { amount: '', currency: 'XOF' },
  dette: { amount: '', currency: 'XOF' },
  fonds_propres: { amount: '', currency: 'XOF' },
})

const stepNumber = computed<number>(() => {
  const order: WizardStepKey[] = ['financial', 'esg', 'governance', 'summary']
  return order.indexOf(wizard.currentStep.value) + 1
})

onMounted(() => {
  wizard.restoreFromStorage(props.accountId, props.entrepriseId)
  // Réhydrate le buffer financier si l'état restauré contient des valeurs
  for (const k of FIN_FIELDS) {
    const m = wizard.state.value.financial[k]
    if (m) {
      buffer.value[k] = {
        amount: m.amount,
        currency: m.currency as 'XOF' | 'EUR' | 'USD',
      }
    }
  }
})

watch(
  () => wizard.state.value,
  (s) => persistWizard(s, props.accountId, props.entrepriseId),
  { deep: true },
)

function commitFinancialBuffer(): boolean {
  let allOk = true
  for (const k of FIN_FIELDS) {
    const raw = buffer.value[k]
    if (!raw.amount.trim()) continue // champ optionnel
    const ok = wizard.setFinancial(k, raw)
    if (!ok) allOk = false
  }
  return allOk
}

function onAdvance() {
  const step = wizard.currentStep.value
  if (step === 'financial') {
    const ok = commitFinancialBuffer()
    if (!ok) return
    // Au moins une valeur financière doit être saisie
    const hasAny = FIN_FIELDS.some((k) => wizard.state.value.financial[k] !== undefined)
    if (!hasAny) {
      wizard.errors.value = { ...wizard.errors.value, _global: 'need_at_least_one' }
      return
    }
    wizard.errors.value = { ...wizard.errors.value, _global: null }
  }
  wizard.advance()
}

async function onSubmit() {
  const ok = await wizard.submitFinal()
  if (ok) {
    wizard.clearStorage(props.accountId, props.entrepriseId)
    emit('submitted')
  }
}

function fieldError(key: FinKey): string | null {
  const code = wizard.errors.value[`financial.${key}`]
  if (!code) return null
  return t(`credit_score.edit.errors.${code}` as const)
}
</script>

<template>
  <section
    class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
    aria-labelledby="wizard-title"
  >
    <header class="mb-4">
      <p class="text-xs font-medium uppercase tracking-wide text-emerald-700">
        {{ t('credit_score.wizard.step_progress', { current: stepNumber, total: 4 }) }}
      </p>
      <h2
        id="wizard-title"
        class="mt-1 text-xl font-bold text-slate-900"
      >
        {{ t(`credit_score.wizard.step.${wizard.currentStep.value}` as const) }}
      </h2>
      <p class="mt-1 text-sm text-slate-600">
        {{ t(`credit_score.wizard.intro.${wizard.currentStep.value}` as const) }}
      </p>
    </header>

    <!-- Étape 1 — Financier -->
    <div
      v-if="wizard.currentStep.value === 'financial'"
      class="space-y-4"
    >
      <div
        v-for="key in FIN_FIELDS"
        :key="key"
        class="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]"
      >
        <div>
          <label
            :for="`wiz-${key}`"
            class="block text-sm font-medium text-slate-700"
          >
            {{ t(`credit_score.edit.step.${key}` as const) }}
          </label>
          <input
            :id="`wiz-${key}`"
            v-model="buffer[key].amount"
            type="text"
            inputmode="decimal"
            class="mt-1 block w-full rounded-md px-3 py-2 text-sm shadow-sm ring-1 ring-slate-300 focus:border-emerald-500 focus:ring-emerald-500"
            :placeholder="t('credit_score.edit.amount_placeholder')"
            :aria-invalid="fieldError(key) !== null"
          >
          <p
            v-if="fieldError(key)"
            class="mt-1 text-xs text-red-700"
            role="alert"
          >
            {{ fieldError(key) }}
          </p>
        </div>
        <div>
          <label
            :for="`wiz-${key}-cur`"
            class="block text-sm font-medium text-slate-700"
          >
            {{ t('credit_score.edit.currency_label') }}
          </label>
          <select
            :id="`wiz-${key}-cur`"
            v-model="buffer[key].currency"
            class="mt-1 block rounded-md px-3 py-2 text-sm shadow-sm ring-1 ring-slate-300 focus:border-emerald-500 focus:ring-emerald-500"
          >
            <option value="XOF">
              XOF (FCFA)
            </option>
            <option value="EUR">
              EUR
            </option>
            <option value="USD">
              USD
            </option>
          </select>
        </div>
      </div>
      <p
        v-if="wizard.errors.value._global === 'need_at_least_one'"
        class="text-sm text-red-700"
        role="alert"
      >
        {{ t('credit_score.wizard.errors.need_at_least_one') }}
      </p>
    </div>

    <!-- Étape 2 — ESG -->
    <div
      v-else-if="wizard.currentStep.value === 'esg'"
      class="space-y-3"
    >
      <label class="flex items-start gap-3 rounded-md p-3 ring-1 ring-slate-200 hover:bg-slate-50">
        <input
          type="checkbox"
          :checked="wizard.state.value.esg.has_carbon_inventory ?? false"
          class="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
          @change="(e) => wizard.setEsg('has_carbon_inventory', (e.target as HTMLInputElement).checked)"
        >
        <span>
          <span class="block text-sm font-medium text-slate-900">{{ t('credit_score.wizard.esg.carbon_inventory') }}</span>
          <span class="block text-xs text-slate-600">{{ t('credit_score.wizard.esg.carbon_inventory_hint') }}</span>
        </span>
      </label>
      <label class="flex items-start gap-3 rounded-md p-3 ring-1 ring-slate-200 hover:bg-slate-50">
        <input
          type="checkbox"
          :checked="wizard.state.value.esg.has_environmental_policy ?? false"
          class="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
          @change="(e) => wizard.setEsg('has_environmental_policy', (e.target as HTMLInputElement).checked)"
        >
        <span>
          <span class="block text-sm font-medium text-slate-900">{{ t('credit_score.wizard.esg.env_policy') }}</span>
          <span class="block text-xs text-slate-600">{{ t('credit_score.wizard.esg.env_policy_hint') }}</span>
        </span>
      </label>
    </div>

    <!-- Étape 3 — Gouvernance -->
    <div
      v-else-if="wizard.currentStep.value === 'governance'"
      class="space-y-3"
    >
      <label class="flex items-start gap-3 rounded-md p-3 ring-1 ring-slate-200 hover:bg-slate-50">
        <input
          type="checkbox"
          :checked="wizard.state.value.governance.has_board ?? false"
          class="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
          @change="(e) => wizard.setGovernance('has_board', (e.target as HTMLInputElement).checked)"
        >
        <span>
          <span class="block text-sm font-medium text-slate-900">{{ t('credit_score.wizard.gov.board') }}</span>
          <span class="block text-xs text-slate-600">{{ t('credit_score.wizard.gov.board_hint') }}</span>
        </span>
      </label>
      <label class="flex items-start gap-3 rounded-md p-3 ring-1 ring-slate-200 hover:bg-slate-50">
        <input
          type="checkbox"
          :checked="wizard.state.value.governance.has_compliance_program ?? false"
          class="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
          @change="(e) => wizard.setGovernance('has_compliance_program', (e.target as HTMLInputElement).checked)"
        >
        <span>
          <span class="block text-sm font-medium text-slate-900">{{ t('credit_score.wizard.gov.compliance') }}</span>
          <span class="block text-xs text-slate-600">{{ t('credit_score.wizard.gov.compliance_hint') }}</span>
        </span>
      </label>
    </div>

    <!-- Étape 4 — Récap -->
    <div
      v-else-if="wizard.currentStep.value === 'summary'"
      class="space-y-2"
    >
      <dl class="divide-y divide-slate-200 rounded-lg ring-1 ring-slate-200 text-sm">
        <div
          v-for="k in FIN_FIELDS"
          :key="k"
          class="flex items-baseline justify-between gap-2 px-4 py-2"
        >
          <dt class="text-slate-600">
            {{ t(`credit_score.edit.step.${k}` as const) }}
          </dt>
          <dd class="font-medium text-slate-900">
            <template v-if="wizard.state.value.financial[k]">
              {{ wizard.state.value.financial[k]!.amount }} {{ wizard.state.value.financial[k]!.currency }}
            </template>
            <template v-else>—</template>
          </dd>
        </div>
        <div class="flex items-baseline justify-between gap-2 px-4 py-2">
          <dt class="text-slate-600">
            {{ t('credit_score.wizard.esg.section_label') }}
          </dt>
          <dd class="font-medium text-slate-900">
            {{ Object.values(wizard.state.value.esg).filter(Boolean).length }} / 2
          </dd>
        </div>
        <div class="flex items-baseline justify-between gap-2 px-4 py-2">
          <dt class="text-slate-600">
            {{ t('credit_score.wizard.gov.section_label') }}
          </dt>
          <dd class="font-medium text-slate-900">
            {{ Object.values(wizard.state.value.governance).filter(Boolean).length }} / 2
          </dd>
        </div>
      </dl>
      <p
        v-if="wizard.errors.value._global === 'submit_failed'"
        class="text-sm text-red-700"
        role="alert"
      >
        {{ t('credit_score.wizard.errors.submit_failed') }}
      </p>
    </div>

    <!-- Actions -->
    <footer class="mt-6 flex flex-wrap items-center justify-between gap-2">
      <button
        v-if="stepNumber > 1"
        type="button"
        class="rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
        :disabled="wizard.isSubmitting.value"
        @click="wizard.back"
      >
        {{ t('credit_score.edit.back') }}
      </button>
      <span
        v-else
        class="text-xs text-slate-400"
      >
        {{ t('credit_score.wizard.persisted_hint') }}
      </span>

      <button
        v-if="wizard.currentStep.value !== 'summary'"
        type="button"
        class="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        @click="onAdvance"
      >
        {{ t('credit_score.edit.next') }}
      </button>
      <button
        v-else
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
        :disabled="wizard.isSubmitting.value"
        @click="onSubmit"
      >
        <svg
          v-if="wizard.isSubmitting.value"
          class="h-4 w-4 animate-spin"
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
        {{ t('credit_score.wizard.submit') }}
      </button>
    </footer>
  </section>
</template>
