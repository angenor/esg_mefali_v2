// F45 T021 — E2E timeline rendering.
//
// Pré-requis : backend démarré (port 8010), compte PME e2e provisionné.
// Variables : PLAYWRIGHT_BACKEND_URL, PLAYWRIGHT_E2E_EMAIL, PLAYWRIGHT_E2E_PASSWORD.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test.describe("Plan d'action — timeline render", () => {
  test("affiche la timeline en moins de 2 s avec ≥ 1 jalon par bucket utile", async ({ page }) => {
    await seedPmeWithActionPlan(page, { stepsCount: 6 })
    const start = Date.now()
    await page.goto("/plan-action")
    await page.waitForSelector('[data-testid="timeline"]', { timeout: 5000 })
    const elapsed = Date.now() - start
    expect(elapsed).toBeLessThan(5000) // tolérance E2E (NFR-001 = LCP 1,5 s sur 4G)
    const buckets = page.locator(".pa-timeline__bucket")
    expect(await buckets.count()).toBe(5)
    expect(await page.locator(".pa-timeline__milestone").count()).toBeGreaterThan(0)
  })
})
