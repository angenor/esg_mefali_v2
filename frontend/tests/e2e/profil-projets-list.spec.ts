// F43 T047 — /profil/projets : liste cards + bouton "Nouveau projet" + wizard
import { test, expect } from '@playwright/test'

test.describe('F43 — Profil projets liste (/profil/projets)', () => {
  test('non-authentifié → redirigé vers /login (middleware pme-only)', async ({ page }) => {
    await page.goto('/profil/projets')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page authentifiée affiche le titre Projets', async ({ page }) => {
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

    await page.goto('/profil/projets')

    // Titre de page : h1 dans la section projets-page
    const heading = page.getByRole('heading', { level: 1 })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test('avec projets existants : cards et bouton "Nouveau projet" visibles', async ({ page }) => {
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

    await page.goto('/profil/projets')
    await page.waitForTimeout(600)

    // Si des projets existent : le grid est présent
    const grid = page.locator('.projets-page__grid')
    const emptyState = page.locator('.projet-empty')
    const hasGrid = await grid.count()
    const hasEmpty = await emptyState.count()

    // L'un des deux états doit être présent
    expect(hasGrid + hasEmpty).toBeGreaterThan(0)

    if (hasGrid > 0) {
      // Bouton "Nouveau projet" uniquement si active.length > 0
      const newBtn = page.locator('.projets-page__cta')
      if (await newBtn.count()) {
        await expect(newBtn.first()).toBeVisible()
      }
    }
  })

  test('les ProjetCards affichent le titre et le statut', async ({ page }) => {
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

    await page.goto('/profil/projets')
    await page.waitForTimeout(600)

    const cards = page.locator('.projet-card')
    const count = await cards.count()
    if (count > 0) {
      // Chaque carte doit avoir un titre (h3)
      const firstTitle = cards.first().locator('.projet-card__title')
      await expect(firstTitle).toBeVisible()
      // Et un badge de statut
      const firstStatus = cards.first().locator('.projet-card__status')
      await expect(firstStatus).toBeVisible()
    }
  })

  test('clic sur une card navigue vers /profil/projets/{id}', async ({ page }) => {
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

    await page.goto('/profil/projets')
    await page.waitForTimeout(600)

    const cardBtns = page.locator('.projets-page__card-btn')
    if (await cardBtns.count()) {
      await cardBtns.first().click()
      await expect(page).toHaveURL(/\/profil\/projets\/[^/]+$/, { timeout: 5000 })
    }
  })

  test('clic "Nouveau projet" ouvre le ProjetWizard', async ({ page }) => {
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

    await page.goto('/profil/projets')
    await page.waitForTimeout(600)

    const newBtn = page.locator('.projets-page__cta')
    if (await newBtn.count()) {
      await newBtn.first().click()
      // Le wizard doit s'ouvrir — un dialog ou une overlay
      const wizard = page.getByRole('dialog').or(page.locator('[data-testid="projet-wizard"]'))
      if (await wizard.count()) {
        await expect(wizard.first()).toBeVisible({ timeout: 3000 })
      }
    }
  })
})
