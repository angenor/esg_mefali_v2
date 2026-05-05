// F48 [US3] T060+T061 — Eligibility badges: 3 items, statuses, modal detail.
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

const MOCK_RECOMMENDATIONS = {
  items: [],
  selected_subscores: [],
}

const MOCK_ELIGIBILITY = {
  items: [
    {
      code: 'boad_vert',
      label: 'BOAD Vert',
      description: 'Ligne verte BOAD',
      status: 'eligible',
      primary_reason: 'Score crédit ≥ 60',
      criteria: [
        {
          code: 'c1',
          label: 'Score crédit minimum',
          threshold: '60',
          actual: '72',
          met: true,
          blocking: true,
        },
      ],
      matching_offer_query: 'code=boad_vert',
      source_id: 'src-boad',
      version: 1,
      valid_from: '2024-01-01',
      valid_to: null,
    },
    {
      code: 'sunref',
      label: 'SUNREF',
      description: 'Programme SUNREF AFD',
      status: 'eligible',
      primary_reason: 'Secteur agro éligible',
      criteria: [
        {
          code: 'c2',
          label: 'Secteur éligible',
          threshold: 'Agro / Énergie',
          actual: 'Agriculture',
          met: true,
          blocking: true,
        },
      ],
      matching_offer_query: 'code=sunref',
      source_id: 'src-sunref',
      version: 1,
      valid_from: '2024-01-01',
      valid_to: null,
    },
    {
      code: 'ecobank',
      label: 'Ecobank Green',
      description: 'Prêt vert Ecobank',
      status: 'not_eligible',
      primary_reason: 'Score insuffisant pour ce dispositif',
      criteria: [
        {
          code: 'c3',
          label: 'Score crédit minimum',
          threshold: '80',
          actual: '72',
          met: false,
          blocking: true,
        },
      ],
      matching_offer_query: 'code=ecobank_green',
      source_id: 'src-ecobank',
      version: 1,
      valid_from: '2024-01-01',
      valid_to: null,
    },
  ],
  evaluated_at: NOW_ISO,
  catalog_version_max: 1,
}

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-eligibility-${name}.png`,
  )
}

async function setupMocks(page: import('@playwright/test').Page) {
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
}

test.describe('Credit Score — Eligibility badges (F48 US3)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await page.goto('/credit-score')
    // Le sous-titre de la page contient déjà "éligibilité aux financements verts" → cibler le h2 de section.
    await expect(
      page.getByRole('heading', { name: 'Éligibilité aux financements verts' }),
    ).toBeVisible({ timeout: 10000 })
  })

  test('US3-A : 3 badges rendus', async ({ page }) => {
    // All three badge labels visible
    await expect(page.getByText('BOAD Vert')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('SUNREF')).toBeVisible()
    await expect(page.getByText('Ecobank Green')).toBeVisible()

    await page.screenshot({ path: screenshotPath('01-three-badges') })
  })

  test('US3-B : 2 « Éligible », 1 « Non éligible »', async ({ page }) => {
    await expect(page.getByText('BOAD Vert')).toBeVisible({ timeout: 8000 })

    // Count "Éligible" occurrences (exact text in status label)
    const eligibleLabels = page.getByText('Éligible', { exact: true })
    await expect(eligibleLabels).toHaveCount(2, { timeout: 5000 })

    // Count "Non éligible" occurrences
    const notEligibleLabels = page.getByText('Non éligible', { exact: true })
    await expect(notEligibleLabels).toHaveCount(1, { timeout: 5000 })

    await page.screenshot({ path: screenshotPath('02-status-count') })
  })

  test('US3-C : clic badge ecobank → modal avec tableau critères + bouton Fermer', async ({ page }) => {
    await expect(page.getByText('Ecobank Green')).toBeVisible({ timeout: 8000 })

    // Click the Ecobank badge (not_eligible)
    const ecobankBadge = page.locator('button[data-code="ecobank"]')
    await expect(ecobankBadge).toBeVisible()
    await ecobankBadge.click()

    // Modal should open with criteria table
    await expect(page.getByText('Critères d\'éligibilité')).toBeVisible({ timeout: 5000 })

    // The close button should be present
    const closeBtn = page.getByRole('button', { name: 'Fermer' })
    await expect(closeBtn).toBeVisible()

    // NOT eligible → "Voir les offres compatibles" link should NOT appear
    await expect(page.getByText('Voir les offres compatibles')).not.toBeVisible()

    await page.screenshot({ path: screenshotPath('03-ecobank-modal') })

    // Close the modal
    await closeBtn.click()
    await expect(page.getByText('Critères d\'éligibilité')).not.toBeVisible({ timeout: 3000 })
  })

  test('US3-D : clic badge boad_vert (éligible) → modal contient « Voir les offres compatibles »', async ({ page }) => {
    await expect(page.getByText('BOAD Vert')).toBeVisible({ timeout: 8000 })

    const boadBadge = page.locator('button[data-code="boad_vert"]')
    await expect(boadBadge).toBeVisible()
    await boadBadge.click()

    // Modal opens
    await expect(page.getByText('Critères d\'éligibilité')).toBeVisible({ timeout: 5000 })

    // Eligible → "Voir les offres compatibles" link present
    await expect(page.getByText('Voir les offres compatibles')).toBeVisible({ timeout: 3000 })

    // Also close button present
    await expect(page.getByRole('button', { name: 'Fermer' })).toBeVisible()

    await page.screenshot({ path: screenshotPath('04-boad-modal-eligible') })
  })
})
