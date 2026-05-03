// F44 T011 — Composable d'export de données PME (RGPD art. 20).
//
// Cf. contracts/frontend-components.md C-CMP-2 et research.md R6.
// - Anti double-clic : second appel est no-op.
// - Nom de fichier : `esg-mefali-export-YYYY-MM-DD.json` (Intl `fr-CA`).
// - Bouton réactivable 2 s après download.
import { computed, ref, type ComputedRef } from "vue"
import { useT } from "~/composables/useT"
import { useToast } from "~/composables/useToast"

const COOLDOWN_MS = 2_000

export interface UseDataExport {
  isDownloading: ComputedRef<boolean>
  download: () => Promise<void>
}

function buildFilename(now: Date = new Date()): string {
  // Intl 'fr-CA' produit `YYYY-MM-DD` ISO.
  const ymd = new Intl.DateTimeFormat("fr-CA").format(now)
  return `esg-mefali-export-${ymd}.json`
}

export function useDataExport(): UseDataExport {
  const downloading = ref(false)
  const cooldown = ref(false)
  const { t } = useT()
  const toast = useToast()

  async function download(): Promise<void> {
    if (downloading.value || cooldown.value) return
    downloading.value = true
    const apiBase =
      (globalThis.useRuntimeConfig?.() as { public?: { apiBase?: string } })?.public?.apiBase ?? ""
    const url = `${apiBase}/me/data/export`
    const fetchFn = globalThis.$fetch as
      | (<T>(u: string, o?: Record<string, unknown>) => Promise<T>)
      | undefined
    try {
      if (!fetchFn) throw new Error("$fetch unavailable")
      const data = await fetchFn<unknown>(url, { credentials: "include" })
      const payload = JSON.stringify(data)
      const blob = new Blob([payload], { type: "application/json" })
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = objectUrl
      a.download = buildFilename()
      a.style.display = "none"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(objectUrl)
      toast.push({ severity: "success", message: t("dashboard.export.toast_started") })
    } catch (_err) {
      toast.push({ severity: "error", message: t("dashboard.export.toast_error") })
    } finally {
      downloading.value = false
      cooldown.value = true
      setTimeout(() => {
        cooldown.value = false
      }, COOLDOWN_MS)
    }
  }

  return {
    isDownloading: computed(() => downloading.value || cooldown.value),
    download,
  }
}
