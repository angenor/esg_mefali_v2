// F48 T095 [US7] — History render: 6 entries → chart canvas; 1 entry → "Premier calcul" message.
// Backend DOWN → all API calls mocked via page.route().
import { test, expect } from '@playwright/test'
import path from 'path'

const NOW = Date.now()
function isoMonthsAgo(n: number): string {
  return new Date(NOW - n * 30 * 24 * 3600_000).toISOString()
}

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
  computed_at: isoMonthsAgo(0),
  subscores: {
    solidite_financiere: 75,
    performance_operationnelle: 80,
    engagement_esg: 65,
    gouvernance: 70,
  },
}

// 6 entries DESC by computed_at: scores 72, 70, 68, 62, 55, 50
const MOCK_HISTORY_6 = {
  items: [
    { id: 'h6', combine: 72, solvabilite: 70, impact_vert: 74, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(0), coherence_warning: false },
    { id: 'h5', combine: 70, solvabilite: 68, impact_vert: 72, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(1), coherence_warning: false },
    { id: 'h4', combine: 68, solvabilite: 66, impact_vert: 70, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(2), coherence_warning: false },
    { id: 'h3', combine: 62, solvabilite: 60, impact_vert: 64, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(3), coherence_warning: false },
    { id: 'h2', combine: 55, solvabilite: 53, impact_vert: 57, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(4), coherence_warning: false },
    { id: 'h1', combine: 50, solvabilite: 48, impact_vert: 52, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(5), coherence_warning: false },
  ],
}

// Single entry
const MOCK_HISTORY_1 = {
  items: [
    { id: 'h1', combine: 72, solvabilite: 70, impact_vert: 74, subscores: null, methodologie_version: 1, computed_at: isoMonthsAgo(0), coherence_warning: false },
  ],
}

const MOCK_ELIGIBILITY = { items: [], evaluated_at: isoMonthsAgo(0), catalog_version_max: 1 }
const MOCK_RECOMMENDATIONS = { items: [], selected_subscores: [] }

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-history-${name}.png`,
  )
}

async function setupCommonMocks(page: import('@playwright/test').Page, historyPayload: object) {
  await page.route('**/me', async (route) => {
    const url = route.request().url()
    if (url.includes('/credit-score') || url.includes('/credit-data')) {
      await route.fallback()
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ME) })
  })

  await page.route('**/me/credit-score/history**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(historyPayload) })
  })

  await page.route('**/me/credit-score/eligibility**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ELIGIBILITY) })
  })

  await page.route('**/me/credit-score/recommendations**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMMENDATIONS) })
  })

  await page.route('**/me/credit-score', async (route) => {
    const url = route.request().url()
    if (url.includes('/history') || url.includes('/eligibility') || url.includes('/recommendations') || url.includes('/recompute')) {
      await route.fallback()
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SCORE) })
  })

  await page.route('**/me/credit-data', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
  })
}

test.describe('Credit Score — History render (F48 T095 US7)', () => {
  test('US7-A : 6 entrées → section historique + titre graphe + canvas visible', async ({ page }) => {
    await setupCommonMocks(page, MOCK_HISTORY_6)
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // Section "Historique du score" visible
    const historySection = page.locator('section').filter({ hasText: 'Historique du score' })
    await expect(historySection).toBeVisible({ timeout: 8000 })

    // Titre du graphe "Évolution du score"
    await expect(historySection.getByText('Évolution du score')).toBeVisible({ timeout: 5000 })

    // Canvas chart.js rendu (VizLineChart injecte un <canvas>)
    const canvas = historySection.locator('canvas')
    await expect(canvas).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('01-six-entries-chart') })
  })

  test('US7-B : 1 seule entrée → message "Premier calcul" + pas de canvas', async ({ page }) => {
    await setupCommonMocks(page, MOCK_HISTORY_1)
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    const historySection = page.locator('section').filter({ hasText: 'Historique du score' })
    await expect(historySection).toBeVisible({ timeout: 8000 })

    // Le message "Premier calcul" doit être visible
    await expect(
      historySection.getByText('Premier calcul — l\'historique apparaîtra après votre prochain recalcul.'),
    ).toBeVisible({ timeout: 5000 })

    // Pas de canvas lorsqu'il n'y a qu'une seule entrée
    const canvas = historySection.locator('canvas')
    await expect(canvas).not.toBeVisible()

    await page.screenshot({ path: screenshotPath('02-single-entry-no-chart') })
  })
})
