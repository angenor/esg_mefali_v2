// F47 T075 [US6] — Wizard empty-state 3 étapes : énergie / mobilité / achats.
//
// Persistance partielle dans localStorage (TTL 7 jours via store), submit final
// vers POST /me/carbon/compute. Bouton `Répondre librement` ouvre le chat.
//
// Cf. specs/047-empreinte-carbone-ui/spec.md US6 et data-model.md §3.4.

import { computed, ref, type ComputedRef, type Ref } from "vue"
import { z } from "zod"
import { useCarbonStore } from "~/stores/carbon"
import { useChatBottomSheet } from "~/composables/useChatBottomSheet"
import { useChatEventBus } from "~/composables/useChatEventBus"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import { carbonApi } from "~/services/api/carbon"
import type {
  CarbonFootprint,
  CarbonSourceItemPayload,
  WizardAnswers,
  WizardDraft,
} from "~/types/carbon"

export type WizardStepKey = "energy" | "mobility" | "purchases"
export type WizardStepNumber = 1 | 2 | 3

const STEP_KEYS: WizardStepKey[] = ["energy", "mobility", "purchases"]

const SCHEMAS = {
  energy: z.object({
    quantity: z.string().regex(/^\d+(\.\d+)?$/, "quantity_invalid"),
    unit: z.enum(["kWh", "MJ"]),
    source_id: z.string().uuid("source_required"),
  }),
  mobility: z.object({
    quantity: z.string().regex(/^\d+(\.\d+)?$/, "quantity_invalid"),
    unit: z.enum(["km", "litre"]),
    source_id: z.string().uuid("source_required"),
  }),
  purchases: z.object({
    quantity: z.string().regex(/^\d+(\.\d+)?$/, "quantity_invalid"),
    unit: z.enum(["EUR", "FCFA"]),
    source_id: z.string().uuid("source_required"),
  }),
} as const

const POSTE_BY_STEP: Record<WizardStepKey, string> = {
  energy: "electricite",
  mobility: "deplacements",
  purchases: "achats",
}

export interface UseCarbonWizardApi {
  draft: ComputedRef<WizardDraft | null>
  step: ComputedRef<WizardStepNumber>
  stepKey: ComputedRef<WizardStepKey>
  isSubmitting: Ref<boolean>
  start(year: number, accountId?: string | null): void
  setAnswer<K extends WizardStepKey>(
    stepKey: K,
    payload: NonNullable<WizardAnswers[K]>,
  ): void
  nextStep(): boolean
  previousStep(): void
  hydrate(accountId?: string | null): void
  submit(accountId?: string | null): Promise<CarbonFootprint | null>
  cancel(accountId?: string | null): void
  freeText(): Promise<void>
}

export function useCarbonWizard(): UseCarbonWizardApi {
  const store = useCarbonStore()
  const sheet = useChatBottomSheet()
  const bus = useChatEventBus()
  const toast = useToast()
  const { t } = useT()

  const isSubmitting = ref<boolean>(false)
  const draft = computed<WizardDraft | null>(() => store.wizardDraft)
  const step = computed<WizardStepNumber>(
    () => (store.wizardDraft?.step ?? 1) as WizardStepNumber,
  )
  const stepKey = computed<WizardStepKey>(
    () => STEP_KEYS[step.value - 1] ?? "energy",
  )

  function persist(
    accountId: string | null | undefined,
    next: WizardDraft | null,
  ): void {
    store.setWizardDraft(accountId ?? null, next)
  }

  function start(year: number, accountId: string | null = null): void {
    const next: WizardDraft = {
      step: 1,
      year,
      answers: {},
      saved_at: new Date().toISOString(),
    }
    persist(accountId, next)
  }

  function setAnswer<K extends WizardStepKey>(
    key: K,
    payload: NonNullable<WizardAnswers[K]>,
  ): void {
    const current = store.wizardDraft
    if (!current) return
    const accountId = null
    const validated = SCHEMAS[key].safeParse(payload)
    if (!validated.success) {
      toast.push({
        severity: "error",
        message: t("carbon.editLine.sourceRequired"),
        duration: 4000,
      })
      return
    }
    const nextAnswers: WizardAnswers = {
      ...current.answers,
      [key]: payload,
    }
    persist(accountId, {
      ...current,
      answers: nextAnswers,
      saved_at: new Date().toISOString(),
    })
  }

  function nextStep(): boolean {
    const current = store.wizardDraft
    if (!current) return false
    const key = STEP_KEYS[current.step - 1]
    if (!key) return false
    const answer = current.answers[key]
    if (!answer) return false
    const validated = SCHEMAS[key].safeParse(answer)
    if (!validated.success) return false
    if (current.step >= 3) return true
    persist(null, {
      ...current,
      step: ((current.step + 1) as WizardStepNumber),
      saved_at: new Date().toISOString(),
    })
    return true
  }

  function previousStep(): void {
    const current = store.wizardDraft
    if (!current || current.step <= 1) return
    persist(null, {
      ...current,
      step: ((current.step - 1) as WizardStepNumber),
      saved_at: new Date().toISOString(),
    })
  }

  function hydrate(accountId: string | null = null): void {
    store.hydrateWizardDraft(accountId)
  }

  async function submit(
    accountId: string | null = null,
  ): Promise<CarbonFootprint | null> {
    if (isSubmitting.value) return null
    const current = store.wizardDraft
    if (!current) return null
    const sourceData: CarbonSourceItemPayload[] = []
    for (const key of STEP_KEYS) {
      const ans = current.answers[key]
      if (!ans) {
        toast.push({
          severity: "error",
          message: t("carbon.wizard.partialSaved"),
          duration: 4000,
        })
        return null
      }
      const validated = SCHEMAS[key].safeParse(ans)
      if (!validated.success) return null
      sourceData.push({
        code: POSTE_BY_STEP[key],
        quantity: ans.quantity,
        source_id: ans.source_id,
      })
    }
    isSubmitting.value = true
    try {
      const fp = await carbonApi.computeInitial(current.year, sourceData)
      store.applyFootprint(current.year, fp)
      persist(accountId, null)
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "carbon_footprint",
        entityId: fp.id,
        fieldsUpdated: [`year:${current.year}`, "wizard"],
        source: "manual",
        ts: new Date().toISOString(),
      })
      toast.push({
        severity: "success",
        message: t("carbon.wizard.success"),
        duration: 4000,
      })
      return fp
    } catch (err: unknown) {
      toast.push({
        severity: "error",
        message: t("carbon.errors.generic"),
        duration: 5000,
      })
      void err
      return null
    } finally {
      isSubmitting.value = false
    }
  }

  function cancel(accountId: string | null = null): void {
    persist(accountId, null)
  }

  async function freeText(): Promise<void> {
    await sheet.close("freetext")
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("carbon:wizard:freetext", { detail: { source: "wizard" } }),
      )
    }
  }

  return {
    draft,
    step,
    stepKey,
    isSubmitting,
    start,
    setAnswer,
    nextStep,
    previousStep,
    hydrate,
    submit,
    cancel,
    freeText,
  }
}
