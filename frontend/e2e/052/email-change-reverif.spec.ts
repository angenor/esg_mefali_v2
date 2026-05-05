// F52 SC-003 — E2E modification e-mail (re-vérif).
import { test, expect } from '@playwright/test'

const PME_EMAIL = process.env.E2E_PME_EMAIL ?? ''
const PME_PASSWORD = process.env.E2E_PME_PASSWORD ?? ''

test.describe('F52 SC-003 — Email change re-vérif', () => {
  test.skip(!PME_EMAIL || !PME_PASSWORD, 'E2E_PME_EMAIL/PWD non définis')

  test("demande crée un email_pending visible", async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(PME_EMAIL)
    await page.getByLabel(/Mot de passe/i).fill(PME_PASSWORD)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()

    await page.goto('/parametres/profil')
    await page.getByTestId('profile-change-email').click()
    const newEmail = `e2e_${Date.now()}@example.com`
    await page.getByTestId('email-change-new').fill(newEmail)
    await page.getByTestId('email-change-password').fill(PME_PASSWORD)
    await page.getByTestId('email-change-submit').click()
    await page.waitForLoadState('networkidle')

    await expect(page.getByTestId('profile-email-pending')).toContainText(newEmail, {
      timeout: 5000,
    })
  })
})
