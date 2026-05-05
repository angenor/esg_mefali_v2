// F46 T026 [US1] — E2E empty state /scoring/BOAD pour un compte sans calcul.
import { test, expect } from "@playwright/test"

test.describe("Scoring — empty no calculation (US1)", () => {
  test("compte sans calcul → /scoring/BOAD montre l'empty state, CTA déclenche un recalcul", async ({
    page,
  }) => {
    // Authentification PME (utilisateur sans calcul ESG initial).
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-empty@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    await page.goto("/scoring/BOAD")

    const empty = page.locator('[data-testid="scoring-empty-no-calc"]')
    await expect(empty).toBeVisible()
    await expect(empty).toContainText(/diagnostic/i)

    const cta = page.locator('[data-testid="scoring-empty-no-calc-cta"]')
    await expect(cta).toBeEnabled()
    await cta.click()

    // Spinner ou bouton désactivé pendant le recalcul (anti double-clic).
    await expect(cta).toBeDisabled({ timeout: 1000 })

    // Score visible une fois le recalcul terminé.
    await expect(
      page.locator('[data-testid="score-overview-score"]'),
    ).toBeVisible({ timeout: 15000 })
  })
})
