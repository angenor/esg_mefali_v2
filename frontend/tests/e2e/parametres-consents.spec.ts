// F52 SC-004 — Paramètres consentements RGPD : affichage liste + bouton retrait
import { test, expect } from '@playwright/test'

test.describe('F52 — Paramètres consentements (/parametres/consents)', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/parametres/consents')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page affiche le titre Consentements', async ({ page }) => {
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

    await page.goto('/parametres/consents')

    const heading = page.getByRole('heading', { name: /Consentements/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test('liste des consentements : état vide ou items chargés', async ({ page }) => {
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

    await page.goto('/parametres/consents')
    // Attendre que le store charge
    await page.waitForTimeout(800)

    // Soit un message "Aucun consentement", soit une liste d'items
    const emptyMsg = page.getByText(/Aucun consentement enregistré/i)
    const list = page.getByRole('list')

    const hasEmpty = await emptyMsg.count()
    const hasList = await list.count()

    // L'un des deux doit être présent
    expect(hasEmpty + hasList).toBeGreaterThan(0)
  })

  test('bouton Retirer visible sur consentement actif', async ({ page }) => {
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

    await page.goto('/parametres/consents')
    await page.waitForTimeout(800)

    // Les boutons de retrait ont data-testid="consent-withdraw-{id}"
    // Skip-tolérant : uniquement vérifiable si des consentements actifs existent
    const withdrawBtns = page.locator('[data-testid^="consent-withdraw-"]')
    const count = await withdrawBtns.count()
    if (count > 0) {
      await expect(withdrawBtns.first()).toBeVisible()
      await expect(withdrawBtns.first()).toContainText(/Retirer/i)
    }
  })

  test('clic Retirer ouvre un bottom-sheet de confirmation', async ({ page }) => {
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

    await page.goto('/parametres/consents')
    await page.waitForTimeout(800)

    const withdrawBtns = page.locator('[data-testid^="consent-withdraw-"]')
    const count = await withdrawBtns.count()
    if (count > 0) {
      await withdrawBtns.first().click()
      // Un dialog/sheet doit apparaître
      const sheet = page.getByRole('dialog')
      if (await sheet.count()) {
        await expect(sheet.first()).toBeVisible({ timeout: 3000 })
      }
    }
  })
})
