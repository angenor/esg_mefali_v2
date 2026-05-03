export interface UseMoneyFormatOptions {
  currency: string // ISO 4217
  locale?: string
  precision?: number
}

export interface UseMoneyFormatApi {
  display: (raw: number | null | undefined) => string
  parse: (input: string) => number | null
}

const DEFAULT_PRECISION: Record<string, number> = {
  XOF: 0,
  EUR: 2,
  USD: 2,
}

export function useMoneyFormat(options: UseMoneyFormatOptions): UseMoneyFormatApi {
  const locale = options.locale ?? 'fr-FR'
  const precision = options.precision ?? DEFAULT_PRECISION[options.currency] ?? 2
  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: options.currency,
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })

  return {
    display(raw) {
      if (raw === null || raw === undefined || Number.isNaN(raw)) return ''
      return formatter.format(raw)
    },
    parse(input) {
      if (typeof input !== 'string' || input.trim() === '') return null
      // Conserve chiffres, signe, séparateurs locaux ; convertit virgule en point.
      const cleaned = input
        .replace(/[\s  ]/g, '')
        .replace(/[^\d,.\-]/g, '')
        .replace(',', '.')
      if (cleaned === '' || cleaned === '-' || cleaned === '.') return null
      const n = Number(cleaned)
      return Number.isFinite(n) ? n : null
    },
  }
}
