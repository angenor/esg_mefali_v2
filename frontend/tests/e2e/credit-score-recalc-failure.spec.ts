// F48 [US6] T083 — Recalc failure: 500 → error toast + gauge unchanged at 72.
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
    `credit-score-recalc-failure-${name}.png`,
  )
}

test.describe('Credit Score — Recalc failure (F48 US6 T083)', () => {
  test('recalc 500 → toast erreur FR + gauge reste à 72', async ({ page }) => {
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

    // Mock recompute → 500
    await page.route('**/me/credit-score/recompute', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
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

    // Wait for gauge section to load with score 72
    const gaugeSection = page.locator('section').filter({ hasText: 'Score crédit ESG' }).first()
    await expect(gaugeSection).toBeVisible({ timeout: 10000 })

    // Confirm score 72 is displayed initially
    const gaugeValue = gaugeSection.locator('text').filter({ hasText: '72' }).first()
    await expect(gaugeValue).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('01-before-recalc') })

    // Click "Recalculer maintenant"
    const recalcBtn = page.getByRole('button', { name: 'Recalculer maintenant' }).first()
    await expect(recalcBtn).toBeVisible()
    await recalcBtn.click()

    // Toast error should appear with French message
    await expect(
      page.getByText('Le recalcul a échoué. Votre score précédent est conservé.'),
    ).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('02-error-toast') })

    // Gauge should remain at 72 (page re-fetches original score on error)
    await expect(gaugeSection.locator('text').filter({ hasText: '72' }).first()).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('03-gauge-unchanged') })
  })
})
