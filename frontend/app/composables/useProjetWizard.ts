// F43 T038 — useProjetWizard : 4 steps avec validation Zod par step + submit final.
//
// Pipeline :
//   step1 (nom + description) → step2 (secteur + type_impact)
//     → step3 (pays + région + lat/lng optionnels)
//     → step4 (budget + horizon)
//     → submit() → POST /me/projets via store.create()
//
// `canAdvance` reflète la validation Zod du step courant.
// `submit()` mappe vers `ProjetCreate` et délègue au store.
import { computed, reactive, ref, type ComputedRef, type Ref } from "vue"
import { z } from "zod"
import { useProjetsStore, type ProjetCreate, type ProjetRead } from "~/stores/projets"
import type { MoneyOut } from "~/stores/entreprise"

export type WizardStep = 1 | 2 | 3 | 4

export interface WizardData {
  step1: { nom: string; description: string }
  step2: { secteur: string; type_impact: string }
  step3: {
    localisation_pays_iso2: string
    localisation_region: string
    localisation_lat: string
    localisation_lng: string
  }
  step4: { budget: MoneyOut | null; horizon_mois: number | null }
}

const SCHEMAS = {
  step1: z.object({
    nom: z.string().min(3, "nom_min").max(120, "nom_max"),
    description: z.string().max(2000).optional().or(z.literal("")),
  }),
  step2: z.object({
    secteur: z.string().min(1, "required"),
    type_impact: z.string().min(1, "required"),
  }),
  step3: z.object({
    localisation_pays_iso2: z.string().length(2, "iso2"),
    localisation_region: z.string().min(1, "required"),
    localisation_lat: z.string().optional().or(z.literal("")),
    localisation_lng: z.string().optional().or(z.literal("")),
  }),
  step4: z.object({
    budget: z
      .object({
        amount: z.string().regex(/^-?\d+(\.\d+)?$/),
        currency: z.enum(["XOF", "EUR", "USD"]),
      })
      .nullable(),
    horizon_mois: z.number().int().min(1).max(240).nullable(),
  }),
} as const

export interface UseProjetWizard {
  step: Ref<WizardStep>
  data: WizardData
  errors: ComputedRef<Record<string, string>>
  canAdvance: ComputedRef<boolean>
  next: () => void
  prev: () => void
  submit: () => Promise<ProjetRead>
  reset: () => void
}

function buildInitial(): WizardData {
  return {
    step1: { nom: "", description: "" },
    step2: { secteur: "", type_impact: "" },
    step3: {
      localisation_pays_iso2: "",
      localisation_region: "",
      localisation_lat: "",
      localisation_lng: "",
    },
    step4: { budget: null, horizon_mois: null },
  }
}

export function useProjetWizard(): UseProjetWizard {
  const step = ref<WizardStep>(1)
  const data = reactive<WizardData>(buildInitial())
  const store = useProjetsStore()

  const errors = computed<Record<string, string>>(() => {
    const schema = SCHEMAS[`step${step.value}` as keyof typeof SCHEMAS]
    const stepData = data[`step${step.value}` as keyof WizardData]
    const result = schema.safeParse(stepData)
    if (result.success) return {}
    const out: Record<string, string> = {}
    for (const issue of result.error.issues) {
      out[issue.path.join(".") || "form"] = issue.message
    }
    return out
  })

  const canAdvance = computed(() => Object.keys(errors.value).length === 0)

  function next(): void {
    if (!canAdvance.value) return
    if (step.value < 4) step.value = ((step.value + 1) as WizardStep)
  }

  function prev(): void {
    if (step.value > 1) step.value = ((step.value - 1) as WizardStep)
  }

  function buildPayload(): ProjetCreate {
    const payload: ProjetCreate = {
      nom: data.step1.nom.trim(),
    }
    if (data.step1.description?.trim()) payload.description = data.step1.description.trim()
    if (data.step2.secteur) payload.secteur = data.step2.secteur
    if (data.step2.type_impact) payload.type_impact = data.step2.type_impact as ProjetCreate["type_impact"]
    if (data.step3.localisation_pays_iso2) payload.localisation_pays_iso2 = data.step3.localisation_pays_iso2
    if (data.step3.localisation_region) payload.localisation_region = data.step3.localisation_region
    if (data.step3.localisation_lat) payload.localisation_lat = data.step3.localisation_lat
    if (data.step3.localisation_lng) payload.localisation_lng = data.step3.localisation_lng
    if (data.step4.budget) payload.budget = data.step4.budget
    if (data.step4.horizon_mois != null) payload.horizon_mois = data.step4.horizon_mois
    return payload
  }

  async function submit(): Promise<ProjetRead> {
    if (!canAdvance.value) {
      throw new Error("wizard_invalid")
    }
    return await store.create(buildPayload())
  }

  function reset(): void {
    step.value = 1
    Object.assign(data, buildInitial())
  }

  return { step, data, errors, canAdvance, next, prev, submit, reset }
}
