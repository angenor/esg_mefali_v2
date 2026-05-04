// F48 [Polish T119] — Partial coverage banner: null subscores → banner + Non calculé CTA.
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

// Score with 2 null subscores: performance_operationnelle and engagement_esg
const MOCK_SCORE_PARTIAL = {
  id: 'test-partial',
  entreprise_id: 'ent-1',
  solvabilite: 72,
  impact_vert: 70,
  combine: 71,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: NOW_ISO,
  subscores: {
    solidite_financiere: 75,
    performance_operationnelle: null,
    engagement_esg: null,
    gouvernance: 70,
  },
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-partial-coverage-${name}.png`,
  )
}

test.describe('Credit Score — Partial coverage (F48 Polish T119)', () => {
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
        body: JSON.stringify(MOCK_SCORE_PARTIAL),
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
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })
  })

  test('Polish-A : PartialCoverageBanner visible avec les sous-scores manquants', async ({ page }) => {
    // The banner (role=status aside) should be visible
    const banner = page.locator('aside[role="status"]')
    await expect(banner).toBeVisible({ timeout: 8000 })

    // Banner text should mention "Performance opérationnelle"
    await expect(banner).toContainText('Performance opérationnelle', { timeout: 5000 })

    // Banner text should mention "Engagement ESG"
    await expect(banner).toContainText('Engagement ESG', { timeout: 5000 })

    await page.screenshot({ path: screenshotPath('01-banner-visible') })
  })

  test('Polish-B : 2 cartes sous-scores affichent « Non calculé »', async ({ page }) => {
    // Wait for page to load
    await expect(page.locator('aside[role="status"]')).toBeVisible({ timeout: 8000 })

    // "Non calculé" should appear at least twice (for 2 null subscores)
    const nonCalculeTexts = page.getByText('Non calculé')
    const count = await nonCalculeTexts.count()
    expect(count).toBeGreaterThanOrEqual(2)

    await page.screenshot({ path: screenshotPath('02-non-calcule-cards') })
  })

  test('Polish-C : CTA « Compléter mes données » dans la bannière', async ({ page }) => {
    const banner = page.locator('aside[role="status"]')
    await expect(banner).toBeVisible({ timeout: 8000 })

    // CTA button in banner
    const cta = banner.getByRole('button', { name: 'Compléter mes données' })
    await expect(cta).toBeVisible()

    await page.screenshot({ path: screenshotPath('03-cta-visible') })

    // Click CTA → should open the edit drawer
    await cta.click()
    await expect(page.getByText('Étape 1 sur 5')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('04-drawer-opened-from-banner') })
  })
})
