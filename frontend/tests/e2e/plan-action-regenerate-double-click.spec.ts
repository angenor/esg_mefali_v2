// F45 T043 — E2E anti double-clic régénération.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("double-clic Confirmer ne déclenche qu'un seul POST", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")

  let postCount = 0
  await page.route(/\/me\/action-plan\/generate/, async (route) => {
    postCount++
    await new Promise((r) => setTimeout(r, 1000))
    const json = await page.evaluate(() =>
      fetch("/me/action-plan").then((r) => r.json()).catch(() => ({})),
    )
    await route.fulfill({
      status: 200,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(json ?? {}),
    })
  })

  await page.click('[data-testid="pa-regenerate-cta"]')
  const dialog = page.locator('[role="dialog"]')
  const confirm = dialog.locator(".pa-regen__confirm")
  await confirm.click()
  await confirm.click({ force: true }).catch(() => {})
  await page.waitForTimeout(1500)
  expect(postCount).toBe(1)
})
