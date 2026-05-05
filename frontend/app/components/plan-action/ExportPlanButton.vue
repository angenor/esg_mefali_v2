<script setup lang="ts">
// F45 T071 — Bouton export PDF du plan d'action.
//
// Différé : tant que F51 n'est pas livrée, le bouton reste désactivé sauf si
// le flag `NUXT_PUBLIC_FEATURE_PLAN_EXPORT_PDF=true` est positionné.
import { computed, ref } from "vue"
import { useT } from "~/composables/useT"

interface RuntimeConfigShape {
  public?: { apiBase?: string; featurePlanExportPdf?: string }
}

const { t } = useT()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cfg = (globalThis as any).useRuntimeConfig?.() as RuntimeConfigShape | undefined
const enabled = computed(() => String(cfg?.public?.featurePlanExportPdf ?? "false") === "true")
const apiBase = String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")

const downloading = ref(false)

function fileName(): string {
  const today = new Date().toISOString().slice(0, 10)
  return `plan-action-${today}.pdf`
}

async function onExport(): Promise<void> {
  if (!enabled.value || downloading.value) return
  downloading.value = true
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const fetchFn = (globalThis as any).$fetch as
      | (<T>(u: string, o?: Record<string, unknown>) => Promise<T>)
      | undefined
    if (!fetchFn) throw new Error("$fetch unavailable")
    const blob = await fetchFn<Blob>(`${apiBase}/me/action-plan/export.pdf`, {
      method: "GET",
      credentials: "include",
      responseType: "blob",
    })
    if (typeof window !== "undefined") {
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = fileName()
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    }
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="pa-export"
    :disabled="!enabled || downloading"
    :title="enabled ? undefined : t('planAction.export.soon')"
    :aria-label="enabled ? t('planAction.export.cta') : t('planAction.export.soon')"
    data-testid="pa-export-pdf"
    @click="onExport"
  >
    {{ enabled ? t("planAction.export.cta") : t("planAction.export.soon") }}
  </button>
</template>

<style scoped>
.pa-export {
  border: 1px solid var(--color-border, #e5e7eb);
  background: white;
  padding: 6px 12px;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: var(--font-size-sm);
  min-height: 36px;
}
.pa-export[disabled] {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
