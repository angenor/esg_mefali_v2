// F52 US6 — Tests Vitest de la vue MiniChatView.
// Vérifie que la saisie est déléguée à un bottom-sheet (P10) et non inline.
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import MiniChatView from "../views/MiniChatView.vue"

describe("MiniChatView.vue", () => {
  it("rend la bulle d'accueil read-only", () => {
    const wrapper = mount(MiniChatView, {
      attachTo: document.body,
    })
    const assistantBubbles = wrapper.findAll('[data-testid="chat-bubble-assistant"]')
    expect(assistantBubbles.length).toBeGreaterThanOrEqual(1)
    expect(assistantBubbles[0].text()).toContain("Bienvenue")
    wrapper.unmount()
  })

  it("ouvre le bottom-sheet via 'Répondre librement' (P10)", async () => {
    const wrapper = mount(MiniChatView, {
      attachTo: document.body,
    })
    expect(document.querySelector('[data-testid="chat-sheet"]')).toBeNull()
    await wrapper.find('[data-testid="chat-open-sheet"]').trigger("click")
    expect(document.querySelector('[data-testid="chat-sheet"]')).not.toBeNull()
    wrapper.unmount()
  })

  it("ajoute la bulle utilisateur après envoi via le bottom-sheet", async () => {
    const wrapper = mount(MiniChatView, {
      attachTo: document.body,
    })
    await wrapper.find('[data-testid="chat-open-sheet"]').trigger("click")
    const textarea = document.querySelector(
      '[data-testid="chat-input"]'
    ) as HTMLTextAreaElement | null
    expect(textarea).not.toBeNull()
    if (textarea) {
      textarea.value = "Quelles sont mes deadlines ?"
      textarea.dispatchEvent(new Event("input", { bubbles: true }))
    }
    const submit = document.querySelector(
      '[data-testid="chat-submit"]'
    ) as HTMLButtonElement | null
    submit?.click()
    await wrapper.vm.$nextTick()
    const userBubbles = wrapper.findAll('[data-testid="chat-bubble-user"]')
    expect(userBubbles.length).toBe(1)
    expect(userBubbles[0].text()).toContain("deadlines")
    wrapper.unmount()
  })

  it("ne rend aucune saisie inline dans une bulle", () => {
    const wrapper = mount(MiniChatView, {
      attachTo: document.body,
    })
    const inlineInputs = wrapper.findAll(
      '[data-testid^="chat-bubble-"] input, [data-testid^="chat-bubble-"] textarea'
    )
    expect(inlineInputs.length).toBe(0)
    wrapper.unmount()
  })
})
