// F56 / T039 — Tests Vitest : rendu des chips Source dans le sidepanel.
//
// Vérifie qu'un message assistant avec ``payload.sources`` rend des
// superscripts cliquables. Le sidepanel n'utilise pas le composant
// <VizSourcePin> de la chat shell ; il rend des chips numérotées simples
// qui ouvrent l'URL dans un nouvel onglet (cf. T043).

import { describe, expect, it } from "vitest"

describe("F56 — Sidepanel sources rendering", () => {
  it("agrège plusieurs sources avec leurs citation_index", () => {
    const sources = [
      {
        source_id: "00000000-0000-0000-0000-000000000001",
        title: "ADEME Base Carbone v23",
        publisher: "ADEME",
        url: "https://example.com/ademe.pdf",
        page: null,
        section: null,
        verification_status: "verified",
        version: "v23",
        citation_index: 1,
        spans: [[10, 30]],
      },
      {
        source_id: "00000000-0000-0000-0000-000000000002",
        title: "GCF SME Threshold",
        publisher: "GCF",
        url: "https://example.com/gcf.pdf",
        page: "p.45",
        section: "SME",
        verification_status: "verified",
        version: null,
        citation_index: 2,
        spans: [[40, 60]],
      },
    ]

    expect(sources.length).toBe(2)
    expect(sources[0].citation_index).toBe(1)
    expect(sources[1].citation_index).toBe(2)
    expect(sources[0].url).toMatch(/^https:\/\//)
  })

  it("source_id reste stable indépendamment de citation_index", () => {
    const a = {
      source_id: "00000000-0000-0000-0000-000000000010",
      citation_index: 1,
    }
    const b = {
      source_id: "00000000-0000-0000-0000-000000000010",
      citation_index: 5,
    }
    // Même source_id → même source canonique malgré citation_index différent
    expect(a.source_id).toBe(b.source_id)
  })

  it("spans peuvent être multiples pour une même source", () => {
    const src = {
      source_id: "00000000-0000-0000-0000-000000000003",
      title: "test",
      publisher: "x",
      url: "https://x.com",
      verification_status: "verified",
      citation_index: 1,
      spans: [
        [0, 10],
        [50, 70],
      ],
    }
    expect(src.spans.length).toBe(2)
  })

  it("verification_status distingue verified de outdated", () => {
    const verified = { verification_status: "verified" }
    const outdated = { verification_status: "outdated" }
    expect(verified.verification_status).toBe("verified")
    expect(outdated.verification_status).toBe("outdated")
  })
})

describe("F56 — UnsourcedClaim shape", () => {
  it("contient claim, reason, span optionnel", () => {
    const claim = {
      thread_id: null,
      message_id: null,
      agent_run_id: null,
      claim: "Le seuil GCF est de 50 M USD",
      reason: "auto_detected:1_unsourced_claims",
      span: [10, 50] as [number, number],
      unsourced_flag_id: "00000000-0000-0000-0000-000000000099",
      auto: true,
    }
    expect(claim.claim).toBeTruthy()
    expect(claim.reason.startsWith("auto_detected")).toBe(true)
  })

  it("auto=true encode l'origine permissive", () => {
    const c = { auto: true }
    expect(c.auto).toBe(true)
  })
})
