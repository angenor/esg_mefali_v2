// F48 T071 [US4 edge case] — Recommendation dead link behavior.
// step_id="" → href="/plan-action" (no fragment)
// step_id="nonexistant" → href="/plan-action#step-nonexistant" (no client-side check)
// Backend DOWN → all API calls mocked via page.route().
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
const MOCK_ELIGIBILITY = { items: [], evaluated_at: NOW_ISO, catalog_version_max: 1 }

// Recommendations avec step_id vide et step_id inexistant
const MOCK_RECOMMENDATIONS_DEADLINKS = {
  items: [
    {
      step_id: '',
      title: 'Action sans étape liée',
      description: 'Cette action n\'a pas d\'étape plan d\'action associée.',
      target_subscore: 'engagement_esg',
      estimated_credit_points_impact: 4,
    },
    {
      step_id: 'nonexistant',
      title: 'Action avec étape inexistante',
      description: 'L\'étape plan-action correspondante n\'existe pas.',
      target_subscore: 'gouvernance',
      estimated_credit_points_impact: 6,
    },
    {
      step_id: 's-valid',
      title: 'Action avec étape valide',
      description: 'Cette action pointe vers une étape réelle.',
      target_subscore: 'solidite_financiere',
      estimated_credit_points_impact: 3,
    },
  ],
  selected_subscores: ['engagement_esg', 'gouvernance'],
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-deadlink-${name}.png`,
  )
}

test.describe('Credit Score — Recommendation dead link (F48 T071 US4 edge)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/me', async (route) => {
      const url = route.request().url()
      if (url.includes('/credit-score') || url.includes('/credit-data')) {
        await route.fallback()
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ME) })
    })

    await page.route('**/me/credit-score/history**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HISTORY) })
    })

    await page.route('**/me/credit-score/eligibility**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ELIGIBILITY) })
    })

    await page.route('**/me/credit-score/recommendations**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMMENDATIONS_DEADLINKS) })
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

    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })
  })

  test('US4-edge-A : step_id vide → href="/plan-action" sans fragment', async ({ page }) => {
    // La carte avec step_id="" doit avoir un href="/plan-action" (pas de fragment)
    await expect(page.getByText('Action sans étape liée')).toBeVisible({ timeout: 8000 })

    // Le lien avec step_id vide — le composant RecommendationCard utilise data-step-id
    // Selon l'implémentation : href = step_id ? `/plan-action#step-${step_id}` : '/plan-action'
    const emptyStepCard = page.locator('a[data-step-id=""]')
    await expect(emptyStepCard).toBeVisible({ timeout: 5000 })
    const href = await emptyStepCard.getAttribute('href')
    expect(href).toBe('/plan-action')

    await page.screenshot({ path: screenshotPath('01-empty-step-id-href') })
  })

  test('US4-edge-B : step_id non vide inexistant → href="/plan-action#step-nonexistant"', async ({ page }) => {
    // La carte avec step_id="nonexistant" doit avoir href="/plan-action#step-nonexistant"
    // Le frontend ne vérifie pas l'existence côté client — le routage /plan-action gère le fallback
    await expect(page.getByText('Action avec étape inexistante')).toBeVisible({ timeout: 8000 })

    const nonexistantCard = page.locator('a[data-step-id="nonexistant"]')
    await expect(nonexistantCard).toBeVisible({ timeout: 5000 })
    const href = await nonexistantCard.getAttribute('href')
    expect(href).toBe('/plan-action#step-nonexistant')

    await page.screenshot({ path: screenshotPath('02-nonexistant-step-id-href') })
  })

  test('US4-edge-C : step_id valide → href="/plan-action#step-s-valid"', async ({ page }) => {
    await expect(page.getByText('Action avec étape valide')).toBeVisible({ timeout: 8000 })

    const validCard = page.locator('a[data-step-id="s-valid"]')
    await expect(validCard).toBeVisible({ timeout: 5000 })
    const href = await validCard.getAttribute('href')
    expect(href).toBe('/plan-action#step-s-valid')

    await page.screenshot({ path: screenshotPath('03-valid-step-id-href') })
  })
})
