// F47 T061 [US4] — Composable useCarbonHistory : dérive 4 séries (total, scope1/2/3)
// à partir de l'index store (lecture seule, max 5 ans).
//
// Cf. specs/047-empreinte-carbone-ui/spec.md US4 et data-model.md §3.

import { computed, ref, watchEffect, type ComputedRef, type Ref } from "vue"
import Decimal from "decimal.js"
import { useCarbonStore } from "~/stores/carbon"
import type { CarbonFootprint, Scope } from "~/types/carbon"

export interface CarbonHistoryPoint {
  year: number
  value: number | null
}

export interface CarbonHistorySeries {
  key: "total" | "scope1" | "scope2" | "scope3"
  label: string
  points: CarbonHistoryPoint[]
}

export interface UseCarbonHistoryApi {
  series: ComputedRef<CarbonHistorySeries[]>
  loading: Ref<boolean>
  error: Ref<string | null>
  load(force?: boolean): Promise<void>
}

const MAX_YEARS = 5

function tco2e(kg: string | undefined): number | null {
  if (kg === undefined || kg === null) return null
  try {
    return Number(new Decimal(kg).dividedBy(1000).toFixed(3))
  } catch {
    return null
  }
}

function totalTco2e(fp: CarbonFootprint | null | undefined): number | null {
  if (!fp) return null
  try {
    return Number(new Decimal(fp.total_tco2e).toFixed(3))
  } catch {
    return null
  }
}

export function useCarbonHistory(): UseCarbonHistoryApi {
  const store = useCarbonStore()
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  async function load(force = false): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await store.loadIndex({ force })
      const years = (store.index ?? [])
        .slice(0, MAX_YEARS)
        .map((e) => e.year)
        .sort((a, b) => a - b)

      const missing = years.filter(
        (y) => store.footprints[y] === undefined,
      )
      const results = await Promise.allSettled(
        missing.map((y) => store.loadFootprint(y)),
      )
      results.forEach((r, idx) => {
        if (r.status === "rejected") {
          // eslint-disable-next-line no-console
          console.warn(
            `[useCarbonHistory] échec chargement footprint ${missing[idx]}`,
            r.reason,
          )
        }
      })
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "history_failed"
    } finally {
      loading.value = false
    }
  }

  watchEffect(() => {
    if (store.index !== null && !loading.value) {
      const years = (store.index ?? []).slice(0, MAX_YEARS).map((e) => e.year)
      const missing = years.filter((y) => store.footprints[y] === undefined)
      if (missing.length > 0) {
        void load(false)
      }
    }
  })

  const series = computed<CarbonHistorySeries[]>(() => {
    const years = (store.index ?? [])
      .slice(0, MAX_YEARS)
      .map((e) => e.year)
      .sort((a, b) => a - b)

    if (years.length === 0) return []

    const buildPoints = (
      project: (fp: CarbonFootprint | null) => number | null,
    ): CarbonHistoryPoint[] =>
      years.map((y) => ({ year: y, value: project(store.footprints[y] ?? null) }))

    const scopeProj =
      (s: Scope) =>
      (fp: CarbonFootprint | null): number | null =>
        fp ? tco2e(fp.by_scope_kgco2e[s]) : null

    return [
      {
        key: "total",
        label: "Total",
        points: years.map((y) => {
          const fp = store.footprints[y]
          if (fp === undefined) {
            const idx = (store.index ?? []).find((e) => e.year === y)
            return {
              year: y,
              value: idx ? Number(new Decimal(idx.total_tco2e).toFixed(3)) : null,
            }
          }
          return { year: y, value: totalTco2e(fp) }
        }),
      },
      { key: "scope1", label: "Scope 1", points: buildPoints(scopeProj("1")) },
      { key: "scope2", label: "Scope 2", points: buildPoints(scopeProj("2")) },
      { key: "scope3", label: "Scope 3", points: buildPoints(scopeProj("3")) },
    ]
  })

  return { series, loading, error, load }
}
