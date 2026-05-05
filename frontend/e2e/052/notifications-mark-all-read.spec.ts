// F52 SC-002 — E2E mark-all-read.
// Hypothèse : un seed dispose de notifications non-lues sur la PME courante.
// Si l'environnement n'est pas configuré, le test est skippé proprement.
import { test, expect } from '@playwright/test'

const PME_EMAIL = process.env.E2E_PME_EMAIL ?? ''
const PME_PASSWORD = process.env.E2E_PME_PASSWORD ?? ''

test.describe('F52 SC-002 — Mark all read', () => {
  test.skip(!PME_EMAIL || !PME_PASSWORD, 'E2E_PME_EMAIL/PASSWORD non définis')

  test('marquer toutes les non-lues remet la cloche à 0', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(PME_EMAIL)
    await page.getByLabel(/Mot de passe/i).fill(PME_PASSWORD)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()

    await page.goto('/notifications')
    const button = page.getByTestId('mark-all-read-btn')
    await expect(button).toBeVisible()
    if (await button.isDisabled()) {
      test.info().annotations.push({ type: 'note', description: 'Aucune non-lue à marquer.' })
      return
    }
    await button.click()
    await expect(page.getByTestId('mark-all-read-btn')).toBeDisabled({ timeout: 5000 })
    // La cloche du shell doit être à 0 (pas de badge).
    const badge = page.getByTestId('bell-badge')
    await expect(badge).toBeHidden()
  })
})
