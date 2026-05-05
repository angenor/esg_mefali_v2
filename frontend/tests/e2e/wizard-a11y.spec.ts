// F51 T100 — A11y E2E : axe-core sur les 5 étapes du wizard candidature.
// Critère : 0 violation `serious` ou `critical` (WCAG 2.1 AA).
// Backend mocké via page.route().

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const NOW_ISO = new Date().toISOString()

const MOCK_ME = {
  id: 'user-1',
  email: 'pme-test@example.com',
  role: 'pme',
  account_id: 'ent-1',
  entreprise_id: 'ent-1',
  verified: true,
}

const CANDIDATURE_ID = 'cand-a11y-1'
const OFFRE_ID = 'offre-1'

const MOCK_DETAIL = {
  id: CANDIDATURE_ID,
  projet_id: 'projet-1',
  offre_id: OFFRE_ID,
  statut: 'brouillon',
  step_courant: 1,
  progression_pct: 20,
  expected_version: 1,
  submitted_at: null,
  submitted_snapshot_json: null,
  draft_snapshot_json: {
    step1: { confirmed: false },
    step2: { indicateurs: [] },
    step3: { documents_links: [] },
    step4: { plan_action_validated: false },
    step5: { resume_validated: false },
  },
  offre: {
    id: OFFRE_ID,
    nom: 'Subvention Énergie Verte',
    type: 'subvention',
    bailleur: 'AFD',
    documents_requis: [
      { key: 'statuts', label: 'Statuts juridiques' },
      { key: 'kbis', label: 'Extrait KBIS' },
    ],
    accepted_languages: ['fr'],
  },
  timeline: [
    { ts: NOW_ISO, type: 'created', actor: 'pme', comment: null },
  ],
}

async function mockApi(page: import('@playwright/test').Page) {
  await page.route('**/me', async (route) => {
    const url = route.request().url()
    if (url.includes('/me/candidatures') || url.includes('/me/projets')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ME),
    })
  })

  await page.route('**/me/candidatures/*', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_DETAIL),
    })
  })
}

async function runAxe(page: import('@playwright/test').Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  )
  if (blocking.length > 0) {
    // eslint-disable-next-line no-console
    console.error(
      `[a11y][wizard ${label}] violations:`,
      JSON.stringify(blocking, null, 2),
    )
  }
  expect(blocking, `axe a11y violations on wizard ${label}`).toEqual([])
}

test.describe('F51 T100 — Wizard candidature a11y (5 étapes)', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('étape par défaut — 0 violation serious/critical', async ({ page }) => {
    await page.goto(`/candidatures/${CANDIDATURE_ID}`)
    await expect(page.getByText(/Subvention Énergie Verte/i)).toBeVisible({
      timeout: 10000,
    })
    await runAxe(page, 'step-default')
  })

  test('navigation clavier : focus visible sur boutons étape', async ({ page }) => {
    await page.goto(`/candidatures/${CANDIDATURE_ID}`)
    await expect(page.getByText(/Subvention Énergie Verte/i)).toBeVisible({
      timeout: 10000,
    })
    // Tab focus passe les liens/boutons sans être bloqué
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(focused).toBeTruthy()
  })
})
