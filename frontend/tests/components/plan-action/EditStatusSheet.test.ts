// F45 T031 — Tests EditStatusSheet.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EditStatusSheet from "~/components/plan-action/EditStatusSheet.vue"
import type { ActionStep } from "~/types/actionPlan"

function step(o: Partial<ActionStep> = {}): ActionStep {
  return {
    id: "s",
    plan_id: "p",
    title: "t",
    description: null,
    category: "esg",
    priority: "moyenne",
    horizon_at: "2026-08-01",
    status: "todo",
    responsible_user_id: null,
    indicateur_id: null,
    source_id: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...o,
  }
}

describe("EditStatusSheet", () => {
  it("rend les champs pré-remplis quand open=true", async () => {
    const w = mount(EditStatusSheet, {
      props: { open: true, step: step({ status: "doing" }), responsibleOptions: [] },
      attachTo: document.body,
    })
    await w.vm.$nextTick()
    const radios = document.querySelectorAll<HTMLInputElement>('input[type=radio][name=status]')
    const checked = Array.from(radios).find((r) => r.checked)
    expect(checked?.value).toBe("doing")
    w.unmount()
  })

  it("submit désactivé si rien n'a changé", async () => {
    const w = mount(EditStatusSheet, {
      props: { open: true, step: step({ status: "todo" }), responsibleOptions: [] },
      attachTo: document.body,
    })
    await w.vm.$nextTick()
    const submit = Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find((b) =>
      b.textContent?.includes("Enregistrer"),
    )
    expect(submit?.disabled).toBe(true)
    w.unmount()
  })

  it("submit émet payload minimal après changement", async () => {
    const w = mount(EditStatusSheet, {
      props: { open: true, step: step({ status: "todo" }), responsibleOptions: [] },
      attachTo: document.body,
    })
    await w.vm.$nextTick()
    const radios = document.querySelectorAll<HTMLInputElement>('input[type=radio][name=status]')
    const doing = Array.from(radios).find((r) => r.value === "doing")!
    doing.checked = true
    doing.dispatchEvent(new Event("change", { bubbles: true }))
    await w.vm.$nextTick()
    const submit = Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find((b) =>
      b.textContent?.includes("Enregistrer"),
    )!
    submit.click()
    await w.vm.$nextTick()
    expect(w.emitted("submit")?.[0]).toEqual([{ status: "doing" }])
    w.unmount()
  })
})
