// F48 [US5] T081 — Edit money validation: empty, negative, non-numeric inputs.
// Mocks backend with page.route(); no server required.
import { test, expect } from '@playwright/test'
import path from 'path'

const NOW_ISO = new Date().toISOString()

const MOCK_ME = {
  id: 'user-1',
  email: 'pme-test@example.com',
  role: 'pme',
  account_id: 'ent-1',
  entreprise_id: 'ent-1',
  verified: true,
}

const MOCK_SCORE = {
  id: 'test-id',
  entreprise_id: 'ent-1',
  solvabilite: 70,
  impact_vert: 74,
  combine: 72,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: NOW_ISO,
  subscores: {
    solidite_financiere: 75,
    performance_operationnelle: 80,
    engagement_esg: 65,
    gouvernance: 70,
  },
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-money-validation-${name}.png`,
  )
}

test.describe('Credit Score — Money validation (F48 US5 T081)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/me', async (route) => {
      const url = route.request().url()
      if (url.includes('/credit-score') || url.includes('/credit-data')) {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ME),
      })
    })

    await page.route('**/me/credit-score/history**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      })
    })

    await page.route('**/me/credit-score/eligibility**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], evaluated_at: NOW_ISO, catalog_version_max: 1 }),
      })
    })

    await page.route('**/me/credit-score/recommendations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], selected_subscores: [] }),
      })
    })

    await page.route('**/me/credit-score', async (route) => {
      const url = route.request().url()
      if (
        url.includes('/history')
        || url.includes('/eligibility')
        || url.includes('/recommendations')
        || url.includes('/recompute')
      ) {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SCORE),
      })
    })

    await page.route('**/me/credit-data', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      })
    })

    await page.goto('/credit-score')

    // Open the edit drawer
    const editBtn = page.getByRole('button', { name: 'Mettre à jour mes données financières' })
    await expect(editBtn).toBeVisible({ timeout: 10000 })
    await editBtn.click()

    // Wait for drawer step 1
    await expect(page.getByText('Étape 1 sur 5')).toBeVisible({ timeout: 5000 })
  })

  test('validation-A : champ vide → « Le montant est obligatoire. »', async ({ page }) => {
    // Leave amount empty, click Suivant
    const nextBtn = page.getByRole('button', { name: 'Suivant' })
    await nextBtn.click()

    // Error message should appear
    await expect(page.getByText('Le montant est obligatoire.')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('01-empty-required') })
  })

  test('validation-B : montant négatif → « Le montant ne peut pas être négatif. »', async ({ page }) => {
    const amountInput = page.locator('input[inputmode="decimal"]')
    await amountInput.fill('-5000')

    const nextBtn = page.getByRole('button', { name: 'Suivant' })
    await nextBtn.click()

    await expect(page.getByText('Le montant ne peut pas être négatif.')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('02-negative-amount') })
  })

  test('validation-C : montant non numérique → « Le montant doit être un nombre valide. »', async ({ page }) => {
    const amountInput = page.locator('input[inputmode="decimal"]')
    await amountInput.fill('abc')

    const nextBtn = page.getByRole('button', { name: 'Suivant' })
    await nextBtn.click()

    await expect(page.getByText('Le montant doit être un nombre valide.')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('03-non-numeric') })
  })
})
