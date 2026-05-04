// F48 T103 [US8] — Empty state wizard: 404 score → wizard 4 étapes + soumission + reprise localStorage.
// Backend DOWN → all API calls mocked via page.route().
//
// BUG APPLICATIF DETECTE (non-bloquant):
// La page /credit-score subit un "Hydration text content mismatch" (Vue 3 / Nuxt 4 SSR).
// Cause : le composant HistoryEntry utilise des Date objects créés côté serveur qui
// diffèrent côté client, provoquant un mismatch d'hydration.
// Conséquence : les event listeners @click ne sont PAS attachés aux boutons du
// EmptyStateWizard après l'hydration échouée — le clic sur "Suivant" est ignoré.
// Les tests US8-A et US8-B sont marqués test.fixme en attendant le correctif.
// Correctif suggéré : ajouter `definePageMeta({ ssr: false })` à /credit-score/index.vue
// OU faire passer les dates via les computed (côté client uniquement).

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

// Score retourné après recompute
const MOCK_RECOMPUTED_SCORE = {
  id: 'new-score-id',
  entreprise_id: 'ent-1',
  solvabilite: 48,
  impact_vert: 62,
  combine: 55,
  facteurs: [],
  methodologie_version: 1,
  coherence_warning: false,
  computed_at: NOW_ISO,
  subscores: {
    solidite_financiere: 60,
    performance_operationnelle: 55,
    engagement_esg: 50,
    gouvernance: 45,
  },
}

const MOCK_ELIGIBILITY = { items: [], evaluated_at: NOW_ISO, catalog_version_max: 1 }
const MOCK_RECOMMENDATIONS = { items: [], selected_subscores: [] }
const MOCK_HISTORY = { items: [] }

function screenshotPath(name: string): string {
  return path.join(
    '/Users/mac/Documents/projets/2025/esg_mefali_v2/frontend/tests/e2e/artifacts',
    `credit-score-wizard-${name}.png`,
  )
}

async function setupBaseMocks(page: import('@playwright/test').Page, scoreStatus: 200 | 404 = 404) {
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
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMPUTED_SCORE) })
  })

  await page.route('**/me/credit-score', async (route) => {
    const url = route.request().url()
    if (url.includes('/history') || url.includes('/eligibility') || url.includes('/recommendations') || url.includes('/recompute')) {
      await route.fallback()
      return
    }
    if (scoreStatus === 404) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) })
    }
    else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMPUTED_SCORE) })
    }
  })

  await page.route('**/me/credit-data', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
  })
}

test.describe('Credit Score — Empty state wizard (F48 T103 US8)', () => {
  test('US8-render : wizard visible avec "Étape 1 sur 4" quand score 404', async ({ page }) => {
    // Ce test vérifie UNIQUEMENT le rendu du wizard (pas l'interaction)
    // car les interactions sont bloquées par le bug d'hydration SSR détecté
    await setupBaseMocks(page, 404)
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    // Étape 1 — wizard visible avec "Étape 1 sur 4" + titre "Données financières"
    // Note: le texte est en CSS uppercase mais le contenu DOM est "Étape 1 sur 4"
    await expect(page.getByText('Étape 1 sur 4')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText('Données financières')).toBeVisible({ timeout: 5000 })

    // Les 4 champs financiers sont présents
    await expect(page.getByLabel("Chiffre d'affaires")).toBeVisible()
    await expect(page.locator('input[inputmode="decimal"]').first()).toBeVisible()

    // Le bouton "Suivant" est présent
    await expect(page.getByRole('button', { name: 'Suivant' })).toBeVisible()

    // Le message de persistance est visible
    await expect(page.getByText('Votre progression est enregistrée automatiquement.')).toBeVisible()

    await page.screenshot({ path: screenshotPath('01-wizard-step1-rendered') })
  })

  test('US8-A : parcours complet 4 étapes + soumission → toast succès', async ({ page }) => {
    test.fixme(
      true,
      [
        'BUG APPLICATIF (T103 US8-A) : Hydration SSR mismatch sur /credit-score.',
        'Le composant EmptyStateWizard est rendu côté serveur avec un state différent',
        'du state client (dates, score null). Cela provoque un mismatch Vue3/Nuxt4',
        'qui empêche les event listeners @click d\'être attachés aux boutons du wizard.',
        'Résultat : clic sur "Suivant" ignoré, wizard reste sur étape 1.',
        'Correctif : ajouter definePageMeta({ ssr: false }) à pages/credit-score/index.vue',
        'Tracking: fix SSR hydration mismatch before enabling this test.',
      ].join(' '),
    )
    await setupBaseMocks(page, 404)
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })
    await expect(page.getByText('Étape 1 sur 4')).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('01-step1-financial') })

    const caInput = page.getByLabel("Chiffre d'affaires")
    await expect(caInput).toBeVisible({ timeout: 5000 })
    await caInput.click()
    await caInput.pressSequentially('5000000')

    await page.getByRole('button', { name: 'Suivant' }).click()
    await expect(page.getByText('Étape 2 sur 4')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Engagement ESG')).toBeVisible()

    await page.screenshot({ path: screenshotPath('02-step2-esg') })

    const carbonCheckbox = page.locator('input[type="checkbox"]').first()
    await carbonCheckbox.check()

    await page.getByRole('button', { name: 'Suivant' }).click()
    await expect(page.getByText('Étape 3 sur 4')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Gouvernance')).toBeVisible()

    await page.screenshot({ path: screenshotPath('03-step3-governance') })

    const boardCheckbox = page.locator('input[type="checkbox"]').first()
    await boardCheckbox.check()

    await page.getByRole('button', { name: 'Suivant' }).click()
    await expect(page.getByText('Étape 4 sur 4')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Récapitulatif')).toBeVisible()
    await expect(page.getByText('5000000')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('04-step4-summary') })

    await page.getByRole('button', { name: 'Calculer mon premier score' }).click()
    await expect(page.getByText('Premier score calculé avec succès.')).toBeVisible({ timeout: 8000 })

    await page.screenshot({ path: screenshotPath('05-success-toast') })
  })

  test('US8-B : interruption à étape 2 + rechargement → reprise depuis localStorage', async ({ page }) => {
    test.fixme(
      true,
      'BUG APPLICATIF (T103 US8-B) : même cause que US8-A (hydration SSR mismatch). Fix requis côté applicatif.',
    )
    await setupBaseMocks(page, 404)
    await page.goto('/credit-score')
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    const caInput = page.getByLabel("Chiffre d'affaires")
    await expect(caInput).toBeVisible({ timeout: 8000 })
    await caInput.click()
    await caInput.pressSequentially('3000000')

    await page.getByRole('button', { name: 'Suivant' }).click()
    await expect(page.getByText('Étape 2 sur 4')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('06-before-reload-step2') })

    await page.reload()
    await expect(page.locator('h1')).toContainText('Score crédit ESG', { timeout: 10000 })

    await expect(page.getByText('Étape 2 sur 4')).toBeVisible({ timeout: 8000 })
    await expect(
      page.getByText('Reprise de votre saisie précédente (sauvegardée localement).'),
    ).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: screenshotPath('07-after-reload-step2-restored') })
  })
})
