// F49 T018 — Composable d'URL signée pour aperçu PDF inline.
//
// INV-5 (data-model.md) : aucune URL persistée au-delà de `expires_at`.

import { computed, ref, watchEffect } from "vue"
import { useReportsStore } from "~/stores/reports"

interface UseSignedPdfUrlReturn {
  url: import("vue").ComputedRef<string | null>
  isExpired: import("vue").ComputedRef<boolean>
  loading: import("vue").Ref<boolean>
  error: import("vue").Ref<string | null>
  refresh: () => Promise<void>
}

export function useSignedPdfUrl(
  rapportId: import("vue").Ref<string | null> | string | null,
): UseSignedPdfUrlReturn {
  const store = useReportsStore()
  const loading = ref(false)
  const error = ref<string | null>(null)
  const expiresAtMs = ref<number | null>(null)
  const internalUrl = ref<string | null>(null)
  const now = ref(Date.now())

  let tickerId: ReturnType<typeof setInterval> | null = null
  if (typeof window !== "undefined") {
    tickerId = setInterval(() => {
      now.value = Date.now()
    }, 5_000)
  }

  function getId(): string | null {
    if (typeof rapportId === "string") return rapportId
    return rapportId?.value ?? null
  }

  async function refresh(): Promise<void> {
    const id = getId()
    if (!id) {
      internalUrl.value = null
      expiresAtMs.value = null
      return
    }
    loading.value = true
    error.value = null
    try {
      const fresh = await store.loadPreviewUrl(id)
      internalUrl.value = fresh.url
      expiresAtMs.value = new Date(fresh.expires_at).getTime()
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : "reports.errors.preview_failed"
      internalUrl.value = null
      expiresAtMs.value = null
    } finally {
      loading.value = false
    }
  }

  watchEffect(() => {
    const id = getId()
    if (id) void refresh()
  })

  const isExpired = computed(() => {
    if (!expiresAtMs.value) return true
    return now.value >= expiresAtMs.value
  })

  const url = computed(() => {
    if (!internalUrl.value) return null
    if (isExpired.value) return null
    return internalUrl.value
  })

  if (typeof window !== "undefined") {
    // Cleanup du ticker à la disposition du scope effet ; les composables
    // Pinia/Vue gèrent le scope automatiquement, mais on protège tout de même.
    import("vue")
      .then((vue) => vue.onScopeDispose?.(() => {
        if (tickerId) clearInterval(tickerId)
      }))
      .catch(() => {})
  }

  return { url, isExpired, loading, error, refresh }
}
