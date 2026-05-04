// F46 T086 [US8] — E2E snapshot : sortie du mode.
import { test, expect } from "@playwright/test"

test.describe("Scoring — snapshot exit (US8)", () => {
  test("désactiver toggle → bandeau disparaît, boutons réactivés", async ({
    page,
    request,
  }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })
    await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })

    await page.goto("/scoring/BOAD")
    await expect(
      page.locator('[data-testid="score-overview-score"]'),
    ).toBeVisible({ timeout: 5000 })

    await page.locator('[data-testid="snapshot-switch"]').check()
    await expect(page.locator('[data-testid="snapshot-banner"]')).toBeVisible()

    await page.locator('[data-testid="snapshot-switch"]').uncheck()
    await expect(
      page.locator('[data-testid="snapshot-banner"]'),
    ).toHaveCount(0)
    await expect(page.locator('[data-testid="recalc-button"]')).toBeEnabled()
  })
})
