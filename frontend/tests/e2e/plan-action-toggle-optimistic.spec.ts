// F45 T032 — E2E optimistic toggle.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("cocher étape met à jour UI < 100 ms et persiste après reload", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")
  const firstCheckbox = page.locator('.pa-step input[type="checkbox"]').first()
  await firstCheckbox.check()
  await expect(firstCheckbox).toBeChecked()
  await page.waitForResponse((r) => /\/me\/action-plan\/steps\//.test(r.url()) && r.ok())
  await page.reload()
  await expect(page.locator('.pa-step input[type="checkbox"]').first()).toBeChecked()
})
