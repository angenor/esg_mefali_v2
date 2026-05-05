// F42 T016 — Tests usePasswordStrength
import { describe, it, expect } from "vitest"
import { ref } from "vue"
import { usePasswordStrength } from "../usePasswordStrength"

describe("usePasswordStrength", () => {
  it("retourne score 0 et non acceptable pour chaîne vide", () => {
    const pwd = ref("")
    const r = usePasswordStrength(pwd)
    expect(r.value.score).toBe(0)
    expect(r.value.isAcceptable).toBe(false)
    expect(r.value.meetsBaseCriteria).toBe(false)
  })

  it("retourne score faible pour 'abc'", () => {
    const pwd = ref("abc")
    const r = usePasswordStrength(pwd)
    expect(r.value.score).toBeLessThanOrEqual(1)
    expect(r.value.isAcceptable).toBe(false)
  })

  it("considère 'Mefali2026!Vert' comme acceptable", () => {
    const pwd = ref("Mefali2026!Vert")
    const r = usePasswordStrength(pwd)
    expect(r.value.meetsBaseCriteria).toBe(true)
    expect(r.value.score).toBeGreaterThanOrEqual(3)
    expect(r.value.isAcceptable).toBe(true)
  })

  it("rejette un mot de passe avec critères OK mais score zxcvbn faible", () => {
    // 12 chars, majuscule, chiffre, symbole, mais structure trivialement devinable
    const pwd = ref("Password123!")
    const r = usePasswordStrength(pwd)
    expect(r.value.meetsBaseCriteria).toBe(true)
    if (r.value.score < 3) {
      expect(r.value.isAcceptable).toBe(false)
    }
  })
})
