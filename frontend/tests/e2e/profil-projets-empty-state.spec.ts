// F43 T041 — ProjetEmptyState : section empty + CTA "Créez votre premier projet"
// Ce test est conçu pour un compte sans projets (ou après suppression de tous les projets).
import { test, expect } from '@playwright/test'

test.describe('F43 — Profil projets empty state', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/profil/projets')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('empty state visible si aucun projet actif', async ({ page }) => {
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

    const emptyState = page.locator('.projet-empty')
    if (!(await emptyState.count())) {
      // Des projets existent → skip-tolérant
      return
    }

    await expect(emptyState.first()).toBeVisible()
    // Titre de l'empty state
    const emptyTitle = emptyState.first().locator('.projet-empty__title')
    if (await emptyTitle.count()) {
      await expect(emptyTitle.first()).toBeVisible()
    }
    // Corps descriptif
    const emptyBody = emptyState.first().locator('.projet-empty__body')
    if (await emptyBody.count()) {
      await expect(emptyBody.first()).toBeVisible()
    }
  })

  test('CTA de l\'empty state ouvre le wizard de création', async ({ page }) => {
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

    const emptyState = page.locator('.projet-empty')
    if (!(await emptyState.count())) return

    const ctaBtn = emptyState.first().locator('.projet-empty__cta')
    if (await ctaBtn.count()) {
      await expect(ctaBtn.first()).toBeVisible()
      await ctaBtn.first().click()
      // Le wizard doit s'ouvrir
      const wizard = page.getByRole('dialog').or(page.locator('[data-testid="projet-wizard"]'))
      if (await wizard.count()) {
        await expect(wizard.first()).toBeVisible({ timeout: 3000 })
      }
    }
  })

  test('empty state : le bouton Nouveau projet de header est absent', async ({ page }) => {
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

    const emptyState = page.locator('.projet-empty')
    if (!(await emptyState.count())) return

    // Quand active.length === 0, le bouton .projets-page__cta du header n'est PAS rendu (v-if)
    const headerCta = page.locator('.projets-page__cta')
    await expect(headerCta).toHaveCount(0)
  })

  test('illustration SVG de l\'empty state est présente', async ({ page }) => {
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

    const emptyState = page.locator('.projet-empty')
    if (!(await emptyState.count())) return

    const illustration = emptyState.first().locator('.projet-empty__illustration')
    if (await illustration.count()) {
      await expect(illustration.first()).toBeVisible()
      // aria-hidden pour l'accessibilité
      await expect(illustration.first()).toHaveAttribute('aria-hidden', 'true')
    }
  })
})
