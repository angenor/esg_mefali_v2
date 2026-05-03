// F45 T042 — E2E régénération du plan d'action.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("régénérer le plan crée une version v+1", async ({ page }) => {
  await seedPmeWithActionPlan(page, { horizon: 12 })
  await page.goto("/plan-action")
  await expect(page.locator('[data-testid="plan-action-page"]')).toBeVisible()

  await page.click('[data-testid="pa-regenerate-cta"]')
  const dialog = page.locator('[role="dialog"]')
  await expect(dialog).toBeVisible()

  await dialog.locator('input[type="radio"][value="6"]').check()

  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) => /\/me\/action-plan\/generate/.test(r.url()) && r.request().method() === "POST",
    ),
    dialog.locator(".pa-regen__confirm").click(),
  ])
  expect(resp.ok()).toBe(true)
  expect(resp.url()).toContain("horizon=6")

  await expect(dialog).toBeHidden()
})
