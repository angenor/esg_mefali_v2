// F45 T052 — E2E empty state pas de scoring.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("PME sans scoring → empty state avec CTA /scoring", async ({ page }) => {
  await seedPmeWithActionPlan(page, { withScoring: false })
  await page.goto("/plan-action")

  const cta = page.locator('[data-testid="pa-empty-no-scoring-cta"]')
  await expect(cta).toBeVisible()
  await expect(cta).toHaveAttribute("href", "/scoring")

  await cta.click()
  await page.waitForURL("**/scoring")
})
