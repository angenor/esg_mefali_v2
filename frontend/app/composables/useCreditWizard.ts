/**
 * F48 US8 — Composable useCreditWizard.
 *
 * Wizard 4 étapes (Financier → ESG → Gouvernance → Récap) avec persistance
 * localStorage `credit-score-wizard-{accountId}-{entrepriseId}`, TTL 7 jours.
 *
 * Soumission finale → POST /me/credit-data + POST /me/credit-score/recompute
 * → emit EventBus → bascule vers la vue synthèse.
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

export type WizardStepKey = 'financial' | 'esg' | 'governance' | 'summary'

const STEP_KEYS: WizardStepKey[] = ['financial', 'esg', 'governance', 'summary']
const TTL_MS = 7 * 24 * 60 * 60 * 1000 // 7 jours
const STORAGE_PREFIX = 'credit-score-wizard'

const ALLOWED_CURRENCIES = ['XOF', 'EUR', 'USD'] as const
type Currency = (typeof ALLOWED_CURRENCIES)[number]

export interface FinancialAnswers {
  chiffre_affaires?: MoneyValue
  ebe?: MoneyValue
  dette?: MoneyValue
  fonds_propres?: MoneyValue
}

export interface EsgAnswers {
  has_carbon_inventory?: boolean
  has_environmental_policy?: boolean
}

export interface GovernanceAnswers {
  has_board?: boolean
  has_compliance_program?: boolean
}

export interface WizardState {
  currentStep: WizardStepKey
  financial: FinancialAnswers
  esg: EsgAnswers
  governance: GovernanceAnswers
  savedAt: string
}

export interface UseCreditWizardApi {
  state: Ref<WizardState>
  currentStep: ComputedRef<WizardStepKey>
  isSubmitting: Ref<boolean>
  errors: Ref<Record<string, string | null>>
  setFinancial: (key: keyof FinancialAnswers, raw: { amount: string; currency: string }) => boolean
  setEsg: (key: keyof EsgAnswers, value: boolean) => void
  setGovernance: (key: keyof GovernanceAnswers, value: boolean) => void
  advance: () => boolean
  back: () => void
  restoreFromStorage: (accountId: string | null, entrepriseId: string | null) => boolean
  clearStorage: (accountId: string | null, entrepriseId: string | null) => void
  submitFinal: () => Promise<boolean>
}

function emptyState(): WizardState {
  return {
    currentStep: 'financial',
    financial: {},
    esg: {},
    governance: {},
    savedAt: new Date().toISOString(),
  }
}

function storageKey(accountId: string | null, entrepriseId: string | null): string {
  return `${STORAGE_PREFIX}-${accountId ?? 'anon'}-${entrepriseId ?? 'self'}`
}

function isAllowedCurrency(c: string): c is Currency {
  return (ALLOWED_CURRENCIES as readonly string[]).includes(c)
}

function validateMoney(
  raw: { amount: string; currency: string },
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
  if (dec.lt(0)) return { ok: false, reason: 'amount_negative' }
  return { ok: true, money: { amount: dec.toString(), currency: raw.currency } }
}

export function useCreditWizard(): UseCreditWizardApi {
  const store = useCreditScoreStore()
  const bus = useChatEventBus()
  const toast = useToast()
  const { t } = useT()

  const state = ref<WizardState>(emptyState())
  const isSubmitting = ref<boolean>(false)
  const errors = ref<Record<string, string | null>>({})

  const currentStep = computed<WizardStepKey>(() => state.value.currentStep)

  function persist(accountId: string | null, entrepriseId: string | null) {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem(
        storageKey(accountId, entrepriseId),
        JSON.stringify({ ...state.value, savedAt: new Date().toISOString() }),
      )
    }
    catch {
      // localStorage indisponible (mode privé, quota) — silencieux
    }
  }

  function setFinancial(
    key: keyof FinancialAnswers,
    raw: { amount: string; currency: string },
  ): boolean {
    const result = validateMoney(raw)
    if (!result.ok) {
      errors.value = { ...errors.value, [`financial.${key}`]: result.reason }
      return false
    }
    state.value = {
      ...state.value,
      financial: { ...state.value.financial, [key]: result.money },
    }
    errors.value = { ...errors.value, [`financial.${key}`]: null }
    return true
  }

  function setEsg(key: keyof EsgAnswers, value: boolean) {
    state.value = {
      ...state.value,
      esg: { ...state.value.esg, [key]: value },
    }
  }

  function setGovernance(key: keyof GovernanceAnswers, value: boolean) {
    state.value = {
      ...state.value,
      governance: { ...state.value.governance, [key]: value },
    }
  }

  function advance(): boolean {
    const idx = STEP_KEYS.indexOf(state.value.currentStep)
    if (idx === -1 || idx >= STEP_KEYS.length - 1) return false
    const nextStep = STEP_KEYS[idx + 1]!
    state.value = { ...state.value, currentStep: nextStep }
    return true
  }

  function back() {
    const idx = STEP_KEYS.indexOf(state.value.currentStep)
    if (idx <= 0) return
    const prev = STEP_KEYS[idx - 1]!
    state.value = { ...state.value, currentStep: prev }
  }

  function restoreFromStorage(
    accountId: string | null,
    entrepriseId: string | null,
  ): boolean {
    if (typeof window === 'undefined') return false
    try {
      const raw = window.localStorage.getItem(storageKey(accountId, entrepriseId))
      if (!raw) return false
      const parsed = JSON.parse(raw) as WizardState & { savedAt?: string }
      const savedAt = parsed.savedAt ? new Date(parsed.savedAt).getTime() : 0
      if (!savedAt || Date.now() - savedAt > TTL_MS) {
        window.localStorage.removeItem(storageKey(accountId, entrepriseId))
        return false
      }
      state.value = {
        currentStep: parsed.currentStep ?? 'financial',
        financial: parsed.financial ?? {},
        esg: parsed.esg ?? {},
        governance: parsed.governance ?? {},
        savedAt: parsed.savedAt ?? new Date().toISOString(),
      }
      toast.push({
        severity: 'info',
        message: t('credit_score.wizard.restored'),
        duration: 4000,
      })
      return true
    }
    catch {
      return false
    }
  }

  function clearStorage(accountId: string | null, entrepriseId: string | null) {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.removeItem(storageKey(accountId, entrepriseId))
    }
    catch {
      // ignore
    }
  }

  async function submitFinal(): Promise<boolean> {
    if (isSubmitting.value) return false
    const payload: CreditDeclarativePayload = {}
    const fin = state.value.financial
    if (fin.chiffre_affaires) payload.chiffre_affaires = fin.chiffre_affaires
    if (fin.ebe) payload.ebe = fin.ebe
    if (fin.dette) payload.dette = fin.dette
    if (fin.fonds_propres) payload.fonds_propres = fin.fonds_propres

    if (Object.keys(payload).length === 0) {
      errors.value = { ...errors.value, _global: 'no_financial_data' }
      toast.push({
        severity: 'error',
        message: t('credit_score.wizard.errors.no_data'),
        duration: 4500,
      })
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

      // Reset state + clear localStorage
      state.value = emptyState()
      // Note: l'appelant fournira accountId/entrepriseId pour clearStorage si besoin

      toast.push({
        severity: 'success',
        message: t('credit_score.wizard.success'),
        duration: 3500,
      })
      return true
    }
    catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('credit_score.wizard.errors.submit_failed')
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
    state,
    currentStep,
    isSubmitting,
    errors,
    setFinancial,
    setEsg,
    setGovernance,
    advance,
    back,
    restoreFromStorage,
    clearStorage,
    submitFinal,
  }
}

// Helper interne exposé pour `EmptyStateWizard.vue` : persiste après chaque advance
export function persistWizard(
  state: WizardState,
  accountId: string | null,
  entrepriseId: string | null,
): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(
      storageKey(accountId, entrepriseId),
      JSON.stringify({ ...state, savedAt: new Date().toISOString() }),
    )
  }
  catch {
    // ignore
  }
}
