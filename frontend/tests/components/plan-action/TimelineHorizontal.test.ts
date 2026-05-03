// F45 T020 — Tests TimelineHorizontal.
import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import TimelineHorizontal from "~/components/plan-action/TimelineHorizontal.vue"
import type { TimelineBucketViewModel } from "~/types/actionPlan"

vi.mock("gsap", () => ({ gsap: { from: vi.fn() }, default: { from: vi.fn() } }))

function bucket(o: Partial<TimelineBucketViewModel>): TimelineBucketViewModel {
  return {
    bucket: o.bucket ?? "lt3m",
    label: o.label ?? "Moins de 3 mois",
    rangeStart: null,
    rangeEnd: null,
    steps: o.steps ?? [],
  }
}

function step(id: string, tone: "danger" | "warning" | "info"): import("~/types/actionPlan").StepCardViewModel {
  return {
    id,
    title: `Étape ${id}`,
    description: null,
    priorityLabel: "P",
    priorityTone: tone,
    horizonAt: "2026-06-01",
    horizonRelative: "Dans 1 mois",
    bucket: "lt3m",
    status: "todo",
    statusLabel: "À faire",
    statusTone: "neutral",
    responsibleUserId: null,
    responsibleAvatarUrl: null,
    responsibleLabel: "—",
    indicateurId: null,
    sourceLink: null,
    isLoading: false,
    error: null,
  }
}

describe("TimelineHorizontal", () => {
  it("rend 5 buckets fournis comme 5 colonnes", () => {
    const buckets: TimelineBucketViewModel[] = [
      bucket({ bucket: "lt3m" }),
      bucket({ bucket: "3to6m" }),
      bucket({ bucket: "6to12m" }),
      bucket({ bucket: "12to24m" }),
      bucket({ bucket: "unscheduled" }),
    ]
    const w = mount(TimelineHorizontal, { props: { buckets, reducedMotion: true } })
    expect(w.findAll(".pa-timeline__bucket")).toHaveLength(5)
  })

  it("colore chaque jalon selon le tone", () => {
    const buckets = [
      bucket({
        bucket: "lt3m",
        steps: [step("a", "danger"), step("b", "warning"), step("c", "info")],
      }),
    ]
    const w = mount(TimelineHorizontal, { props: { buckets, reducedMotion: true } })
    expect(w.find(".pa-tone-danger").exists()).toBe(true)
    expect(w.find(".pa-tone-warning").exists()).toBe(true)
    expect(w.find(".pa-tone-info").exists()).toBe(true)
  })

  it("expose le titre via title (tooltip natif)", () => {
    const buckets = [bucket({ bucket: "lt3m", steps: [step("a", "info")] })]
    const w = mount(TimelineHorizontal, { props: { buckets, reducedMotion: true } })
    expect(w.find(".pa-timeline__dot").attributes("title")).toBe("Étape a")
  })

  it("émet select-step au clic", async () => {
    const buckets = [bucket({ bucket: "lt3m", steps: [step("a", "info")] })]
    const w = mount(TimelineHorizontal, { props: { buckets, reducedMotion: true } })
    await w.find(".pa-timeline__dot").trigger("click")
    expect(w.emitted("select-step")?.[0]).toEqual(["a"])
  })

  it("reducedMotion=true → classe sans animation", () => {
    const w = mount(TimelineHorizontal, { props: { buckets: [], reducedMotion: true } })
    expect(w.classes()).toContain("pa-timeline--no-anim")
  })
})
