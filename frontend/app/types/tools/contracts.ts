/**
 * Schémas zod manuels — F39, mirror des Pydantic backend (F15).
 *
 * Source de vérité : `specs/039-bottom-sheet-engine/contracts/tool-payloads.md`.
 * Ces schémas servent à la validation runtime côté UI (R6 — payload reçu via SSE/thread,
 * et `ToolResponse` émise vers le backend).
 *
 * Quand `pnpm gen:tools` produit un fichier auto-généré pour un tool, le schéma manuel
 * d'ici reste l'autorité jusqu'à preuve d'écart : le générateur extrait juste le JSON
 * Schema brut du backend pour comparaison.
 */
import { z } from 'zod'

// ---- Sub-schemas réutilisables ----

const optionSchema = z.object({
  value: z.string(),
  label: z.string(),
  description: z.string().optional(),
})

const isoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'date ISO YYYY-MM-DD attendue')
const isoCurrencySchema = z.string().regex(/^[A-Z]{3}$/, 'code ISO 4217 (3 lettres maj.)')
const decimalSchema = z.string().regex(/^-?\d+(\.\d+)?$/, 'décimal attendu (string)')
const uuidSchema = z.string().uuid()

// ---- Payloads (instructions reçues du backend) ----

export const askYesNoPayload = z
  .object({ question: z.string().min(1), yes_label: z.string().optional(), no_label: z.string().optional() })
  .strict()

export const askQcuPayload = z
  .object({
    question: z.string().min(1),
    options: z.array(optionSchema).min(2).max(10),
    allow_other: z.boolean().optional(),
  })
  .strict()

export const askQcmPayload = z
  .object({
    question: z.string().min(1),
    options: z.array(z.object({ value: z.string(), label: z.string() })).min(1),
    min_select: z.number().int().min(0).optional(),
    max_select: z.number().int().min(1).optional(),
  })
  .strict()

export const askSelectPayload = z
  .object({
    question: z.string().min(1),
    options: z.array(z.object({ value: z.string(), label: z.string() })).optional(),
    options_endpoint: z.string().min(1).optional(),
    search_placeholder: z.string().optional(),
    multiple: z.boolean().optional(),
  })
  .strict()
  .refine((v) => Boolean(v.options) !== Boolean(v.options_endpoint), {
    message: 'options OU options_endpoint, exactement un des deux',
  })

export const askNumberPayload = z
  .object({
    question: z.string().min(1),
    unit: z.string().optional(),
    min: z.number().optional(),
    max: z.number().optional(),
    step: z.number().positive().optional(),
    money: z.object({ currency: isoCurrencySchema }).optional(),
  })
  .strict()

export const askDatePayload = z
  .object({ question: z.string().min(1), min: isoDateSchema.optional(), max: isoDateSchema.optional() })
  .strict()

export const askDateRangePayload = z
  .object({
    question: z.string().min(1),
    min: isoDateSchema.optional(),
    max: isoDateSchema.optional(),
    max_span_days: z.number().int().positive().optional(),
  })
  .strict()

export const askRatingPayload = z
  .object({
    question: z.string().min(1),
    scale: z.union([z.literal(5), z.literal(10)]),
    style: z.enum(['stars', 'numeric']).optional(),
  })
  .strict()

export const askFileUploadPayload = z
  .object({
    question: z.string().min(1),
    attach_to: z.enum(['entreprise', 'projet']),
    projet_id: uuidSchema.optional(),
    accepted_mime: z.array(z.string()).optional(),
    max_size_bytes: z.number().int().positive().optional(),
  })
  .strict()
  .refine((v) => v.attach_to !== 'projet' || Boolean(v.projet_id), {
    message: 'projet_id requis si attach_to=projet',
  })

const showFormFieldSchema = z.discriminatedUnion('type', [
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('text'),
      required: z.boolean().optional(),
      max_length: z.number().int().positive().optional(),
    })
    .strict(),
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('textarea'),
      required: z.boolean().optional(),
      max_length: z.number().int().positive().optional(),
    })
    .strict(),
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('number'),
      required: z.boolean().optional(),
      min: z.number().optional(),
      max: z.number().optional(),
      unit: z.string().optional(),
    })
    .strict(),
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('date'),
      required: z.boolean().optional(),
    })
    .strict(),
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('select'),
      required: z.boolean().optional(),
      options: z.array(z.object({ value: z.string(), label: z.string() })).min(1),
    })
    .strict(),
  z
    .object({
      name: z.string().min(1),
      label: z.string(),
      type: z.literal('checkbox'),
      required: z.boolean().optional(),
    })
    .strict(),
])

