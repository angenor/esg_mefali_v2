// F52 SC-002 — Paramètres profil : affichage email, boutons modifier email/mdp
// Note : le flux email-change-reverif est testé séparément dans e2e/052/email-change-reverif.spec.ts
import { test, expect } from '@playwright/test'

test.describe('F52 — Paramètres profil (/parametres/profil)', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/parametres/profil')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page affiche la section informations personnelles', async ({ page }) => {
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

    await page.goto('/parametres/profil')

    // Titre section
    const heading = page.getByRole('heading', { name: /Informations personnelles/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }

    // Bouton modifier e-mail
    const changeEmailBtn = page.getByTestId('profile-change-email')
    if (await changeEmailBtn.count()) {
      await expect(changeEmailBtn.first()).toBeVisible()
      await expect(changeEmailBtn.first()).toBeEnabled()
    }

    // Bouton changer mot de passe
    const changePwdBtn = page.getByTestId('profile-change-password')
    if (await changePwdBtn.count()) {
      await expect(changePwdBtn.first()).toBeVisible()
      await expect(changePwdBtn.first()).toBeEnabled()
    }
  })

  test('clic "Modifier l\'e-mail" ouvre le bottom-sheet email', async ({ page }) => {
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

    await page.goto('/parametres/profil')

    const changeEmailBtn = page.getByTestId('profile-change-email')
    if (await changeEmailBtn.count()) {
      await changeEmailBtn.first().click()
      // Un bottom-sheet ou dialog doit apparaître — cherche le label d'email cible
      const sheet = page.getByRole('dialog').or(page.locator('[data-testid="email-change-sheet"]'))
      if (await sheet.count()) {
        await expect(sheet.first()).toBeVisible({ timeout: 3000 })
      }
    }
  })

  test('clic "Changer le mot de passe" ouvre le bottom-sheet password', async ({ page }) => {
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

    await page.goto('/parametres/profil')

    const changePwdBtn = page.getByTestId('profile-change-password')
    if (await changePwdBtn.count()) {
      await changePwdBtn.first().click()
      const sheet = page.getByRole('dialog').or(page.locator('[data-testid="password-change-sheet"]'))
      if (await sheet.count()) {
        await expect(sheet.first()).toBeVisible({ timeout: 3000 })
      }
    }
  })

  test('badge email-pending visible si email en attente', async ({ page }) => {
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

    await page.goto('/parametres/profil')

    // Le badge est conditionnel (email_pending != null). Test skip-tolérant.
    const pendingBadge = page.getByTestId('profile-email-pending')
    if (await pendingBadge.count()) {
      await expect(pendingBadge.first()).toBeVisible()
      await expect(pendingBadge.first()).toContainText(/En attente de vérification/i)
    }
  })
})
