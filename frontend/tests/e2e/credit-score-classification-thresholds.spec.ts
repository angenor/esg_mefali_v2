// F48 T042 [US1] — Classification thresholds: 4 parameterized score cases.
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

const BASE_HISTORY = {
  items: [],
}

const MOCK_ELIGIBILITY = {
  items: [],
  evaluated_at: NOW_ISO,
  catalog_version_max: 1,
}

const MOCK_RECOMMENDATIONS = {
  items: [],
  selected_subscores: [],
}

function makeMockScore(combine: number) {
  return {
    id: `test-${combine}`,
    entreprise_id: 'ent-1',
    solvabilite: combine,
    impact_vert: combine,
    combine,
    facteurs: [],
    methodologie_version: 1,
    coherence_warning: false,
    computed_at: NOW_ISO,
    subscores: {
      solidite_financiere: combine,
      performance_operationnelle: combine,
      engagement_esg: combine,
      gouvernance: combine,
    },
  }
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-thresholds-${name}.png`,
  )
}

const CASES = [
  { score: 80, expectedLabel: 'Excellent' },
  { score: 60, expectedLabel: 'Bon' },
  { score: 45, expectedLabel: 'À améliorer' },
  { score: 35, expectedLabel: 'Insuffisant' },
] as const

test.describe('Credit Score — Classification thresholds (F48 T042)', () => {
  for (const { score, expectedLabel } of CASES) {
    test(`score ${score} → classification « ${expectedLabel} »`, async ({ page }) => {
      const mockScore = makeMockScore(score)

      // Mock /me (auth)
      await page.route('**/me', async (route) => {
        const url = route.request().url()
        if (
          url.includes('/credit-score')
          || url.includes('/credit-data')
        ) {
          await route.fallback()
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ME),
        })
      })

      // Mock credit-score history (before main score to avoid fallback issues)
      await page.route('**/me/credit-score/history**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(BASE_HISTORY),
        })
      })

      // Mock eligibility
      await page.route('**/me/credit-score/eligibility**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ELIGIBILITY),
        })
      })

      // Mock recommendations
      await page.route('**/me/credit-score/recommendations**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_RECOMMENDATIONS),
        })
      })

      // Mock main credit-score (exclude sub-paths)
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
          body: JSON.stringify(mockScore),
        })
      })

      // Mock credit-data (POST)
      await page.route('**/me/credit-data', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true }),
        })
      })

      await page.goto('/credit-score')

      // Wait for score value to appear in SVG
      const gaugeSection = page.locator('section').filter({ hasText: 'Score crédit ESG' }).first()
      await expect(gaugeSection).toBeVisible({ timeout: 10000 })

      // Assert classification label visible — scope to gauge section to avoid nav/sidebar matches
      const gaugeSection2 = page.locator('section').filter({ hasText: 'Score crédit ESG' }).first()
      await expect(gaugeSection2).toBeVisible({ timeout: 8000 })
      await expect(gaugeSection2.getByText(expectedLabel, { exact: true })).toBeVisible({ timeout: 8000 })

      await page.screenshot({ path: screenshotPath(`score-${score}-${expectedLabel.replace(/\s/g, '-').replace(/[éàâ]/g, c => ({ 'é': 'e', 'à': 'a', 'â': 'a' }[c] ?? c))}`) })
    })
  }
})
