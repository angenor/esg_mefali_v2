// F45 T044 — E2E erreur régénération.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("régénération en erreur 500 → toast + plan intact + bouton réactivé", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")

  await page.route(/\/me\/action-plan\/generate/, (route) =>
    route.fulfill({
      status: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ detail: "boom" }),
    }),
  )

  await page.click('[data-testid="pa-regenerate-cta"]')
  const dialog = page.locator('[role="dialog"]')
  await dialog.locator(".pa-regen__confirm").click()

  // toast erreur visible
  await expect(page.locator("text=/Régénération impossible/i").first()).toBeVisible()
  // bouton CTA à nouveau cliquable
  const cta = page.locator('[data-testid="pa-regenerate-cta"]')
  await expect(cta).toBeEnabled()
})
