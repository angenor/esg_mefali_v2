// F47 T026 — Composable useCarbon : orchestre store + EventBus.
//
// Cf. specs/047-empreinte-carbone-ui/contracts/chat-eventbus-sync.md.

import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useCarbonStore } from "~/stores/carbon"
import { useChatEventBus } from "~/composables/useChatEventBus"
import { groupCarbonByScope } from "~/lib/groupCarbonByScope"
import { computeCarbonCoverage } from "~/lib/computeCarbonCoverage"
import type { EventBusEvent } from "~/types/chat"

const DEBOUNCE_MS = 200
const ECHO_GUARD_MS = 500

export function useCarbon() {
  const store = useCarbonStore()
  const bus = useChatEventBus()
  const lastLocalEmissionAt = ref<number>(0)

  const currentFootprint = computed(() => store.currentFootprint)
  const previousYearFootprint = computed(() => store.previousYearFootprint)
  const groupedBreakdown = computed(() => {
    const fp = store.currentFootprint
    if (!fp) return null
    return groupCarbonByScope(fp.breakdown)
  })
  const coverage = computed(() => {
    const grouped = groupedBreakdown.value
    if (!grouped) return null
    return computeCarbonCoverage(grouped)
  })

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  const scheduleRefresh = (year: number) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      void store.loadFootprint(year)
    }, DEBOUNCE_MS)
  }

  const handler = (event: EventBusEvent) => {
    if (event.entityType !== "carbon_footprint" && event.entityType !== "source") {
      return
    }
    // Echo-guard : si la mutation vient de nous (manual + < 500ms), ignorer.
    if (
      event.source === "manual" &&
      Date.now() - lastLocalEmissionAt.value < ECHO_GUARD_MS
    ) {
      return
    }
    if (event.entityType === "source") {
      // La ligne réfèrant cette source sera marquée pour rafraîchissement
      // (responsabilité de FactorSourcePopover via useSourceFetch).
      return
    }
    // entity_updated{carbon_footprint}
    const yearFromFields = event.fieldsUpdated?.find((f) =>
      f.startsWith("year:"),
    )
    const year = yearFromFields
      ? Number(yearFromFields.split(":")[1])
      : store.selectedYear
    store.invalidateIndex()
    if (year === store.selectedYear) {
      scheduleRefresh(year)
    } else {
      void store.loadIndex({ force: true })
    }
  }

  let off: (() => void) | null = null

  onMounted(async () => {
    off = bus.on("entity_updated", handler)
    await store.loadIndex()
    await store.loadFootprint(store.selectedYear)
    // Charge aussi N-1 pour delta (silencieux).
    void store.loadFootprint(store.selectedYear - 1)
  })

  onBeforeUnmount(() => {
    if (off) off()
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  const recompute = async (year: number) => {
    lastLocalEmissionAt.value = Date.now()
    const result = await store.recompute(year)
    if (result) {
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "carbon_footprint",
        entityId: result.id,
        fieldsUpdated: [`year:${year}`, "recompute"],
        source: "manual",
        ts: new Date().toISOString(),
      })
    }
    return result
  }

  const editLine = async (
    year: number,
    payload: Parameters<typeof store.editLine>[1],
  ) => {
    lastLocalEmissionAt.value = Date.now()
    const result = await store.editLine(year, payload)
    if (result) {
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "carbon_footprint",
        entityId: result.id,
        fieldsUpdated: [
          `year:${year}`,
          `edited_line:${result.edited_line_code}`,
        ],
        source: "manual",
        ts: new Date().toISOString(),
      })
    }
    return result
  }

  return {
    selectedYear: computed(() => store.selectedYear),
    setSelectedYear: store.setSelectedYear,
    currentFootprint,
    previousYearFootprint,
    groupedBreakdown,
    coverage,
    index: computed(() => store.index),
    loadingFootprint: computed(() => store.loadingFootprint[store.selectedYear] ?? false),
    loadingRecompute: computed(() => store.loadingRecompute[store.selectedYear] ?? false),
    loadingEditLine: computed(() => store.loadingEditLine[store.selectedYear] ?? false),
    error: computed(() => store.errorByYear[store.selectedYear] ?? null),
    isEmpty: computed(() => store.isEmpty),
    recompute,
    editLine,
    refresh: () => store.loadFootprint(store.selectedYear),
  }
}
