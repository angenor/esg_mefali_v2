// F46 T021 [US1] — Tests ScoreOverview.
// Cas (a-i) cf. specs/046-scoring-esg-ui/tasks.md.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import ScoreOverview from "~/components/scoring/ScoreOverview.vue"
import type { ScoreSummaryVM } from "~/types/scoring"

const STUBS = {
  VizRadarChart: {
    props: ["series", "title", "size"],
    template: '<div class="stub-radar" :data-axes="series.axes.length" />',
  },
  VizBarChart: {
    props: ["series", "title", "size"],
    template: '<div class="stub-bar" :data-axes="series.labels.length" />',
  },
  UiSkeleton: { template: '<div class="stub-skeleton" />' },
  UiBadge: {
    props: ["severity", "variant"],
    template: '<span class="stub-badge"><slot /></span>',
  },
}

function buildSummary(overrides: Partial<ScoreSummaryVM> = {}): ScoreSummaryVM {
  return {
    referentielCode: "BOAD",
    referentielId: "ref-1",
    referentielVersion: 3,
    scoreGlobal: 62,
    scoresByPillar: { E: 60, S: 65, G: 70 },
    coverageRatio: 0.85,
    computedAt: "2026-04-15T10:30:00Z",
    ...overrides,
  }
}

describe("ScoreOverview", () => {
  it("(a) avec 3 axes E/S/G → rend <VizRadarChart>", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary() },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-radar").exists()).toBe(true)
    expect(w.find(".stub-bar").exists()).toBe(false)
  })

  it("(b) avec 7 axes → bascule sur <VizBarChart>", () => {
    const summary = buildSummary({
      scoresByPillar: { E: 60, S: 65, G: 70, P1: 55, P2: 50, P3: 45, P4: 40 },
    })
    const w = mount(ScoreOverview, {
      props: { summary },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-bar").exists()).toBe(true)
    expect(w.find(".stub-radar").exists()).toBe(false)
    expect(w.find(".stub-bar").attributes("data-axes")).toBe("7")
  })

  it("(c) summary=null → affiche <UiSkeleton>", () => {
    const w = mount(ScoreOverview, {
      props: { summary: null },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-skeleton").exists()).toBe(true)
    expect(w.attributes("aria-busy")).toBe("true")
  })

  it("(d) coverage_ratio=0.85 → texte '85'", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary() },
      global: { stubs: STUBS },
    })
    const txt = w.find('[data-testid="score-overview-coverage"]').text()
    expect(txt).toContain("85")
  })

  it("(e) referentiel_version=3 → pastille 'v.3'", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary() },
      global: { stubs: STUBS },
    })
    const v = w.find('[data-testid="score-overview-version"]')
    expect(v.exists()).toBe(true)
    expect(v.text()).toContain("v.3")
  })

  it("(f) computed_at ISO → date FR", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary() },
      global: { stubs: STUBS },
    })
    const txt = w.find('[data-testid="score-overview-date"]').text()
    expect(txt).toMatch(/avril/i)
    expect(txt).toContain("2026")
  })

  it("(g) tableau sr-only listant chaque pilier et son score", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary() },
      global: { stubs: STUBS },
    })
    const table = w.find('[data-testid="score-overview-sr-table"]')
    expect(table.exists()).toBe(true)
    expect(table.classes()).toContain("sr-only")
    const rows = table.findAll("tbody tr")
    expect(rows.length).toBe(3)
    expect(rows[0]!.text()).toContain("Environnement")
    expect(rows[1]!.text()).toContain("Social")
    expect(rows[2]!.text()).toContain("Gouvernance")
  })

  it("(h) isSnapshot=true → bandeau snapshot affiché", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary(), isSnapshot: true },
      global: { stubs: STUBS },
    })
    const banner = w.find('[data-testid="score-overview-snapshot-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text().toLowerCase()).toContain("snapshot")
  })

  it("(i) score null → placeholder '—'", () => {
    const w = mount(ScoreOverview, {
      props: { summary: buildSummary({ scoreGlobal: null }) },
      global: { stubs: STUBS },
    })
    const score = w.find('[data-testid="score-overview-score"]')
    expect(score.text()).toBe("—")
  })
})
