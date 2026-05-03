// F43 T006 — tests vitest useDecimal (P5 Money typé).
import { describe, expect, it } from "vitest"
import Decimal from "decimal.js"
import { useDecimal, PEG_XOF_EUR } from "../useDecimal"

const NNBSP = " " // narrow no-break space — séparateur des milliers FR.

describe("useDecimal", () => {
  const { add, multiply, format, convertXofEur, D } = useDecimal()

  it("expose le peg XOF↔EUR à 655.957", () => {
    expect(PEG_XOF_EUR).toBe("655.957")
  })

  it("add additionne deux chaînes Decimal sans dérive", () => {
    expect(add("0.1", "0.2")).toBe("0.3")
    expect(add("1234567890.123456", "0.000001")).toBe("1234567890.123457")
  })

  it("multiply multiplie deux chaînes Decimal", () => {
    expect(multiply("0.1", "0.2")).toBe("0.02")
    expect(multiply("655.957", "100")).toBe("65595.7")
  })

  it("format XOF : 0 décimale, suffixe FCFA, séparateur fin FR", () => {
    expect(format("1250000", "XOF")).toBe(`1${NNBSP}250${NNBSP}000 FCFA`)
    expect(format("0", "XOF")).toBe("0 FCFA")
  })

  it("format EUR : 2 décimales, virgule, suffixe €", () => {
    expect(format("1905.76", "EUR")).toBe(`1${NNBSP}905,76 €`)
    expect(format("0.5", "EUR")).toBe("0,50 €")
  })

  it("format USD : 2 décimales, virgule, suffixe $", () => {
    expect(format("100", "USD")).toBe("100,00 $")
  })

  it("convertXofEur : XOF → EUR via peg 655.957", () => {
    // 1 250 000 XOF / 655.957 ≈ 1905.61...
    const eur = convertXofEur("1250000", "XOF", "EUR")
    expect(eur.startsWith("1905.61")).toBe(true)
  })

  it("convertXofEur : EUR → XOF via peg 655.957", () => {
    expect(convertXofEur("100", "EUR", "XOF")).toBe("65595.7")
  })

  it("convertXofEur : same currency returns identity", () => {
    expect(convertXofEur("123.45", "EUR", "EUR")).toBe("123.45")
  })

  it("Decimal sortie sérialisable en string (jamais Number)", () => {
    const result = add("1", "2")
    expect(typeof result).toBe("string")
  })

  it("rejette une chaîne non numérique", () => {
    expect(() => add("abc", "1")).toThrow()
  })

  it("export D pointe vers la classe Decimal", () => {
    expect(D).toBe(Decimal)
  })
})
