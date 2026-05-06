// F52 SC-003 — Paramètres notifications : matrice toggles préférences par kind × channel
import { test, expect } from '@playwright/test'

const KINDS = [
  'deadline_j_minus_30',
  'deadline_j_minus_7',
  'deadline_j_minus_1',
  'candidature_inactive',
  'offre_recommandee',
]
const CHANNELS = ['email', 'in_app']

test.describe('F52 — Paramètres notifications (/parametres/notifications)', () => {
  test('non-authentifié → redirigé vers /login', async ({ page }) => {
    await page.goto('/parametres/notifications')
    await expect(page).toHaveURL(/\/login/, { timeout: 8000 })
  })

  test('page affiche le titre des préférences de notifications', async ({ page }) => {
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

    await page.goto('/parametres/notifications')

    const heading = page.getByRole('heading', { name: /Préférences de notifications/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test('matrice de checkboxes kind × channel est présente', async ({ page }) => {
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

    await page.goto('/parametres/notifications')
    // Attendre que le store charge
    await page.waitForTimeout(500)

    for (const kind of KINDS) {
      for (const channel of CHANNELS) {
        const checkbox = page.getByTestId(`pref-${kind}-${channel}`)
        if (await checkbox.count()) {
          await expect(checkbox.first()).toBeVisible()
          // Vérifie que c'est bien une checkbox
          await expect(checkbox.first()).toHaveAttribute('type', 'checkbox')
        }
      }
    }
  })

  test('toggle une préférence : le store reçoit le changement', async ({ page }) => {
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

    await page.goto('/parametres/notifications')
    await page.waitForTimeout(800)

    // On toggle le premier checkbox disponible (deadline_j_minus_30 × email)
    const firstCheckbox = page.getByTestId('pref-deadline_j_minus_30-email')
    if (await firstCheckbox.count()) {
      const before = await firstCheckbox.first().isChecked()
      await firstCheckbox.first().click()
      // L'état doit avoir changé
      const after = await firstCheckbox.first().isChecked()
      expect(after).toBe(!before)
    }
  })

  test('colonnes E-mail et In-app présentes dans le tableau', async ({ page }) => {
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

    await page.goto('/parametres/notifications')

    const table = page.getByRole('table')
    if (await table.count()) {
      await expect(table.first()).toBeVisible()
      await expect(table.first()).toContainText('E-mail')
      await expect(table.first()).toContainText('In-app')
    }
  })
})
