// F45 T057 — E2E empty state célébration (pas de gaps exploitables).
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("PME avec scoring sans gap → message de célébration", async ({ page }) => {
  await seedPmeWithActionPlan(page, { withScoring: true, withGaps: false })
  await page.goto("/plan-action")

  await expect(page.locator("text=/Bravo/i")).toBeVisible()
  // pas de bouton de régénération visible (plan non chargé)
  await expect(page.locator('[data-testid="pa-regenerate-cta"]')).toHaveCount(0)
})
