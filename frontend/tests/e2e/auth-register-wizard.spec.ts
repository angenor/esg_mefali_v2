// F42 T039 — E2E wizard register (Playwright)
// Note : ce fichier suppose que @playwright/test est installé. À exécuter via
// `pnpm playwright test` une fois Playwright wired (post-MVP polish).
//
// Scenario :
// 1. Naviguer sur /register
// 2. Remplir step 1 (email + password ; password faible doit bloquer)
// 3. Remplir step 2 (raison sociale + secteur)
// 4. Cocher CGU + RGPD au step 3, soumettre
// 5. Vérifier la redirection /onboarding/welcome
// 6. Naviguer en arrière depuis step 2 doit préserver le draft step 1

import { test, expect } from "@playwright/test"

test.describe("F42 — Register wizard", () => {
  test("password faible bloque le step 1", async ({ page }) => {
    await page.goto("/register")
    await page.fill("#r-email", "test@example.com")
    await page.fill("#r-pwd", "abc")
    await page.fill("#r-pwd2", "abc")
    const next = page.locator('[data-testid="step-identifiants"] button[type="submit"]')
    await expect(next).toBeDisabled()
  })

  test("flow complet → /onboarding/welcome", async ({ page }) => {
    const email = `test_${Date.now()}@example.com`
    await page.goto("/register")

    // Step 1
    await page.fill("#r-email", email)
    await page.fill("#r-pwd", "Mefali2026!Vert")
    await page.fill("#r-pwd2", "Mefali2026!Vert")
    await page.locator('[data-testid="step-identifiants"] button[type="submit"]').click()

    // Step 2
    await page.fill("#r-rs", "PME Test")
    await page.fill("#r-sect", "Agro")
    await page.locator('[data-testid="step-entreprise"] li').first().click()
    await page.locator('[data-testid="step-entreprise"] button[type="submit"]').click()

    // Step 3
    await page.locator('[data-testid="step-consentements"] input[type=checkbox]').nth(0).check()
    await page.locator('[data-testid="step-consentements"] input[type=checkbox]').nth(1).check()
    await page.locator('[data-testid="step-consentements"] button[type="submit"]').click()

    await expect(page).toHaveURL(/\/onboarding\/welcome/)
  })

  test("retour préserve le draft", async ({ page }) => {
    await page.goto("/register")
    await page.fill("#r-email", "draft@example.com")
    await page.fill("#r-pwd", "Mefali2026!Vert")
    await page.fill("#r-pwd2", "Mefali2026!Vert")
    await page.locator('[data-testid="step-identifiants"] button[type="submit"]').click()

    await page.locator('[data-testid="step-entreprise"] button[type="button"]').click()
    await expect(page.locator("#r-email")).toHaveValue("draft@example.com")
  })
})
