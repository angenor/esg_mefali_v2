// F52 SC-005 — E2E suppression compte J+30.
// Hypothèse : E2E_PME_EMAIL/PWD + raison sociale enregistrée = E2E_RAISON_SOCIALE.
import { test, expect } from '@playwright/test'

const PME_EMAIL = process.env.E2E_PME_EMAIL ?? ''
const PME_PASSWORD = process.env.E2E_PME_PASSWORD ?? ''
const RAISON = process.env.E2E_RAISON_SOCIALE ?? ''

test.describe('F52 SC-005 — Suppression compte J+30', () => {
  test.skip(
    !PME_EMAIL || !PME_PASSWORD || !RAISON,
    'E2E_PME_EMAIL/PWD/RAISON_SOCIALE non définis'
  )

  test('demande puis annulation', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(PME_EMAIL)
    await page.getByLabel(/Mot de passe/i).fill(PME_PASSWORD)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()

    await page.goto('/parametres/suppression')
    await page.getByTestId('deletion-open').click()
    await page.getByTestId('deletion-confirmation').fill(RAISON)
    await page.getByTestId('deletion-submit').click()

    await expect(page.getByTestId('deletion-pending')).toBeVisible({ timeout: 5000 })
    await page.getByTestId('deletion-cancel').click()
    await expect(page.getByTestId('deletion-pending')).toBeHidden({ timeout: 5000 })
  })
})
