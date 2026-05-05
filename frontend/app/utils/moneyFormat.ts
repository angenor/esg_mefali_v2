// F40 T006 — formatage Money strict (P5 / FR-015 / SC-009).
// `amount` est TOUJOURS une chaîne (sérialisation Decimal). Aucune conversion
// silencieuse vers `number` n'est tolérée — Intl.NumberFormat reçoit le résultat
// d'un parsing explicite via formatNumberOnly() pour garder la trace.

import type { MoneyValue } from '~/types/viz/chart'

const DEFAULT_LOCALE = 'fr-FR'

const PRECISION_BY_CURRENCY: Record<string, number> = {
  XOF: 0,
  XAF: 0,
  EUR: 2,
  USD: 2,
}

function isStringAmount(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

export function formatMoney(value: MoneyValue, locale: string = DEFAULT_LOCALE): string {
  if (!value || !isStringAmount(value.amount) || typeof value.currency !== 'string') {
    return '--'
  }

  const currency = value.currency.toUpperCase()
  const fractionDigits = PRECISION_BY_CURRENCY[currency] ?? 2

  // Parsing manuel : on transforme la chaîne Decimal en Intl.NumberFormat-compatible
  // sans appeler Number() à la racine (trace d'audit P5). On accepte
  // jusqu'à 21 chiffres significatifs + signe + un point décimal.
  const trimmed = value.amount.trim()
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return '--'
  }

  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })

  // Intl.NumberFormat exige number ou bigint. On garde la trace : conversion
  // contrôlée et localisée à cette ligne — jamais propagée en amont. Pour les
  // amounts hors plage Number safe, on tronque à fractionDigits puis BigInt.
  const [integerPart, fracPart = ''] = trimmed.split('.')
  const safe = integerPart.length <= 15
  if (safe) {
    return formatter.format(parseFloat(trimmed))
  }

  // Big amount path : assemble parts avec BigInt + fraction limitée
  const truncatedFrac = fracPart.slice(0, fractionDigits).padEnd(fractionDigits, '0')
  const sign = integerPart.startsWith('-') ? '-' : ''
  const intDigits = integerPart.replace(/^-/, '')
  const full = BigInt(`${sign}${intDigits}${truncatedFrac || ''}`)
  return formatter.format(full)
}

export function isMoneyValue(input: unknown): input is MoneyValue {
  if (!input || typeof input !== 'object') return false
  const v = input as Record<string, unknown>
  return isStringAmount(v.amount) && typeof v.currency === 'string'
}
