// F42 T040 — E2E tour onboarding (Playwright)
// Suppose un compte fraîchement créé (state=pending). Exécution post-MVP.

import { test, expect } from "@playwright/test"

test.describe("F42 — Onboarding tour", () => {
  test("démarrage automatique au dashboard puis skip", async ({ page }) => {
    // Pré-condition : compte créé via /register, redirigé vers /onboarding/welcome.
    await page.goto("/onboarding/welcome")
    await page.locator("button", { hasText: "Démarrer le tour" }).click()
    // Driver.js inject .driver-popover
    await expect(page.locator(".driver-popover")).toBeVisible()
    await page.locator(".driver-popover-close-btn").click()
    // L'état doit être passé à 'skipped' côté API ; on recharge → tour ne redémarre pas.
    await page.goto("/dashboard")
    await expect(page.locator(".driver-popover")).toHaveCount(0)
  })

  test("relancement manuel via OnboardingTourTrigger", async ({ page }) => {
    await page.goto("/dashboard")
    // Le bouton Trigger devrait être présent dans le menu Aide (post-T035).
    // À adapter selon l'emplacement final.
  })
})
