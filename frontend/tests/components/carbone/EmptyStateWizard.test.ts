// F47 T072 [US6] — Tests EmptyStateWizard.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import EmptyStateWizard from "~/components/carbone/EmptyStateWizard.vue"

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string, p?: Record<string, unknown>) => (p ? `${k}|${JSON.stringify(p)}` : k) }),
}))

vi.mock("~/services/api/carbon", () => ({
  carbonApi: {
    fetchIndex: vi.fn().mockResolvedValue([]),
    fetchFootprint: vi.fn(),
    recompute: vi.fn(),
    editLine: vi.fn(),
    computeInitial: vi.fn(),
  },
}))

// Stubs UI lourds.
vi.mock("~/components/ui/UiButton.vue", () => ({
  default: {
    template: "<button :disabled='disabled' @click='$emit(`click`, $event)'><slot /></button>",
    props: ["variant", "size", "disabled"],
  },
}))
vi.mock("~/components/ui/UiCard.vue", () => ({
  default: { template: "<div class='ui-card'><slot /></div>" },
}))
vi.mock("~/components/ui/UiInput.vue", () => ({
  default: {
    template: "<input :value='modelValue' @input='$emit(`update:modelValue`, $event.target.value)' />",
    props: ["modelValue", "type", "placeholder"],
  },
}))
vi.mock("~/components/ui/UiNumber.vue", () => ({
  default: {
    template: "<input type='number' :value='modelValue' @input='$emit(`update:modelValue`, Number($event.target.value))' />",
    props: ["modelValue"],
  },
}))
vi.mock("~/components/ui/UiSelect.vue", () => ({
  default: {
    template: "<select :value='modelValue' @change='$emit(`update:modelValue`, $event.target.value)'><option v-for='o in options' :key='o.value' :value='o.value'>{{ o.label }}</option></select>",
    props: ["modelValue", "options"],
  },
}))
vi.mock("~/components/ui/UiProgress.vue", () => ({
  default: { template: "<div class='ui-progress' :data-value='modelValue' />", props: ["modelValue"] },
}))

describe("EmptyStateWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    if (typeof window !== "undefined") window.localStorage.clear()
  })
  afterEach(() => vi.restoreAllMocks())

  it("(a) écran initial : header + 3 cartes + bouton Commencer + bouton Répondre librement", () => {
    const w = mount(EmptyStateWizard, { props: { year: 2026 } })
    expect(w.text()).toContain("carbon.wizard.title")
    const cards = w.findAll(".ui-card")
    expect(cards.length).toBe(3)
    const buttons = w.findAll("button")
    expect(buttons.length).toBeGreaterThanOrEqual(2)
    expect(w.text()).toContain("carbon.wizard.start")
    expect(w.text()).toContain("carbon.wizard.answerFreely")
  })

  it("(b) clic Commencer démarre le wizard (1ère étape visible)", async () => {
    const w = mount(EmptyStateWizard, { props: { year: 2026 } })
    const startBtn = w.findAll("button").find((b) => b.text().includes("carbon.wizard.start"))
    expect(startBtn).toBeTruthy()
    await startBtn!.trigger("click")
    expect(w.find(".ui-progress").exists()).toBe(true)
    expect(w.text()).toContain("carbon.wizard.progress")
  })
})
