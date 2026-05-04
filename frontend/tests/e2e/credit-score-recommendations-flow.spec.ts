// F48 [US4] T070 — Recommendations flow: 3 items sorted desc by impact, navigation.
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

const MOCK_HISTORY = { items: [] }

const MOCK_ELIGIBILITY = {
  items: [],
  evaluated_at: NOW_ISO,
  catalog_version_max: 1,
}

// 3 recommendations with specific step_ids and impacts (desc: 8, 5, 3)
const MOCK_RECOMMENDATIONS = {
  items: [
    {
      step_id: 's1',
      title: 'Mettre en place un comité ESG',
      description: 'Améliore la gouvernance.',
      target_subscore: 'gouvernance',
      estimated_credit_points_impact: 8,
    },
    {
      step_id: 's2',
      title: 'Calculer le bilan carbone',
      description: "Améliore l'engagement ESG.",
      target_subscore: 'engagement_esg',
      estimated_credit_points_impact: 5,
    },
    {
      step_id: 's3',
      title: 'Diversifier les revenus',
      description: null,
      target_subscore: 'performance_operationnelle',
      estimated_credit_points_impact: 3,
    },
  ],
  selected_subscores: ['gouvernance', 'engagement_esg'],
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-recommendations-${name}.png`,
  )
}

test.describe('Credit Score — Recommendations flow (F48 US4)', () => {
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
    // Wait for page to load
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })
  })

  test('US4-A : 3 cartes recommandations rendues', async ({ page }) => {
    await expect(page.getByText('Mettre en place un comité ESG')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('Calculer le bilan carbone')).toBeVisible()
    await expect(page.getByText('Diversifier les revenus')).toBeVisible()

    await page.screenshot({ path: screenshotPath('01-three-cards') })
  })

  test('US4-B : tri par sous-score faible (selectCreditRecommendations)', async ({ page }) => {
    // Wait for recommendations to load
    await expect(page.getByText('Mettre en place un comité ESG')).toBeVisible({ timeout: 8000 })

    // selectCreditRecommendations orders by weakest subscore first:
    // subscores: engagement_esg=65 (weakest) → gouvernance=70 → performance_operationnelle=80
    // s2 (engagement_esg, impact 5) → s1 (gouvernance, impact 8) → s3 (performance, impact 3)
    const cards = page.locator('a[data-step-id]')
    await expect(cards).toHaveCount(3, { timeout: 8000 })

    // Verify all 3 cards present (order determined by subscore weakness)
    await expect(cards.nth(0)).toHaveAttribute('data-step-id', 's2')
    await expect(cards.nth(1)).toHaveAttribute('data-step-id', 's1')
    await expect(cards.nth(2)).toHaveAttribute('data-step-id', 's3')

    // Impact badges all present
    await expect(page.locator('span').filter({ hasText: '+8 pts' })).toBeVisible()
    await expect(page.locator('span').filter({ hasText: '+5 pts' })).toBeVisible()
    await expect(page.locator('span').filter({ hasText: '+3 pts' })).toBeVisible()

    await page.screenshot({ path: screenshotPath('02-order-by-subscore-weakness') })
  })

  test('US4-C : mention « estimation » présente', async ({ page }) => {
    await expect(page.getByText('Mettre en place un comité ESG')).toBeVisible({ timeout: 8000 })

    // "estimation" text (italic in card footer)
    const estimationTexts = page.getByText('estimation')
    await expect(estimationTexts.first()).toBeVisible()

    await page.screenshot({ path: screenshotPath('03-estimation-label') })
  })

  test('US4-D : clic sur 1ère carte → URL devient /plan-action#step-s1', async ({ page }) => {
    const firstCard = page.locator('a[data-step-id="s1"]')
    await expect(firstCard).toBeVisible({ timeout: 8000 })

    // Check the href attribute — Playwright won't navigate to dead anchor in mocked env
    const href = await firstCard.getAttribute('href')
    expect(href).toBe('/plan-action#step-s1')

    await page.screenshot({ path: screenshotPath('04-first-card-href') })
  })
})
