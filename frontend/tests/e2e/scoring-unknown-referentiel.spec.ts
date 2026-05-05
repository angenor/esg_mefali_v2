// F46 T039 [US2] — E2E ouverture d'un référentiel inconnu → toast + redirect.
import { test, expect } from "@playwright/test"

test.describe("Scoring — référentiel inconnu (US2)", () => {
  test("/scoring/UNKNOWN_CODE → toast + redirect /scoring", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    await page.goto("/scoring/UNKNOWN_CODE")

    // Toast d'erreur.
    await expect(page.getByText(/référentiel inconnu/i)).toBeVisible({
      timeout: 5000,
    })
    // Redirect (path différent de /scoring/UNKNOWN_CODE).
    await page.waitForURL((url) => !url.pathname.includes("UNKNOWN_CODE"), {
      timeout: 5000,
    })
  })
})
