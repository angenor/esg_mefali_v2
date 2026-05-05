<!--
  F48 US5 — CreditDataDrawer
  Drawer 4 étapes (CA / EBE / Dette / Fonds propres → Récap) basé sur UiModal.
  Saisie typée Money (montant + devise XOF/EUR/USD) avec validation `useCreditEdit`.
  Soumission finale → POST credit-data + POST recompute + EventBus.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import UiModal from '~/components/ui/UiModal.vue'
import { useCreditEdit, type CreditEditStepKey } from '~/composables/useCreditEdit'
import { useT } from '~/composables/useT'

interface Props {
  open: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'submitted'): void
}>()

const { t } = useT()
const edit = useCreditEdit()

const STEP_KEYS_INPUT: Exclude<CreditEditStepKey, 'recap'>[] = [
  'chiffre_affaires',
  'ebe',
  'dette',
  'fonds_propres',
]

// Buffer local pour la saisie (montant + devise) à chaque étape.
const buffer = ref<{ amount: string; currency: 'XOF' | 'EUR' | 'USD' }>({
  amount: '',
  currency: 'XOF',
})

watch(
  () => props.open,
  (v) => {
    if (v) {
      edit.openDrawer()
      buffer.value = { amount: '', currency: 'XOF' }
    }
    else {
      edit.closeDrawer()
    }
  },
  { immediate: true },
)

watch(edit.currentStep, (step) => {
  if (step === 'recap') return
  const existing = edit.values.value[step]
  buffer.value = existing
    ? { amount: existing.amount, currency: existing.currency as 'XOF' | 'EUR' | 'USD' }
    : { amount: '', currency: 'XOF' }
})

const stepLabel = computed<string>(() => {
  const k = edit.currentStep.value
  if (k === 'recap') return t('credit_score.edit.step.recap')
  return t(`credit_score.edit.step.${k}` as const)
})

const stepHint = computed<string>(() => {
  const k = edit.currentStep.value
  if (k === 'recap') return t('credit_score.edit.recap_hint')
  return t(`credit_score.edit.hint.${k}` as const)
})

const stepNumber = computed<number>(() => {
  const k = edit.currentStep.value
  return k === 'recap' ? 5 : STEP_KEYS_INPUT.indexOf(k) + 1
})

const stepError = computed<string | null>(() => {
  const k = edit.currentStep.value
  if (k === 'recap') return null
  const code = edit.errors.value[k]
  if (!code) return null
  return t(`credit_score.edit.errors.${code}` as const)
})

function close() {
  if (edit.isSubmitting.value) return
  emit('update:open', false)
}

function onNext() {
  const step = edit.currentStep.value
  if (step === 'recap') return
  const ok = edit.setValue(step, buffer.value)
  if (!ok) return
  edit.next()
}

function onBack() {
  edit.back()
}

async function onSubmit() {
  const ok = await edit.submitFinal()
  if (ok) {
    emit('update:open', false)
    emit('submitted')
  }
}

function formatMoney(step: Exclude<CreditEditStepKey, 'recap'>): string {
  const m = edit.values.value[step]
  if (!m) return '—'
  const num = Number(m.amount)
  if (Number.isNaN(num)) return `${m.amount} ${m.currency}`
  return `${num.toLocaleString('fr-FR')} ${m.currency}`
}
</script>

<template>
  <UiModal
    :model-value="open"
    size="lg"
    :persistent="edit.isSubmitting.value"
    :aria-label="t('credit_score.edit.modal_title')"
    @close="close"
    @update:model-value="emit('update:open', $event)"
  >
    <div class="space-y-5 p-1">
      <header>
        <p class="text-xs font-medium uppercase tracking-wide text-emerald-700">
          {{ t('credit_score.edit.step_progress', { current: stepNumber, total: 5 }) }}
        </p>
        <h2 class="mt-1 text-lg font-semibold text-slate-900">
          {{ stepLabel }}
        </h2>
        <p class="mt-1 text-sm text-slate-600">
          {{ stepHint }}
        </p>
      </header>

      <!-- Étape input (1..4) -->
      <section
        v-if="edit.currentStep.value !== 'recap'"
        class="space-y-3"
      >
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto]">
          <div>
            <label
              :for="`credit-edit-amount-${edit.currentStep.value}`"
              class="block text-sm font-medium text-slate-700"
            >
              {{ t('credit_score.edit.amount_label') }}
            </label>
            <input
              :id="`credit-edit-amount-${edit.currentStep.value}`"
              v-model="buffer.amount"
              type="text"
              inputmode="decimal"
              class="mt-1 block w-full rounded-md border-slate-300 px-3 py-2 text-sm shadow-sm ring-1 ring-slate-300 focus:border-emerald-500 focus:ring-emerald-500"
              :placeholder="t('credit_score.edit.amount_placeholder')"
              :aria-invalid="stepError !== null"
            >
          </div>
          <div>
            <label
              :for="`credit-edit-currency-${edit.currentStep.value}`"
              class="block text-sm font-medium text-slate-700"
            >
              {{ t('credit_score.edit.currency_label') }}
            </label>
            <select
              :id="`credit-edit-currency-${edit.currentStep.value}`"
              v-model="buffer.currency"
              class="mt-1 block rounded-md border-slate-300 px-3 py-2 text-sm shadow-sm ring-1 ring-slate-300 focus:border-emerald-500 focus:ring-emerald-500"
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
          v-if="stepError"
          class="text-sm text-red-700"
          role="alert"
        >
          {{ stepError }}
        </p>
      </section>

      <!-- Étape récap (5) -->
      <section
        v-else
        class="space-y-2"
      >
        <dl class="divide-y divide-slate-200 rounded-lg ring-1 ring-slate-200">
          <div
            v-for="k in STEP_KEYS_INPUT"
            :key="k"
            class="flex items-baseline justify-between gap-2 px-4 py-2 text-sm"
          >
            <dt class="text-slate-600">
              {{ t(`credit_score.edit.step.${k}` as const) }}
            </dt>
            <dd class="font-medium text-slate-900">
              {{ formatMoney(k) }}
            </dd>
          </div>
        </dl>
        <p
          v-if="edit.errors.value._global"
          class="text-sm text-red-700"
          role="alert"
        >
          {{ t('credit_score.edit.errors.submit_failed') }}
        </p>
      </section>

      <!-- Footer actions -->
      <footer class="flex flex-wrap items-center justify-between gap-2 pt-2">
        <button
          type="button"
          class="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
          :disabled="edit.isSubmitting.value"
          @click="close"
        >
          {{ t('credit_score.edit.cancel') }}
        </button>

        <div class="flex items-center gap-2">
          <button
            v-if="stepNumber > 1"
            type="button"
            class="rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
            :disabled="edit.isSubmitting.value"
            @click="onBack"
          >
            {{ t('credit_score.edit.back') }}
          </button>
          <button
            v-if="edit.currentStep.value !== 'recap'"
            type="button"
            class="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            @click="onNext"
          >
            {{ t('credit_score.edit.next') }}
          </button>
          <button
            v-else
            type="button"
            class="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="edit.isSubmitting.value"
            @click="onSubmit"
          >
            <svg
              v-if="edit.isSubmitting.value"
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
            {{ t('credit_score.edit.submit') }}
          </button>
        </div>
      </footer>
    </div>
  </UiModal>
</template>
