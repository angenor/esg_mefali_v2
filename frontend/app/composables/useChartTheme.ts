// F40 T012 — useChartTheme : lecture des tokens F36 + prefers-reduced-motion (R5).
import { computed, ref, onMounted, onBeforeUnmount, type ComputedRef } from 'vue'

export interface ChartTheme {
  palette: string[]
  fonts: { family: string; size: number; weight: number }
  tooltip: { bg: string; fg: string; border: string; padding: number }
  animations: { duration: number; easing: string; reducedMotion: boolean }
  grid: { color: string; lineWidth: number }
  axis: { color: string; tick: string }
}

const FALLBACK: ChartTheme = {
  palette: ['#16a34a', '#0ea5e9', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'],
  fonts: { family: 'Inter, system-ui, sans-serif', size: 12, weight: 400 },
  tooltip: { bg: '#171717', fg: '#fafafa', border: '#404040', padding: 8 },
  animations: { duration: 320, easing: 'easeOutQuad', reducedMotion: false },
  grid: { color: '#e5e5e5', lineWidth: 1 },
  axis: { color: '#525252', tick: '#a3a3a3' },
}

function readVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v.length > 0 ? v : fallback
}

function buildTheme(reducedMotion: boolean): ChartTheme {
  if (typeof document === 'undefined') {
    return { ...FALLBACK, animations: { ...FALLBACK.animations, reducedMotion, duration: reducedMotion ? 0 : FALLBACK.animations.duration } }
  }
  const palette = [
    readVar('--color-brand-500', FALLBACK.palette[0]!),
    readVar('--color-info-500', FALLBACK.palette[1]!),
    readVar('--color-warning-500', FALLBACK.palette[2]!),
    readVar('--color-danger-500', FALLBACK.palette[3]!),
    readVar('--color-violet-500', FALLBACK.palette[4]!),
    readVar('--color-teal-500', FALLBACK.palette[5]!),
  ]
  return {
    palette,
    fonts: {
      family: readVar('--font-family-sans', FALLBACK.fonts.family),
      size: 12,
      weight: 400,
    },
    tooltip: {
      bg: readVar('--color-neutral-900', FALLBACK.tooltip.bg),
      fg: readVar('--color-neutral-50', FALLBACK.tooltip.fg),
      border: readVar('--color-neutral-700', FALLBACK.tooltip.border),
      padding: 8,
    },
    animations: {
      duration: reducedMotion ? 0 : 320,
      easing: 'easeOutQuad',
      reducedMotion,
    },
    grid: {
      color: readVar('--color-neutral-200', FALLBACK.grid.color),
      lineWidth: 1,
    },
    axis: {
      color: readVar('--color-neutral-600', FALLBACK.axis.color),
      tick: readVar('--color-neutral-400', FALLBACK.axis.tick),
    },
  }
}

const QUERY = '(prefers-reduced-motion: reduce)'

export function useChartTheme(): ComputedRef<ChartTheme> {
  const reduced = ref(false)
  let mql: MediaQueryList | null = null
  let handler: ((e: MediaQueryListEvent) => void) | null = null

  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    mql = window.matchMedia(QUERY)
    reduced.value = mql.matches
    handler = (e) => { reduced.value = e.matches }
  }

  onMounted(() => {
    if (mql && handler && typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', handler)
    }
  })
  onBeforeUnmount(() => {
    if (mql && handler && typeof mql.removeEventListener === 'function') {
      mql.removeEventListener('change', handler)
    }
  })

  return computed(() => buildTheme(reduced.value))
}
