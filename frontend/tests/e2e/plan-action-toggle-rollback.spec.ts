// F45 T033 — E2E rollback sur PATCH 500.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("erreur PATCH 500 → UI revient à todo et toast affiché", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.route("**/me/action-plan/steps/**", (route) => route.fulfill({ status: 500 }))
  await page.goto("/plan-action")
  const checkbox = page.locator('.pa-step input[type="checkbox"]').first()
  await checkbox.check()
  await expect.poll(() => checkbox.isChecked()).toBe(false)
  await expect(page.locator('[role="alert"]').first()).toBeVisible()
})
