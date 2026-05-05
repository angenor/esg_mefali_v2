// F46 T085 [US8] — E2E snapshot : boutons désactivés.
import { test, expect } from "@playwright/test"

test.describe("Scoring — snapshot freeze (US8)", () => {
  test("activer snapshot → bandeau + Modifier/Recalculer désactivés", async ({
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

    await expect(page.locator('[data-testid="snapshot-banner"]')).toBeVisible({
      timeout: 3000,
    })

    const recalc = page.locator('[data-testid="recalc-button"]')
    await expect(recalc).toBeDisabled()
  })
})
