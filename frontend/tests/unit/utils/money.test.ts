// F51 T010 — Tests formatMoney + convertMoney.

import { describe, it, expect } from "vitest"
import { convertMoney } from "~/utils/money"
import { formatMoney } from "~/utils/moneyFormat"

describe("formatMoney", () => {
  it("formats EUR with 2 decimals (fr-FR)", () => {
    const out = formatMoney({ amount: "150000", currency: "EUR" }, "fr-FR")
    // Le NBSP est différent selon les versions Intl ; on vérifie le contenu sans
    // se soucier du séparateur exact.
    expect(out).toMatch(/150[\s  ]?000,00[\s  ]?€/)
  })

  it("formats XOF without decimals", () => {
    const out = formatMoney({ amount: "98415000", currency: "XOF" }, "fr-FR")
    expect(out).toMatch(/98[\s  ]?415[\s  ]?000/)
    expect(out).toContain("F") // F CFA
  })

  it("returns placeholder '--' on invalid amount", () => {
    expect(formatMoney({ amount: "not-a-number", currency: "EUR" })).toBe("--")
  })
})

describe("convertMoney", () => {
  it("converts EUR → XOF using fixed UEMOA peg 655.957", () => {
    const out = convertMoney({ amount: "100", currency: "EUR" }, "XOF")
    expect(out.currency).toBe("XOF")
    expect(out.amount).toBe("65596") // 100 * 655.957 = 65595.7 → arrondi 0 décimale
  })

  it("converts XOF → EUR using inverse peg", () => {
    const out = convertMoney({ amount: "655957", currency: "XOF" }, "EUR")
    expect(out.currency).toBe("EUR")
    expect(out.amount).toBe("1000.00")
  })

  it("returns the same money if currency matches target", () => {
    const m = { amount: "42", currency: "EUR" as const }
    expect(convertMoney(m, "EUR")).toBe(m)
  })
})
