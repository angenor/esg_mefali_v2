// F47 T053 [US3] — Composable d'édition d'une ligne d'activité carbone.
//
// Ouvre un bottom sheet ask_form (P10), valide localement (source_id obligatoire),
// délègue au store + EventBus. Mode "ajout" si line=null (posteCode requis).
//
// Cf. specs/047-empreinte-carbone-ui/spec.md US3 et contracts/frontend-components.md.

import { ref, type Ref } from "vue"
import { useCarbonStore } from "~/stores/carbon"
import { useChatBottomSheet } from "~/composables/useChatBottomSheet"
import { useChatEventBus } from "~/composables/useChatEventBus"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import type {
  CarbonBreakdownLine,
  CarbonEditLineRequest,
  CarbonEditLineResponse,
} from "~/types/carbon"

export interface OpenDrawerArgs {
  year: number
  line: CarbonBreakdownLine | null
  posteCode: string
}

export interface CarbonSubmitArgs {
  year: number
  posteCode: string
  quantity: string
  unit?: string
  country?: string | null
  sourceId: string | null
}

export interface UseCarbonEditApi {
  isOpen: Ref<boolean>
  isSubmitting: Ref<boolean>
  openDrawer(args: OpenDrawerArgs): Promise<void>
  submit(args: CarbonSubmitArgs): Promise<CarbonEditLineResponse | null>
  cancel(): Promise<void>
}

export function useCarbonEdit(): UseCarbonEditApi {
  const store = useCarbonStore()
  const sheet = useChatBottomSheet()
  const bus = useChatEventBus()
  const toast = useToast()
  const { t } = useT()

  const isOpen = ref<boolean>(false)
  const isSubmitting = ref<boolean>(false)

  async function openDrawer(args: OpenDrawerArgs): Promise<void> {
    if (isOpen.value) return
    isOpen.value = true
    const isAdd = args.line === null
    const title = isAdd
      ? t("carbon.editLine.titleAdd")
      : t("carbon.editLine.title")
    const defaults: Record<string, unknown> = {
      code: args.posteCode,
      quantity: args.line?.quantity ?? "",
      unit: args.line?.unit ?? "",
      source_id: args.line?.source_id ?? "",
      country: "",
    }
    await sheet.open({
      tool: "ask_form",
      context: {
        message_id: `carbon-edit-${args.year}-${args.posteCode}-${Date.now()}`,
        thread_id: "",
      },
      payload: {
        title,
        fields: [
          {
            name: "quantity",
            type: "number",
            label: t("carbon.editLine.quantity"),
            required: true,
            default: defaults.quantity,
          },
          {
            name: "country",
            type: "text",
            label: t("carbon.editLine.country"),
            required: false,
          },
          {
            name: "source_id",
            type: "source_select",
            label: t("carbon.editLine.source"),
            required: true,
            placeholder: t("carbon.editLine.sourcePlaceholder"),
            filter: { statut: "verified" },
          },
        ],
        meta: {
          year: args.year,
          posteCode: args.posteCode,
          mode: isAdd ? "add" : "edit",
        },
      },
    })
  }

  async function submit(args: CarbonSubmitArgs): Promise<CarbonEditLineResponse | null> {
    if (isSubmitting.value) return null
    if (!args.sourceId) {
      toast.push({
        severity: "error",
        message: t("carbon.editLine.sourceRequired"),
        duration: 4000,
      })
      return null
    }
    isSubmitting.value = true
    const payload: CarbonEditLineRequest = {
      code: args.posteCode,
      quantity: String(args.quantity),
      source_id: args.sourceId,
      ...(args.country ? { country: args.country } : {}),
    }
    try {
      const result = await store.editLine(args.year, payload)
      if (!result) {
        return null
      }
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "carbon_footprint",
        entityId: result.id,
        fieldsUpdated: [
          `year:${args.year}`,
          `edited_line:${result.edited_line_code}`,
        ],
        source: "manual",
        ts: new Date().toISOString(),
      })
      toast.push({
        severity: "success",
        message: t("carbon.editLine.success"),
        duration: 3000,
      })
      isOpen.value = false
      await sheet.close("freetext")
      return result
    } catch (err: unknown) {
      const e = err as { status?: number; data?: { error?: string } }
      const code = e?.data?.error
      if (code === "source_not_verified") {
        toast.push({
          severity: "error",
          message: t("carbon.editLine.sourceNotVerified"),
          duration: 5000,
        })
      } else {
        toast.push({
          severity: "error",
          message: t("carbon.editLine.error"),
          duration: 5000,
        })
      }
      return null
    } finally {
      isSubmitting.value = false
    }
  }

  async function cancel(): Promise<void> {
    isOpen.value = false
    await sheet.close("cancel")
  }

  return { isOpen, isSubmitting, openDrawer, submit, cancel }
}
