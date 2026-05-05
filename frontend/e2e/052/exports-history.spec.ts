// F52 US3 / SC-006 — E2E historique & génération d'export.
// Hypothèse : un compte PME pré-configuré (E2E_PME_EMAIL / PASSWORD).
// Skippé proprement si l'environnement n'est pas câblé.
import { test, expect } from '@playwright/test'

const PME_EMAIL = process.env.E2E_PME_EMAIL ?? ''
const PME_PASSWORD = process.env.E2E_PME_PASSWORD ?? ''

test.describe('F52 SC-006 — /dashboard/exports', () => {
  test.skip(!PME_EMAIL || !PME_PASSWORD, 'E2E_PME_EMAIL/PASSWORD non définis')

  test("ouvrir l'historique et lancer un nouvel export RGPD", async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(PME_EMAIL)
    await page.getByLabel(/Mot de passe/i).fill(PME_PASSWORD)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()

    await page.goto('/dashboard/exports')
    await expect(page.getByTestId('exports-page')).toBeVisible()
    await expect(page.getByTestId('exports-table')).toBeVisible()

    await page.getByTestId('exports-new-btn').click()
    await expect(page.getByTestId('new-export-sheet')).toBeVisible()
    await page.getByTestId('new-export-type-rgpd_full').check()
    await page.getByTestId('new-export-submit').click()

    // Une nouvelle ligne doit apparaître (status pending ou ready).
    await expect(page.locator('[data-testid^="export-row-"]').first()).toBeVisible({
      timeout: 10000,
    })
  })
})
