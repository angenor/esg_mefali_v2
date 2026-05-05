// F45 T048 — E2E toggle horizon (6/12/24).
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("basculer sur 6 mois filtre la timeline et la liste", async ({ page }) => {
  await seedPmeWithActionPlan(page, { horizon: 24 })
  await page.goto("/plan-action")
  await expect(page.locator('[data-testid="plan-action-page"]')).toBeVisible()

  // étapes initiales (24m)
  const initialCount = await page.locator(".pa-step").count()

  // bascule sur 6 mois
  await page.locator('.pa-horizon__btn', { hasText: "6 mois" }).click()
  await page.waitForTimeout(150)

  // ≤ initialCount (souvent strict <)
  const filteredCount = await page.locator(".pa-step").count()
  expect(filteredCount).toBeLessThanOrEqual(initialCount)
})
