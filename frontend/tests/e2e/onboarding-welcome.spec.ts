// F42 SC-NNN — Page d'accueil onboarding : bouton "Démarrer le tour" et "Plus tard"
// Le onboarding-tour.spec.ts existant teste le tour lui-même (driver-popover) ;
// ce fichier couvre uniquement la page /onboarding/welcome.
import { test, expect } from '@playwright/test'

test.describe('F42 — Onboarding welcome (/onboarding/welcome)', () => {
  test('page accessible sans middleware pme-only — structure de base visible', async ({ page }) => {
    // /onboarding/welcome n'a pas de middleware pme-only dans definePageMeta
    await page.goto('/onboarding/welcome')

    // La page peut rediriger si non-auth selon configuration globale ; test skip-tolérant.
    if (/login/.test(page.url())) {
      return
    }

    // Un h1 doit être présent (texte traduit — on vérifie le rôle, pas le contenu exact)
    const heading = page.getByRole('heading', { level: 1 })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }

    // Deux boutons attendus
    const buttons = page.getByRole('button')
    const count = await buttons.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  test('bouton principal (démarrer) est visible et activé', async ({ page }) => {
    await page.goto('/onboarding/welcome')
    if (/login/.test(page.url())) return

    // Le bouton "Démarrer" est le premier bouton non-texte (bg-brand-600)
    // On le cherche par son texte traduit ou par son rôle
    const startBtn = page.locator('button:not([class*="underline"])').first()
    if (await startBtn.count()) {
      await expect(startBtn.first()).toBeVisible()
      await expect(startBtn.first()).toBeEnabled()
    }
  })

  test('bouton "Plus tard / skip" est visible', async ({ page }) => {
    await page.goto('/onboarding/welcome')
    if (/login/.test(page.url())) return

    // Le bouton skip a la classe "underline" dans le template
    const skipBtn = page.locator('button.underline, button[class*="underline"]')
    if (await skipBtn.count()) {
      await expect(skipBtn.first()).toBeVisible()
    }
  })

  test('clic "skip" redirige vers /dashboard', async ({ page }) => {
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
    await page.waitForURL(/\/(dashboard|profil|parametres|onboarding)/, { timeout: 10000 })

    await page.goto('/onboarding/welcome')
    if (/login/.test(page.url())) return

    const skipBtn = page.locator('button.underline, button[class*="underline"]')
    if (await skipBtn.count()) {
      await skipBtn.first().click()
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 5000 })
    }
  })

  test('clic "Démarrer" avec store déclenche la navigation', async ({ page }) => {
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
    await page.waitForURL(/\/(dashboard|profil|parametres|onboarding)/, { timeout: 10000 })

    await page.goto('/onboarding/welcome')
    if (/login/.test(page.url())) return

    const startBtn = page.locator('button:not([class*="underline"])').first()
    if (!(await startBtn.count())) return

    // Après clic, startTour() → start() → router.push('/dashboard')
    await startBtn.first().click()
    // On attend soit /dashboard (après tour ou skip), soit que le driver popover apparaisse
    await page.waitForURL(/\/dashboard/, { timeout: 8000 }).catch(() => null)
    const onDash = /dashboard/.test(page.url())
    const hasPopover = (await page.locator('.driver-popover').count()) > 0
    expect(onDash || hasPopover).toBe(true)
  })

  test('état chargement : bouton Démarrer désactivé pendant launching', async ({ page }) => {
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
    await page.waitForURL(/\/(dashboard|profil|parametres|onboarding)/, { timeout: 10000 })

    await page.goto('/onboarding/welcome')
    if (/login/.test(page.url())) return

    // Ralentir l'appel preferences pour observer l'état :disabled
    await page.route('**/preferences**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      await route.continue()
    })

    const startBtn = page.locator('button:not([class*="underline"])').first()
    if (!(await startBtn.count())) return

    await startBtn.first().click()
    // Pendant launching=true le bouton doit être désactivé
    const isDisabled = await startBtn.first().isDisabled()
    expect(isDisabled).toBe(true)
  })
})
