// F44 T007 — Tests adapter pur DashboardSummaryOut → ViewModels.
import { describe, expect, it } from "vitest"
import { mapSummaryToCardViewModels } from "../mapSummaryToCardViewModels"
import type { DashboardSummaryOut } from "~/stores/dashboard"

const tStub = (key: string) => key

const EMPTY_SUMMARY: DashboardSummaryOut = {
  account_id: "acc-1",
  scores: [],
  carbon: [],
  credit_score: null,
  candidatures: { counters_by_statut: {}, total: 0, recent: [] },
  rapports: { total: 0, recent: [] },
  attestations: { active: 0, revoked: 0, recent: [] },
  next_actions: [],
  generated_at: "2026-05-03T08:00:00Z",
}

const FILLED_SUMMARY: DashboardSummaryOut = {
  ...EMPTY_SUMMARY,
  scores: [
    {
      referentiel_code: "GCF",
      referentiel_version: 2,
      score_global: "62.5",
      computed_at: "2026-05-01T10:00:00Z",
      by_axis: { e: 60, s: 65, g: 70 },
      source_count: 4,
    },
  ],
  carbon: [
    {
      year: 2025,
      total_tco2e: "120.4",
      computed_at: "2026-04-22T08:00:00Z",
      trend: [
        { quarter: "2024-Q4", tco2e: "30.1" },
        { quarter: "2025-Q1", tco2e: "29.0" },
      ],
    },
  ],
  credit_score: {
    solvabilite: 70,
    impact_vert: 65,
    combine: 68,
    methodologie_version: 1,
    coherence_warning: true,
    computed_at: "2026-04-30T12:00:00Z",
  },
  candidatures: {
    counters_by_statut: { en_cours: 2 },
    total: 2,
    recent: [
      {
        id: "c1",
        projet_id: "p1",
        offre_id: "o1",
        statut: "en_cours",
        soumission_at: null,
        created_at: "2026-04-15T09:00:00Z",
      },
    ],
  },
  rapports: {
    total: 1,
    recent: [
      {
        id: "r1",
        entity_type: "scoring",
        entity_id: "e1",
        referentiels: ["GCF", "IFC"],
        language: "fr",
        generated_at: "2026-04-25T14:00:00Z",
      },
    ],
  },
  attestations: {
    active: 1,
    revoked: 0,
    recent: [
      {
        id: "att1",
        public_id: "pub-att1",
        generated_at: "2026-04-20T09:00:00Z",
        valid_until: "2027-04-20T00:00:00Z",
        revoked_at: null,
      },
      {
        id: "att2",
        public_id: "pub-att2",
        generated_at: "2025-04-20T09:00:00Z",
        valid_until: "2025-04-20T00:00:00Z", // expirée
        revoked_at: null,
      },
      {
        id: "att3",
        public_id: "pub-att3",
        generated_at: "2026-04-20T09:00:00Z",
        valid_until: "2027-04-20T00:00:00Z",
        revoked_at: "2026-04-21T00:00:00Z", // révoquée
      },
    ],
  },
  next_actions: [
    {
      id: "s1",
      title: "Compléter bilan carbone",
      category: "carbone",
      priority: "moyenne",
      status: "pending",
      horizon_at: "2026-06-15",
    },
    {
      id: "s2",
      title: "Audit gouvernance",
      category: "gouvernance",
      priority: "haute",
      status: "pending",
      horizon_at: "2026-07-01",
    },
    {
      id: "s3",
      title: "Plan diversité",
      category: "social",
      priority: "haute",
      status: "pending",
      horizon_at: "2026-05-30",
    },
    {
      id: "s4",
      title: "Action faite",
      category: "social",
      priority: "haute",
      status: "done",
      horizon_at: "2026-05-15",
    },
  ],
}

const baseOpts = {
  t: tStub,
  hasProjet: false,
  isLoading: false,
  blockErrors: {},
  onRetry: () => {},
  now: new Date("2026-05-03T00:00:00Z"),
}

