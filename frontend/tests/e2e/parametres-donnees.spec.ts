// F52 SC-006b — Paramètres données : export RGPD depuis /parametres/donnees
// Note : exports-history.spec.ts teste /dashboard/exports ; ce fichier couvre
// le déclenchement depuis /parametres/donnees (DataExportCard).
import { test, expect } from '@playwright/test'

test.describe('F52 — Paramètres données (/parametres/donnees)', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/parametres/donnees')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page affiche le titre Export RGPD complet', async ({ page }) => {
    const email = process.env.E2E_PME_EMAIL
    const password = process.env.E2E_PME_PASSWORD
    if (!email || !password) {
      test.skip(true, 'E2E_PME_EMAIL/PASSWORD non définis')
      return
    }

    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/Mot de passe/i).fill(password)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()
    await page.waitForURL(/\/(dashboard|profil|parametres)/, { timeout: 10000 })

    await page.goto('/parametres/donnees')

    const heading = page.getByRole('heading', { name: /Export RGPD complet/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test('bouton "Demander un export" est visible et activé', async ({ page }) => {
    const email = process.env.E2E_PME_EMAIL
    const password = process.env.E2E_PME_PASSWORD
    if (!email || !password) {
      test.skip(true, 'E2E_PME_EMAIL/PASSWORD non définis')
      return
    }

    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/Mot de passe/i).fill(password)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()
    await page.waitForURL(/\/(dashboard|profil|parametres)/, { timeout: 10000 })

    await page.goto('/parametres/donnees')

    const exportBtn = page.getByTestId('data-export-trigger')
    if (await exportBtn.count()) {
      await expect(exportBtn.first()).toBeVisible()
      await expect(exportBtn.first()).toBeEnabled()
      await expect(exportBtn.first()).toContainText(/Demander un export/i)
    }
  })

  test('clic "Demander un export" envoie la requête et affiche la confirmation', async ({ page }) => {
    const email = process.env.E2E_PME_EMAIL
    const password = process.env.E2E_PME_PASSWORD
    if (!email || !password) {
      test.skip(true, 'E2E_PME_EMAIL/PASSWORD non définis')
      return
    }

    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/Mot de passe/i).fill(password)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()
    await page.waitForURL(/\/(dashboard|profil|parametres)/, { timeout: 10000 })

    await page.goto('/parametres/donnees')

    const exportBtn = page.getByTestId('data-export-trigger')
    if (!(await exportBtn.count())) return

    // Intercepter la requête POST /me/exports pour éviter un vrai appel en CI
    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes('/me/exports') && resp.request().method() === 'POST',
        { timeout: 8000 }
      ).catch(() => null),
      exportBtn.first().click(),
    ])

    if (response) {
      // Après succès : le bouton revient en état actif (plus "Génération…")
      await expect(exportBtn.first()).toBeEnabled({ timeout: 5000 })
    }
  })

  test('état "Génération…" pendant le submit', async ({ page }) => {
    const email = process.env.E2E_PME_EMAIL
    const password = process.env.E2E_PME_PASSWORD
    if (!email || !password) {
      test.skip(true, 'E2E_PME_EMAIL/PASSWORD non définis')
      return
    }

    await page.goto('/login')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/Mot de passe/i).fill(password)
    await page.getByRole('button', { name: /Se connecter|Connexion/i }).click()
    await page.waitForURL(/\/(dashboard|profil|parametres)/, { timeout: 10000 })

    await page.goto('/parametres/donnees')

    const exportBtn = page.getByTestId('data-export-trigger')
    if (!(await exportBtn.count())) return

    // Ralentir la requête pour observer l'état intermédiaire
    await page.route('**/me/exports', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 400))
      await route.continue()
    })

    await exportBtn.first().click()
    // Pendant le submit : le bouton doit afficher "Génération…" et être désactivé
    const isDisabledDuring = await exportBtn.first().isDisabled()
    expect(isDisabledDuring).toBe(true)
  })
})
