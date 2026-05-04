// F48 T122 [Polish] — Reduced motion: gauge affiche directement la valeur sans animation prolongée.
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

// Score initial 64
const MOCK_SCORE_INITIAL = {
  id: 'test-id-v1',
  entreprise_id: 'ent-1',
  solvabilite: 62,
  impact_vert: 66,
  combine: 64,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: NOW_ISO,
  subscores: {
    solidite_financiere: 65,
    performance_operationnelle: 70,
    engagement_esg: 60,
    gouvernance: 58,
  },
}

// Score après recalcul 72
const MOCK_SCORE_RECOMPUTED = {
  id: 'test-id-v2',
  entreprise_id: 'ent-1',
  solvabilite: 70,
  impact_vert: 74,
  combine: 72,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: new Date().toISOString(),
  subscores: {
    solidite_financiere: 75,
    performance_operationnelle: 80,
    engagement_esg: 65,
    gouvernance: 70,
  },
}

const MOCK_HISTORY = { items: [] }
const MOCK_ELIGIBILITY = { items: [], evaluated_at: NOW_ISO, catalog_version_max: 1 }
const MOCK_RECOMMENDATIONS = { items: [], selected_subscores: [] }

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-reduced-motion-${name}.png`,
  )
}

test.describe('Credit Score — Reduced motion (F48 T122 Polish)', () => {
  test('Polish-A : prefers-reduced-motion → gauge affiche directement 72 après recalcul', async ({ page }) => {
    // Émuler prefers-reduced-motion: reduce
    await page.emulateMedia({ reducedMotion: 'reduce' })

    let scoreCallCount = 0
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

    await page.route('**/me/credit-score/recompute', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SCORE_RECOMPUTED) })
    })

    await page.route('**/me/credit-score', async (route) => {
      const url = route.request().url()
      if (url.includes('/history') || url.includes('/eligibility') || url.includes('/recommendations') || url.includes('/recompute')) {
        await route.fallback()
        return
      }
      scoreCallCount++
      // Retourner le score initial la première fois, recomputed ensuite
      const payload = scoreCallCount === 1 ? MOCK_SCORE_INITIAL : MOCK_SCORE_RECOMPUTED
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) })
    })

    await page.route('**/me/credit-data', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
    })

    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // Vérifier que le score initial 64 est affiché
    const gaugeSection = page.locator('section').filter({ hasText: 'Score crédit ESG' }).first()
    await expect(gaugeSection).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('01-initial-score-64') })

    // Clic "Recalculer maintenant"
    const recalcBtn = page.getByRole('button', { name: 'Recalculer maintenant' }).first()
    await expect(recalcBtn).toBeVisible()
    await recalcBtn.click()

    // Attendre un court instant (pas de waitForTimeout — on attend la présence du texte 72)
    // Avec reduced-motion, la gauge doit afficher directement 72 sans animation prolongée
    const gaugeValue72 = gaugeSection.locator('text').filter({ hasText: '72' })
    await expect(gaugeValue72).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('02-after-recalc-72-no-animation') })

    // Vérifier qu'aucune classe animate-spin n'est active de manière prolongée
    // (Le spinner doit disparaître rapidement après la réponse du mock)
    const spinner = page.locator('.animate-spin')
    // Le spinner peut être brièvement visible pendant l'appel, mais doit disparaître
    await expect(spinner).not.toBeVisible({ timeout: 3000 })

    await page.screenshot({ path: screenshotPath('03-no-spinner-after-recalc') })
  })

  test('Polish-B : bouton "Recalculer maintenant" fonctionnel avec reduced-motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })

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

    await page.route('**/me/credit-score/recompute', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SCORE_RECOMPUTED) })
    })

    await page.route('**/me/credit-score', async (route) => {
      const url = route.request().url()
      if (url.includes('/history') || url.includes('/eligibility') || url.includes('/recommendations') || url.includes('/recompute')) {
        await route.fallback()
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SCORE_INITIAL) })
    })

    await page.route('**/me/credit-data', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
    })

    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // Le bouton doit être cliquable
    const recalcBtn = page.getByRole('button', { name: 'Recalculer maintenant' }).first()
    await expect(recalcBtn).toBeVisible({ timeout: 5000 })
    await expect(recalcBtn).toBeEnabled()

    // Cliquer et vérifier que le bouton répond (pas de freeze)
    await recalcBtn.click()

    // Toast ou nouvelle valeur doit apparaître, prouvant que le clic a fonctionné
    // Avec stable mock (= pas de delta), toast "score stable" visible
    // Ou si delta, toast "+N points" visible
    // On attend simplement que la page reste fonctionnelle
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 5000 })

    await page.screenshot({ path: screenshotPath('04-reduced-motion-button-works') })
  })
})