describe("mapSummaryToCardViewModels", () => {
  it("loading global quand summary=null && isLoading=true", () => {
    const vms = mapSummaryToCardViewModels(null, { ...baseOpts, isLoading: true })
    expect(vms.scoring.kind).toBe("loading")
    expect(vms.carbon.kind).toBe("loading")
    expect(vms.credit.kind).toBe("loading")
    expect(vms.candidatures.kind).toBe("loading")
    expect(vms.rapports.kind).toBe("loading")
    expect(vms.actionPlan.kind).toBe("loading")
  })

  it("compte vierge → empty avec bonnes hrefs", () => {
    const vms = mapSummaryToCardViewModels(EMPTY_SUMMARY, baseOpts)
    expect(vms.scoring.kind).toBe("empty")
    if (vms.scoring.kind === "empty") expect(vms.scoring.cta.href).toBe("/scoring")
    if (vms.carbon.kind === "empty") expect(vms.carbon.cta.href).toBe("/carbone")
    if (vms.credit.kind === "empty") expect(vms.credit.cta.href).toBe("/credit-score")
    if (vms.candidatures.kind === "empty") expect(vms.candidatures.cta.href).toBe("/candidatures")
    if (vms.rapports.kind === "empty") expect(vms.rapports.cta.href).toBe("/rapports")
    if (vms.actionPlan.kind === "empty") expect(vms.actionPlan.cta.href).toBe("/plan-action")
  })

  it("scoring rempli expose byAxis et sourceCount", () => {
    const vms = mapSummaryToCardViewModels(FILLED_SUMMARY, baseOpts)
    expect(vms.scoring.kind).toBe("filled")
    if (vms.scoring.kind === "filled") {
      expect(vms.scoring.data.scoreGlobal).toBe(62.5)
      expect(vms.scoring.data.byAxis).toEqual({ e: 60, s: 65, g: 70 })
      expect(vms.scoring.data.sourceCount).toBe(4)
      expect(vms.scoring.data.href).toBe("/scoring")
    }
  })

  it("credit rempli expose eligibilityBadges dérivés et coherenceWarning", () => {
    const vms = mapSummaryToCardViewModels(FILLED_SUMMARY, baseOpts)
    if (vms.credit.kind === "filled") {
      expect(vms.credit.data.combineScore).toBe(68)
      expect(vms.credit.data.eligibilityBadges).toContain("BOAD")
      expect(vms.credit.data.coherenceWarning).toBe(true)
    }
  })

  it("rapports : filtre attestations expirées et révoquées, max 2", () => {
    const vms = mapSummaryToCardViewModels(FILLED_SUMMARY, baseOpts)
    if (vms.rapports.kind === "filled") {
      expect(vms.rapports.data.activeAttestations).toHaveLength(1)
      expect(vms.rapports.data.activeAttestations[0]?.publicId).toBe("pub-att1")
    }
  })

  it("actionPlan : tri priorité haute d'abord puis horizon ASC, max 3, exclut done", () => {
    const vms = mapSummaryToCardViewModels(FILLED_SUMMARY, baseOpts)
    if (vms.actionPlan.kind === "filled") {
      const ids = vms.actionPlan.data.steps.map((s) => s.id)
      // s3 (haute, 2026-05-30) → s2 (haute, 2026-07-01) → s1 (moyenne, 2026-06-15) ; s4 exclu (done).
      expect(ids).toEqual(["s3", "s2", "s1"])
    }
  })

  it("blockErrors[block] non vide → kind error avec retry", () => {
    let retried: string | null = null
    const vms = mapSummaryToCardViewModels(FILLED_SUMMARY, {
      ...baseOpts,
      blockErrors: { scores: "Erreur réseau" },
      onRetry: (block) => {
        retried = block
      },
    })
    expect(vms.scoring.kind).toBe("error")
    if (vms.scoring.kind === "error") {
      expect(vms.scoring.message).toBe("Erreur réseau")
      vms.scoring.retry()
      expect(retried).toBe("scores")
    }
  })

  it("intermediaires : null si pas de projet, loading sinon", () => {
    const vmsSans = mapSummaryToCardViewModels(EMPTY_SUMMARY, baseOpts)
    expect(vmsSans.intermediaires).toBeNull()
    const vmsAvec = mapSummaryToCardViewModels(EMPTY_SUMMARY, { ...baseOpts, hasProjet: true })
    expect(vmsAvec.intermediaires?.kind).toBe("loading")
  })

  // F44 T039 [US3] — Vérifie pour chaque carte le label CTA et la href cible exacte sur compte vierge.
  it.each([
    ["scoring", "/scoring", "dashboard.cards.scoring.empty_cta"],
    ["carbon", "/carbone", "dashboard.cards.carbon.empty_cta"],
    ["credit", "/credit-score", "dashboard.cards.credit.empty_cta"],
    ["candidatures", "/candidatures", "dashboard.cards.candidatures.empty_cta"],
    ["rapports", "/rapports", "dashboard.cards.rapports.empty_cta"],
    ["actionPlan", "/plan-action", "dashboard.cards.action_plan.empty_cta"],
  ] as const)(
    "compte vierge → carte %s emit empty avec href=%s + label clé i18n %s",
    (cardKey, expectedHref, expectedLabel) => {
      const vms = mapSummaryToCardViewModels(EMPTY_SUMMARY, baseOpts)
      const vm = vms[cardKey]
      expect(vm.kind).toBe("empty")
      if (vm.kind === "empty") {
        expect(vm.cta.href).toBe(expectedHref)
        expect(vm.cta.label).toBe(expectedLabel)
      }
    },
  )

  // F44 T049 [US5] — Filtre attestations actives avec faux Now (révoquée + expirée).
  it("attestations : filtre révoquée et expirée selon `now` injecté", () => {
    const summary: DashboardSummaryOut = {
      ...EMPTY_SUMMARY,
      attestations: {
        active: 2,
        revoked: 1,
        recent: [
          {
            id: "a1",
            public_id: "pub-active",
            generated_at: "2026-01-01T00:00:00Z",
            valid_until: "2026-12-31T23:59:59Z",
            revoked_at: null,
          },
          {
            id: "a2",
            public_id: "pub-expired",
            generated_at: "2025-01-01T00:00:00Z",
            valid_until: "2025-06-01T00:00:00Z",
            revoked_at: null,
          },
          {
            id: "a3",
            public_id: "pub-revoked",
            generated_at: "2026-02-01T00:00:00Z",
            valid_until: "2027-02-01T00:00:00Z",
            revoked_at: "2026-04-15T00:00:00Z",
          },
        ],
      },
      rapports: { total: 1, recent: [{ id: "r0", entity_type: "scoring", entity_id: "x", referentiels: ["GCF"], language: "fr", generated_at: "2026-01-01T00:00:00Z", title: "T", download_href: "/rapports/r0.pdf" }] },
    }
    const vms = mapSummaryToCardViewModels(summary, {
      ...baseOpts,
      now: new Date("2026-06-01T00:00:00Z"),
    })
    if (vms.rapports.kind === "filled") {
      const ids = vms.rapports.data.activeAttestations.map((a) => a.publicId)
      expect(ids).toEqual(["pub-active"])
    }
  })

  it("candidatures : limite à 3 récentes et résout label", () => {
    const summary: DashboardSummaryOut = {
      ...FILLED_SUMMARY,
      candidatures: {
        counters_by_statut: { en_cours: 4 },
        total: 4,
        recent: Array.from({ length: 4 }, (_, i) => ({
          id: `c${i}`,
          projet_id: `pid${i}-aaaaaaaa`,
          offre_id: `oid${i}-bbbbbbbb`,
          statut: "en_cours",
          soumission_at: null,
          created_at: "2026-04-15T09:00:00Z",
          projet_label: `Projet ${i}`,
          offre_label: `Offre ${i}`,
        })),
      },
    }
    const vms = mapSummaryToCardViewModels(summary, baseOpts)
    if (vms.candidatures.kind === "filled") {
      expect(vms.candidatures.data.recent).toHaveLength(3)
      expect(vms.candidatures.data.recent[0]?.projetLabel).toBe("Projet 0")
    }
  })
})
