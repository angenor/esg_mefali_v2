// F48 T121 [Polish R-10] — Color-blind friendly: classification + badges + delta identifiables en grayscale.
// Backend DOWN → all API calls mocked via page.route().
import { test, expect } from '@playwright/test'
import path from 'path'

const NOW_ISO = new Date().toISOString()
const MINUS_1M = new Date(Date.now() - 30 * 24 * 3600_000).toISOString()

const MOCK_ME = {
  id: 'user-1',
  email: 'pme-test@example.com',
  role: 'pme',
  account_id: 'ent-1',
  entreprise_id: 'ent-1',
  verified: true,
}

// Score 72 → classification "Bon"
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

const MOCK_HISTORY = {
  items: [
    { id: 'h2', combine: 72, solvabilite: 70, impact_vert: 74, subscores: null, methodologie_version: 1, computed_at: NOW_ISO, coherence_warning: false },
    { id: 'h1', combine: 68, solvabilite: 66, impact_vert: 70, subscores: null, methodologie_version: 1, computed_at: MINUS_1M, coherence_warning: false },
  ],
}

// 1 éligible + 1 non éligible
const MOCK_ELIGIBILITY = {
  items: [
    {
      code: 'boad_vert',
      label: 'BOAD Vert',
      status: 'eligible',
      primary_reason: 'Score combiné ≥ 60 et secteur éligible.',
      criteria: [],
      matching_offer_query: null,
      source_id: 'src-1',
      catalog_version: 1,
    },
    {
      code: 'sunref',
      label: 'SUNREF',
      status: 'not_eligible',
      primary_reason: 'Score ESG insuffisant (minimum 70 requis).',
      criteria: [],
      matching_offer_query: null,
      source_id: 'src-2',
      catalog_version: 1,
    },
  ],
  evaluated_at: NOW_ISO,
  catalog_version_max: 1,
}

const MOCK_RECOMMENDATIONS = { items: [], selected_subscores: [] }

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-a11y-color-${name}.png`,
  )
}

test.describe('Credit Score — Color-blind friendly (F48 T121 Polish R-10)', () => {
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

    // Simuler un filtre grayscale avant navigation (equivalent daltonisme total)
    await page.addStyleTag({ content: 'html { filter: grayscale(100%) !important; }' })
  })

  test('R-10-A : classification "Bon" lisible textuellement (pas uniquement par couleur)', async ({ page }) => {
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // La classification doit être exprimée en texte, pas seulement en couleur
    // ClassificationLabel rend "Bon" pour un score 72 (seuil 60-79)
    await expect(page.getByText('Bon')).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('01-grayscale-classification') })
  })

  test('R-10-B : badges éligibilité affichent "Éligible" / "Non éligible" en texte', async ({ page }) => {
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // Attendre que les badges soient visibles
    await expect(page.getByText('BOAD Vert')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('SUNREF')).toBeVisible({ timeout: 5000 })

    // Les statuts doivent être exprimés en texte (pas uniquement par couleur de badge)
    // EligibilityBadge rend le libellé "Éligible" ou "Non éligible"
    await expect(page.getByText('Éligible').first()).toBeVisible()
    await expect(page.getByText('Non éligible').first()).toBeVisible()

    await page.screenshot({ path: screenshotPath('02-grayscale-eligibility-badges') })
  })

  test('R-10-C : delta affiche le signe "+" ou "−" en texte en plus de la couleur', async ({ page }) => {
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // delta = 72 - 68 = +4 → le signe "+" doit être présent en texte
    // GaugeHero affiche deltaInfo.sign (+, −, ou vide) avant la valeur
    const deltaText = page.locator('p').filter({ hasText: /points vs précédent/ })
    await expect(deltaText).toBeVisible({ timeout: 8000 })

    // Le texte doit contenir "+" (signe positif textuel)
    const content = await deltaText.textContent()
    expect(content).toMatch(/[+−]/)

    await page.screenshot({ path: screenshotPath('03-grayscale-delta-sign') })
  })
})
