// F51 — Test du CTA simulateur → /matching.
//
// Verifie que le CTA "Trouver des offres compatibles" construit bien l'URL
// `/matching?montant_max=X&duree_max=Y` a partir des inputs courants
// (PAS des results), pour rester fonctionnel meme si compute a echoue.

import { describe, expect, it } from "vitest"
import { buildMatchingTargetFromInputs } from "~/utils/simulateurNav"

describe("buildMatchingTargetFromInputs", () => {
  it("constructs /matching?montant_max=X&duree_max=Y from current inputs", () => {
    const target = buildMatchingTargetFromInputs({
      montant: { amount: "150000", currency: "EUR" },
      duree_mois: 84,
    })
    expect(target.path).toBe("/matching")
    expect(target.query).toEqual({
      montant_max: "150000",
      duree_max: "84",
    })
  })

  it("uses default-like inputs when compute never succeeded", () => {
    // Defaults du store : 100000 EUR / 60 mois.
    const target = buildMatchingTargetFromInputs({
      montant: { amount: "100000", currency: "EUR" },
      duree_mois: 60,
    })
    expect(target.query.montant_max).toBe("100000")
    expect(target.query.duree_max).toBe("60")
  })

  it("supports XOF currency without losing the amount", () => {
    const target = buildMatchingTargetFromInputs({
      montant: { amount: "65595700", currency: "XOF" },
      duree_mois: 36,
    })
    expect(target.query.montant_max).toBe("65595700")
    expect(target.query.duree_max).toBe("36")
  })

  it("drops montant_max when amount is empty", () => {
    const target = buildMatchingTargetFromInputs({
      montant: { amount: "", currency: "EUR" },
      duree_mois: 60,
    })
    expect("montant_max" in target.query).toBe(false)
    expect(target.query.duree_max).toBe("60")
  })

  it("drops duree_max when duree is invalid", () => {
    const target = buildMatchingTargetFromInputs({
      montant: { amount: "100000", currency: "EUR" },
      duree_mois: 0,
    })
    expect(target.query.montant_max).toBe("100000")
    expect("duree_max" in target.query).toBe(false)
  })
})
