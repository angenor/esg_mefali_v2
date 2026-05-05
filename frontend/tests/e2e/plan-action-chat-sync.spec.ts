// F45 T060 — E2E synchronisation chat ↔ plan-action via EventBus.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("entity_updated{action_step} émis sur le bus → re-fetch ciblé", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")

  // Attendre rendu plan
  await expect(page.locator(".pa-step").first()).toBeVisible()

  // Récupérer l'id de la première étape
  const stepId = await page.evaluate(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any
    const piniaState = w.__PINIA_STATE__ ?? null
    void piniaState
    // fallback : extraire depuis le store via window.__chatBus n'existe pas pour le state
    const cb = document.querySelector('.pa-step input[type="checkbox"]')
    return cb?.getAttribute("aria-label") ?? null
  })
  void stepId

  // Compter les requêtes vers /me/action-plan
  let fetches = 0
  page.on("response", (r) => {
    if (/\/me\/action-plan(\?|$)/.test(r.url()) && r.request().method() === "GET") fetches++
  })

  // Émettre l'event via le bus exposé
  await page.evaluate(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const bus = (window as any).__chatBus
    if (!bus) throw new Error("__chatBus not exposed")
    bus.emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_step",
      entityId: "00000000-0000-0000-0000-000000000000",
      source: "llm",
      ts: new Date().toISOString(),
    })
  })

  // Au moins un fetch déclenché
  await page.waitForTimeout(500)
  expect(fetches).toBeGreaterThanOrEqual(1)
})
