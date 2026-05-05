// F46 T061 [US4] — Composable d'édition d'un indicateur via bottom sheet ask_number.
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md (drawer.edit) et
// data-model.md §5.2 (mapping éditable).
//
// Comportement :
//  - row.isEditable=false → toast + emit `open_chat_for_indicateur` (cas non mappé)
//  - snapshot.active → toast bloquant
//  - row.isEditable=true → ouvre <ChatBottomSheet> type ask_number avec valeur+unité
//  - submit OK → store.editIndicateur (PATCH + recompute + bus emit) puis fermeture
//  - submit KO → toast erreur, sheet reste ouvert (gestion par F39 sheet)

import { ref, type Ref } from "vue"
import { useChatBottomSheet } from "~/composables/useChatBottomSheet"
import { useChatEventBus } from "~/composables/useChatEventBus"
import { useScoringStore } from "~/stores/scoring"
import { useEntrepriseStore } from "~/stores/entreprise"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"
import type { PillarRowVM } from "~/types/scoring"

export interface UseIndicateurEditApi {
  isOpen: Ref<boolean>
  openFor(row: PillarRowVM, refCode: string): Promise<void>
  submit(newValue: unknown, row: PillarRowVM, refCode: string): Promise<void>
  cancel(): void
}

export function useIndicateurEdit(): UseIndicateurEditApi {
  const sheet = useChatBottomSheet()
  const bus = useChatEventBus()
  const store = useScoringStore()
  const entreprise = useEntrepriseStore()
  const toast = useToast()
  const { t } = useT()

  const isOpen = ref<boolean>(false)
  const currentRow = ref<PillarRowVM | null>(null)
  const currentRef = ref<string>("")

  async function openFor(row: PillarRowVM, refCode: string): Promise<void> {
    if (store.isSnapshot) {
      toast.push({
        severity: "warning",
        message: t("scoring.snapshot.cannotEdit"),
        duration: 4000,
      })
      return
    }
    if (!row.isEditable) {
      toast.push({
        severity: "info",
        message: t("scoring.errors.notEditableHere"),
        duration: 4000,
      })
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "indicateur",
        entityId: row.indicateurId,
        fieldsUpdated: [row.indicateurCode],
        source: "manual",
        ts: new Date().toISOString(),
      })
      // F41 écoute `open_chat_for_indicateur` via window event (hors EventBus typé).
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("open_chat_for_indicateur", {
            detail: {
              indicateur_code: row.indicateurCode,
              referentiel_code: refCode,
              source: "scoring_page",
            },
          }),
        )
      }
      return
    }
    currentRow.value = row
    currentRef.value = refCode
    isOpen.value = true
    const numericValue =
      typeof row.rawValue === "number" ? row.rawValue : null
    await sheet.open({
      tool: "ask_number",
      context: {
        message_id: `scoring-edit-${row.indicateurId}`,
        thread_id: "",
      },
      payload: {
        question: t("scoring.edit.title"),
        unit: row.weight !== null ? "" : undefined,
        ...(numericValue !== null ? { default: numericValue } : {}),
      },
    })
  }

  async function submit(
    newValue: unknown,
    row: PillarRowVM,
    refCode: string,
  ): Promise<void> {
    try {
      await store.editIndicateur(
        {
          indicateurId: row.indicateurId,
          indicateurCode: row.indicateurCode,
          newValue,
          refCode,
        },
        (entreprise.data ?? null) as Record<string, unknown> | null,
      )
      toast.push({
        severity: "success",
        message: t("scoring.edit.success"),
        duration: 3000,
      })
      isOpen.value = false
      currentRow.value = null
      await sheet.close("freetext")
    } catch (err: unknown) {
      const reason = err instanceof Error ? err.message : "edit_failed"
      toast.push({
        severity: "error",
        message: t("scoring.errors.editFailed"),
        duration: 4000,
      })
      void reason
    }
  }

  function cancel(): void {
    isOpen.value = false
    currentRow.value = null
    void sheet.close("cancel")
  }

  return { isOpen, openFor, submit, cancel }
}
