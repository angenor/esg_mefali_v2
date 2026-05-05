// F48 [US5] T080 — Edit data flow: 4-step wizard, recap, submit → toast success.
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

const MOCK_RECOMPUTED_SCORE = {
  id: 'test-id-v2',
  entreprise_id: 'ent-1',
  solvabilite: 76,
  impact_vert: 80,
  combine: 78,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: new Date().toISOString(),
  subscores: {
    solidite_financiere: 80,
    performance_operationnelle: 82,
    engagement_esg: 70,
    gouvernance: 75,
  },
}

const MOCK_HISTORY = { items: [] }
const MOCK_ELIGIBILITY = {
  items: [],
  evaluated_at: NOW_ISO,
  catalog_version_max: 1,
}
const MOCK_RECOMMENDATIONS = {
  items: [],
  selected_subscores: [],
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-edit-flow-${name}.png`,
  )
}

test.describe('Credit Score — Edit data flow (F48 US5 T080)', () => {
  test('flow complet : 4 étapes → récap → soumettre → toast succès', async ({ page }) => {
    let creditDataPosted = false
    let recomputePosted = false

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
        body: JSON.stringify(MOCK_HISTORY),
      })
    })

    await page.route('**/me/credit-score/eligibility**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ELIGIBILITY),
      })
    })

    await page.route('**/me/credit-score/recommendations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_RECOMMENDATIONS),
      })
    })

    await page.route('**/me/credit-score/recompute', async (route) => {
      recomputePosted = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_RECOMPUTED_SCORE),
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
      if (route.request().method() === 'POST') {
        creditDataPosted = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        })
      }
      else {
        await route.fallback()
      }
    })

    await page.goto('/credit-score')

    // Wait for the page to load
    const editBtn = page.getByRole('button', { name: 'Mettre à jour mes données financières' })
    await expect(editBtn).toBeVisible({ timeout: 10000 })

    // Open the drawer
    await editBtn.click()
    await page.screenshot({ path: screenshotPath('01-drawer-open') })

    // Step 1: Chiffre d'affaires
    await expect(page.getByText('Étape 1 sur 5')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: "Chiffre d'affaires" })).toBeVisible()

    const amountInput = page.locator('input[inputmode="decimal"]')
    await amountInput.fill('12000000')

    const nextBtn = page.getByRole('button', { name: 'Suivant' })
    await nextBtn.click()

    // Step 2: EBE
    await expect(page.getByText('Étape 2 sur 5')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: /EBE|Excédent brut/ })).toBeVisible()

    await amountInput.fill('2500000')
    await nextBtn.click()

    // Step 3: Dette
    await expect(page.getByText('Étape 3 sur 5')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: /Dette/ })).toBeVisible()

    await amountInput.fill('4000000')
    await nextBtn.click()

    // Step 4: Fonds propres
    await expect(page.getByText('Étape 4 sur 5')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: /Fonds propres/ })).toBeVisible()

    await amountInput.fill('5000000')
    await nextBtn.click()

    // Step 5: Récap
    await expect(page.getByText('Étape 5 sur 5')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: 'Récapitulatif' })).toBeVisible()

    // Verify 4 recap lines visible
    await expect(page.getByText("Chiffre d'affaires")).toBeVisible()
    await expect(page.getByText(/EBE|Excédent brut/)).toBeVisible()
    await expect(page.getByText('Dette totale')).toBeVisible()
    await expect(page.getByText('Fonds propres')).toBeVisible()

    await page.screenshot({ path: screenshotPath('02-recap-step') })

    // Submit
    const submitBtn = page.getByRole('button', { name: 'Soumettre et recalculer' })
    await expect(submitBtn).toBeVisible()
    await submitBtn.click()

    // Wait for toast success message
    await expect(page.getByText('Données enregistrées et score recalculé.')).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('03-toast-success') })

    // Verify APIs were called
    expect(creditDataPosted).toBe(true)
    expect(recomputePosted).toBe(true)

    // Drawer should be closed after success
    await expect(page.getByText('Étape 5 sur 5')).not.toBeVisible({ timeout: 5000 })
  })
})
