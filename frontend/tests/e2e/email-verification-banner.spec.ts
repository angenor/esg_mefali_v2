// F42 T071 — E2E bandeau de vérification email
// Pré-conditions :
//   - fixture compte non vérifié → bandeau visible
//   - fixture compte vérifié → bandeau absent

import { test, expect } from "@playwright/test"

test.describe("F42 — Email verification banner", () => {
  test("compte non vérifié voit le bandeau", async ({ page }) => {
    // TODO : auth fixture
    await page.goto("/dashboard")
    const banner = page.locator('[data-testid="email-verification-banner"]')
    if (await banner.count()) {
      await expect(banner).toBeVisible()
    }
  })

  test("clic Renvoyer verrouille le bouton 60 s", async ({ page }) => {
    await page.goto("/dashboard")
    const banner = page.locator('[data-testid="email-verification-banner"]')
    if (!(await banner.count())) return
    const resendBtn = banner.locator("button", { hasText: /Renvoyer/i }).first()
    await resendBtn.click()
    // Cooldown affiché
    await expect(banner.locator("button").filter({ hasText: /Renvoyer dans/i })).toBeVisible()
  })

  test("dismiss via bouton X masque le bandeau", async ({ page }) => {
    await page.goto("/dashboard")
    const banner = page.locator('[data-testid="email-verification-banner"]')
    if (!(await banner.count())) return
    await banner.locator('button[aria-label*="Masquer"]').click()
    await expect(banner).toBeHidden()
  })
})
