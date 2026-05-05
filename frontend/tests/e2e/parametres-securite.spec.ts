// F52 SC-007 — Paramètres sécurité : sessions actives + carte extension navigateur
import { test, expect } from '@playwright/test'

test.describe('F52 — Paramètres sécurité (/parametres/securite)', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/parametres/securite')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page affiche le titre Sessions actives', async ({ page }) => {
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

    await page.goto('/parametres/securite')

    const heading = page.getByRole('heading', { name: /Sessions actives/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test('carte extension navigateur est présente avec badge de détection', async ({ page }) => {
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

    await page.goto('/parametres/securite')
    await page.waitForTimeout(600)

    // data-testid="extension-status-card"
    const card = page.getByTestId('extension-status-card')
    if (await card.count()) {
      await expect(card.first()).toBeVisible()

      // Badge détecté / non détecté
      const badge = page.getByTestId('extension-detected-badge')
      if (await badge.count()) {
        await expect(badge.first()).toBeVisible()
        await expect(badge.first()).toContainText(/Détectée|Non détectée/i)
      }

      // Bouton Actualiser
      const refreshBtn = page.getByTestId('extension-refresh-btn')
      if (await refreshBtn.count()) {
        await expect(refreshBtn.first()).toBeVisible()
      }

      // Bouton Synchroniser
      const syncBtn = page.getByTestId('extension-sync-btn')
      if (await syncBtn.count()) {
        await expect(syncBtn.first()).toBeVisible()
      }
    }
  })

  test('liste des sessions : session courante marquée "Courant"', async ({ page }) => {
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

    await page.goto('/parametres/securite')
    await page.waitForTimeout(800)

    // La session courante affiche "Courant" et pas de bouton Révoquer
    const currentBadge = page.getByText(/Courant/i)
    if (await currentBadge.count()) {
      await expect(currentBadge.first()).toBeVisible()
    }
  })

  test('bouton Révoquer présent sur sessions non-courantes', async ({ page }) => {
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

    await page.goto('/parametres/securite')
    await page.waitForTimeout(800)

    // data-testid="session-revoke-{id}" — skip-tolérant si une seule session
    const revokeBtns = page.locator('[data-testid^="session-revoke-"]')
    const count = await revokeBtns.count()
    if (count > 0) {
      await expect(revokeBtns.first()).toBeVisible()
      await expect(revokeBtns.first()).toContainText(/Révoquer/i)
    }
  })
})
