// F51 T011 — Util `formatMoney` & `convertMoney` pour Money typé (P5).
//
// Toutes les valeurs Money portent {amount: string Decimal, currency}. Aucune
// arithmétique en Number ; conversion XOF↔EUR via parité figée 655.957
// (UEMOA, sourcée constitution P5).

import Decimal from "decimal.js"
import type { Currency, Money } from "~/types/matching"

const FCFA_PER_EUR = new Decimal("655.957")
const PRECISION_BY_CURRENCY: Record<Currency, number> = { XOF: 0, EUR: 2 }

export function formatMoney(money: Money, locale = "fr-FR"): string {
  const precision = PRECISION_BY_CURRENCY[money.currency] ?? 2
  const formatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: money.currency,
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })
  const num = Number.parseFloat(money.amount)
  if (Number.isNaN(num)) return ""
  return formatter.format(num)
}

export function convertMoney(money: Money, target: Currency): Money {
  if (money.currency === target) return money
  const amount = new Decimal(money.amount)
  let converted: Decimal
  if (money.currency === "XOF" && target === "EUR") {
    converted = amount.dividedBy(FCFA_PER_EUR)
  } else if (money.currency === "EUR" && target === "XOF") {
    converted = amount.times(FCFA_PER_EUR)
  } else {
    throw new Error(`unsupported_conversion_${money.currency}_${target}`)
  }
  const precision = PRECISION_BY_CURRENCY[target]
  return {
    amount: converted.toFixed(precision),
    currency: target,
  }
}

export function toEur(money: Money): Money {
  return convertMoney(money, "EUR")
}

export function toXof(money: Money): Money {
  return convertMoney(money, "XOF")
}