export const showFormPayload = z
  .object({ title: z.string().min(1), fields: z.array(showFormFieldSchema).min(1) })
  .strict()

export const showSummaryCardPayload = z
  .object({
    title: z.string().min(1),
    rows: z
      .array(
        z.object({
          label: z.string(),
          value: z.string(),
          source_id: uuidSchema.optional(),
          source_label: z.string().optional(),
        }),
      )
      .min(1),
    ok_label: z.string().optional(),
    edit_label: z.string().optional(),
    cancel_label: z.string().optional(),
  })
  .strict()

// ---- Map tool → schéma (utilisé par useChatBottomSheet pour valider) ----

export const TOOL_PAYLOAD_SCHEMAS = {
  ask_yes_no: askYesNoPayload,
  ask_qcu: askQcuPayload,
  ask_qcm: askQcmPayload,
  ask_select: askSelectPayload,
  ask_number: askNumberPayload,
  ask_date: askDatePayload,
  ask_date_range: askDateRangePayload,
  ask_rating: askRatingPayload,
  ask_file_upload: askFileUploadPayload,
  show_form: showFormPayload,
  show_summary_card: showSummaryCardPayload,
} as const

export type ToolName = keyof typeof TOOL_PAYLOAD_SCHEMAS

export const TOOL_NAMES = Object.keys(TOOL_PAYLOAD_SCHEMAS) as ToolName[]

// ---- Types instructions / responses ----

export interface ToolContext {
  thread_id: string
  message_id: string
}

export type ToolPayload<T extends ToolName> = z.infer<(typeof TOOL_PAYLOAD_SCHEMAS)[T]>

export type ToolInstruction = {
  [K in ToolName]: { tool: K; payload: ToolPayload<K>; context: ToolContext }
}[ToolName]

export interface ToolResponseBase {
  tool: ToolName
  label: string
  metadata?: Record<string, unknown>
}

// Valeurs typées par tool (mirror exact contracts/tool-payloads.md).
export type AskYesNoValue = boolean
export type AskQcuValue = string
export type AskQcmValue = string[]
export type AskSelectValue = string | string[]
export interface AskNumberValue {
  amount: string
  currency?: string
  unit?: string
}
export type AskDateValue = string
export interface AskDateRangeValue {
  start: string
  end: string
}
export type AskRatingValue = number
export interface AskFileUploadValue {
  doc_id: string
  filename: string
  mime: string
  size: number
}
export type ShowFormValue = Record<string, string | number | boolean | null>
export type ShowSummaryCardValue = { action: 'validate' | 'correct' | 'cancel' }

export type ToolResponseValue<T extends ToolName> = T extends 'ask_yes_no'
  ? AskYesNoValue
  : T extends 'ask_qcu'
    ? AskQcuValue
    : T extends 'ask_qcm'
      ? AskQcmValue
      : T extends 'ask_select'
        ? AskSelectValue
        : T extends 'ask_number'
          ? AskNumberValue
          : T extends 'ask_date'
            ? AskDateValue
            : T extends 'ask_date_range'
              ? AskDateRangeValue
              : T extends 'ask_rating'
                ? AskRatingValue
                : T extends 'ask_file_upload'
                  ? AskFileUploadValue
                  : T extends 'show_form'
                    ? ShowFormValue
                    : T extends 'show_summary_card'
                      ? ShowSummaryCardValue
                      : never

export type ToolResponse = {
  [K in ToolName]: { tool: K; value: ToolResponseValue<K>; label: string; metadata?: Record<string, unknown> }
}[ToolName]

// ---- Helpers ----

export function isKnownTool(name: unknown): name is ToolName {
  return typeof name === 'string' && (TOOL_NAMES as string[]).includes(name)
}

export const toolInstructionSchema = z
  .object({
    tool: z.string(),
    payload: z.unknown(),
    context: z.object({ thread_id: uuidSchema, message_id: uuidSchema }).strict(),
  })
  .superRefine((value, ctx) => {
    if (!isKnownTool(value.tool)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: `tool inconnu: ${String(value.tool)}` })
      return
    }
    const schema = TOOL_PAYLOAD_SCHEMAS[value.tool]
    const result = schema.safeParse(value.payload)
    if (!result.success) {
      for (const issue of result.error.issues) {
        ctx.addIssue({ ...issue, path: ['payload', ...(issue.path ?? [])] })
      }
    }
  })

export type ValidatedInstruction = z.infer<typeof toolInstructionSchema>

export { decimalSchema, isoCurrencySchema, isoDateSchema, uuidSchema }
