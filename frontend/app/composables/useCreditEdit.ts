/**
 * F48 US5+US6 — Composable useCreditEdit.
 *
 * Orchestre l'édition financière déclarative en 4 étapes
 * (CA → EBE → Dette → Fonds propres) puis le recalcul.
 * Validation Money via decimal.js, soumission séquentielle :
 *   POST /me/credit-data → POST /me/credit-score/recompute → emit EventBus.
 *
 * Cf. specs/048-credit-scoring-ui/data-model.md « Règles de validation ».
 */

import { computed, ref, type ComputedRef, type Ref } from 'vue'
import Decimal from 'decimal.js'
import { creditScoreApi } from '~/services/api/creditScore'
import { useCreditScoreStore } from '~/stores/creditScore'
import { useChatEventBus } from '~/composables/useChatEventBus'
import { useToast } from '~/composables/useToast'
import { useT } from '~/composables/useT'
import type {
  CreditDeclarativePayload,
  MoneyValue,
} from '~/types/creditScore'

export type CreditEditStepKey =
  | 'chiffre_affaires'
  | 'ebe'
  | 'dette'
  | 'fonds_propres'
  | 'recap'

const STEP_ORDER: CreditEditStepKey[] = [
  'chiffre_affaires',
  'ebe',
  'dette',
  'fonds_propres',
  'recap',
]

const ALLOWED_CURRENCIES = ['XOF', 'EUR', 'USD'] as const
type Currency = (typeof ALLOWED_CURRENCIES)[number]

export interface CreditEditValues {
  chiffre_affaires: MoneyValue | null
  ebe: MoneyValue | null
  dette: MoneyValue | null
  fonds_propres: MoneyValue | null
}

export interface UseCreditEditApi {
  isOpen: Ref<boolean>
  isSubmitting: Ref<boolean>
  currentStep: ComputedRef<CreditEditStepKey>
  values: Ref<CreditEditValues>
  errors: Ref<Record<string, string | null>>
  openDrawer: () => void
  closeDrawer: () => void
  setValue: (step: Exclude<CreditEditStepKey, 'recap'>, raw: { amount: string; currency: string }) => boolean
  next: () => boolean
  back: () => void
  submitFinal: () => Promise<boolean>
}

function emptyValues(): CreditEditValues {
  return {
    chiffre_affaires: null,
    ebe: null,
    dette: null,
    fonds_propres: null,
  }
}

function isAllowedCurrency(c: string): c is Currency {
  return (ALLOWED_CURRENCIES as readonly string[]).includes(c)
}

function validateMoney(
  raw: { amount: string; currency: string },
  step: Exclude<CreditEditStepKey, 'recap'>,
): { ok: true; money: MoneyValue } | { ok: false; reason: string } {
  if (!raw.currency) return { ok: false, reason: 'currency_required' }
  if (!isAllowedCurrency(raw.currency)) return { ok: false, reason: 'currency_invalid' }
  if (!raw.amount?.trim()) return { ok: false, reason: 'amount_required' }
  let dec: Decimal
  try {
    dec = new Decimal(raw.amount.replace(',', '.'))
  }
  catch {
    return { ok: false, reason: 'amount_invalid' }
  }
  if (!dec.isFinite()) return { ok: false, reason: 'amount_invalid' }
  // dette peut être 0 ; les autres doivent rester ≥ 0 (validations métier
  // additionnelles dans le backend) — on refuse simplement les négatifs côté front.
  if (dec.lt(0)) return { ok: false, reason: 'amount_negative' }
  // EBE / fonds propres peuvent être négatifs métier mais le contrat MVP F48
  // limite la saisie à montants positifs ; on traite les cas avancés via chat.
  if (step === 'fonds_propres' && dec.lt(0)) {
    return { ok: false, reason: 'amount_negative' }
  }
  return { ok: true, money: { amount: dec.toString(), currency: raw.currency } }
}

export function useCreditEdit(): UseCreditEditApi {
  const store = useCreditScoreStore()
  const bus = useChatEventBus()
  const toast = useToast()
  const { t } = useT()

  const isOpen = ref<boolean>(false)
  const isSubmitting = ref<boolean>(false)
  const stepIndex = ref<number>(0)
  const values = ref<CreditEditValues>(emptyValues())
  const errors = ref<Record<string, string | null>>({})

  const currentStep = computed<CreditEditStepKey>(
    () => STEP_ORDER[stepIndex.value] ?? 'recap',
  )

  function reset() {
    stepIndex.value = 0
    values.value = emptyValues()
    errors.value = {}
  }

  function openDrawer() {
    if (isOpen.value) return
    reset()
    isOpen.value = true
  }

  function closeDrawer() {
    if (isSubmitting.value) return
    isOpen.value = false
  }

  function setValue(
    step: Exclude<CreditEditStepKey, 'recap'>,
    raw: { amount: string; currency: string },
  ): boolean {
    const result = validateMoney(raw, step)
    if (!result.ok) {
      errors.value = { ...errors.value, [step]: result.reason }
      return false
    }
    values.value = { ...values.value, [step]: result.money }
    errors.value = { ...errors.value, [step]: null }
    return true
  }

  function next(): boolean {
    if (stepIndex.value >= STEP_ORDER.length - 1) return false
    stepIndex.value += 1
    return true
  }

  function back() {
    if (stepIndex.value === 0) return
    stepIndex.value -= 1
  }

  async function submitFinal(): Promise<boolean> {
    if (isSubmitting.value) return false
    const payload: CreditDeclarativePayload = {}
    if (values.value.chiffre_affaires) payload.chiffre_affaires = values.value.chiffre_affaires
    if (values.value.ebe) payload.ebe = values.value.ebe
    if (values.value.dette) payload.dette = values.value.dette
    if (values.value.fonds_propres) payload.fonds_propres = values.value.fonds_propres

    if (Object.keys(payload).length === 0) {
      errors.value = { ...errors.value, _global: 'no_data' }
      return false
    }

    isSubmitting.value = true
    try {
      await creditScoreApi.submitDeclarative(payload)

      bus.emit('entity_updated', {
        eventType: 'entity_updated',
        entityType: 'credit_data',
        entityId: 'me',
        fieldsUpdated: Object.keys(payload),
        source: 'manual',
        ts: new Date().toISOString(),
      })

      const fresh = await creditScoreApi.recompute()
      store.applyRecomputeResult(fresh)
      await store.refreshHistory({ force: true })

      bus.emit('entity_updated', {
        eventType: 'entity_updated',
        entityType: 'credit_score',
        entityId: fresh.id,
        fieldsUpdated: ['combine'],
        source: 'manual',
        ts: new Date().toISOString(),
      })

      toast.push({
        severity: 'success',
        message: t('credit_score.edit.success'),
        duration: 3500,
      })

      isOpen.value = false
      reset()
      return true
    }
    catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('credit_score.edit.error')
      toast.push({
        severity: 'error',
        message,
        duration: 5000,
      })
      errors.value = { ...errors.value, _global: 'submit_failed' }
      return false
    }
    finally {
      isSubmitting.value = false
    }
  }

  return {
    isOpen,
    isSubmitting,
    currentStep,
    values,
    errors,
    openDrawer,
    closeDrawer,
    setValue,
    next,
    back,
    submitFinal,
  }
}
