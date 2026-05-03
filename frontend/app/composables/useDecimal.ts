// F43 T007 — Wrapper Decimal.js + helpers monétaires (constitution P5).
//
// Toute arithmétique monétaire passe par decimal.js : `Number` est strictement
// interdit côté front. Les valeurs entrent et sortent en `string`.
//
// Le peg XOF↔EUR est figé à `655.957` (convention monétaire UEMOA, déjà sourcé
// côté backend via `Source` verified). USD : pas de conversion live en MVP
// (research R7) — l'UI affiche "≈ –" et n'effectue pas de calcul.

import Decimal from "decimal.js"

export type Currency = "XOF" | "EUR" | "USD"

/** Peg fixe FCFA ↔ EUR. 1 EUR = 655.957 XOF. */
export const PEG_XOF_EUR = "655.957"

const PEG = new Decimal(PEG_XOF_EUR)

function toDecimal(input: string | Decimal): Decimal {
  if (input instanceof Decimal) return input
  if (typeof input !== "string") {
    throw new TypeError("useDecimal: amount must be a string")
  }
  if (!/^-?\d+(\.\d+)?$/.test(input.trim())) {
    throw new RangeError(`useDecimal: invalid decimal "${input}"`)
  }
  return new Decimal(input.trim())
}

export interface UseDecimal {
  D: typeof Decimal
  add(a: string, b: string): string
  multiply(a: string, b: string): string
  format(amount: string, currency: Currency): string
  convertXofEur(amount: string, from: "XOF" | "EUR", to: "XOF" | "EUR"): string
  PEG_XOF_EUR: string
}

export function useDecimal(): UseDecimal {
  function add(a: string, b: string): string {
    return toDecimal(a).plus(toDecimal(b)).toString()
  }

  function multiply(a: string, b: string): string {
    return toDecimal(a).times(toDecimal(b)).toString()
  }

  /**
   * Format montant + devise selon convention FR.
   * - XOF : 0 décimale, suffixe `FCFA`.
   * - EUR : 2 décimales, suffixe `€`.
   * - USD : 2 décimales, suffixe `$`.
   */
  function format(amount: string, currency: Currency): string {
    const d = toDecimal(amount)
    const decimals = currency === "XOF" ? 0 : 2
    const fixed = d.toFixed(decimals)
    // Sépare partie entière / décimale, applique espaces fines pour milliers FR.
    const sign = fixed.startsWith("-") ? "-" : ""
    const unsigned = sign ? fixed.slice(1) : fixed
    const [intPart, fracPart] = unsigned.split(".")
    const grouped = (intPart ?? "0").replace(/\B(?=(\d{3})+(?!\d))/g, " ")
    const num = fracPart != null ? `${grouped},${fracPart}` : grouped
    const suffix = currency === "XOF" ? "FCFA" : currency === "EUR" ? "€" : "$"
    return `${sign}${num} ${suffix}`
  }

  /** Convertit entre XOF et EUR via le peg fixe. Le résultat est sérialisé en string. */
  function convertXofEur(amount: string, from: "XOF" | "EUR", to: "XOF" | "EUR"): string {
    if (from === to) return toDecimal(amount).toString()
    if (from === "EUR" && to === "XOF") {
      return toDecimal(amount).times(PEG).toString()
    }
    // XOF → EUR
    return toDecimal(amount).dividedBy(PEG).toString()
  }

  return {
    D: Decimal,
    add,
    multiply,
    format,
    convertXofEur,
    PEG_XOF_EUR,
  }
}
