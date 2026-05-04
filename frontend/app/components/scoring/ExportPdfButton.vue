<script setup lang="ts">
// F46 T094 [US9] — Bouton "Exporter PDF" (P2 — dégradé si flag F51 absent).
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §ExportPdfButton.
import { computed, ref } from "vue"
import { scoringApi } from "~/services/api/scoring"
import { useScoringStore } from "~/stores/scoring"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"

interface Props {
  referentielCode: string
  frozenCalculationId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  frozenCalculationId: null,
})

const store = useScoringStore()
const toast = useToast()
const { t } = useT()

const flagEnabled = computed<boolean>(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.()
  const v = cfg?.public?.featureFlags?.f51_pdf_export
  return Boolean(v)
})

const downloading = ref<boolean>(false)
const disabled = computed<boolean>(() => !flagEnabled.value || downloading.value)

async function onClick(): Promise<void> {
  if (disabled.value) return
  if (!store.entityId) return
  downloading.value = true
  try {
    const blob = await scoringApi.exportPdf({
      entity_type: store.entityType,
      entity_id: store.entityId,
      referentiel_code: props.referentielCode,
      score_calculation_id: props.frozenCalculationId ?? null,
    })
    if (typeof window !== "undefined" && blob instanceof Blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `scoring-${props.referentielCode}.pdf`
      a.setAttribute("data-testid", "export-pdf-anchor")
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    }
    toast.push({
      severity: "success",
      message: t("scoring.export.success"),
      duration: 3000,
    })
  } catch {
    toast.push({
      severity: "error",
      message: t("scoring.export.failed"),
      duration: 4000,
    })
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="export-pdf-btn"
    data-testid="export-pdf-button"
    :disabled="disabled"
    :title="
      !flagEnabled ? t('scoring.export.tooltipDisabled') : undefined
    "
    @click="onClick"
  >
    {{ t("scoring.buttons.export") }}
  </button>
</template>

<style scoped>
.export-pdf-btn {
  font-family: inherit;
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 500;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  background: var(--color-surface, #fff);
  cursor: pointer;
  min-height: 36px;
}
.export-pdf-btn:hover:not(:disabled) {
  background: var(--color-neutral-50, #fafafa);
}
.export-pdf-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.export-pdf-btn:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
</style>
