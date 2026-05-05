// F51 T101 — A11y E2E : axe-core sur /matching ; charts F40 ont aria-label
// + tableau caché (data table fallback).

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const NOW_ISO = new Date().toISOString()
const PROJET_ID = 'projet-a11y-1'

const MOCK_ME = {
  id: 'user-1',
  email: 'pme-test@example.com',
  role: 'pme',
  account_id: 'ent-1',
  entreprise_id: 'ent-1',
  verified: true,
}

function makeOffres(n: number) {
  const items = []
  for (let i = 0; i < n; i++) {
    items.push({
      offre_id: `offre-${i}`,
      type: i % 2 === 0 ? 'subvention' : 'pret',
      title: `Offre ${i} — Solaire toiture`,
      issuer: `Bailleur ${i % 3}`,
      score: 90 - i * 5,
      gap_count: i,
      montant_min: { amount: '5000', currency: 'EUR' },
      montant_max: { amount: '200000', currency: 'EUR' },
      duree_max_mois: 60,
      country_codes: ['CIV'],
      reasons_top: ['secteur compatible', 'taille PME'],
      created_at: NOW_ISO,
    })
  }
  return { items, projet_id: PROJET_ID, total: n }
}

const MOCK_LIST = makeOffres(8)

async function mockApi(page: import('@playwright/test').Page) {
  await page.route('**/me', async (route) => {
    const url = route.request().url()
    if (url.includes('/me/projets')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ME),
    })
  })
  await page.route('**/me/projets/*/matching*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_LIST),
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
      `[a11y][matching ${label}] violations:`,
      JSON.stringify(blocking, null, 2),
    )
  }
  expect(blocking, `axe a11y violations on /matching ${label}`).toEqual([])
}

test.describe('F51 T101 — /matching a11y', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('liste matching — 0 violation serious/critical', async ({ page }) => {
    await page.goto(`/matching?projet=${PROJET_ID}`)
    await expect(page.getByText(/Trouvez votre financement/i)).toBeVisible({
      timeout: 10000,
    })
    await runAxe(page, 'list-view')
  })

  test('charts ont un libellé accessible (aria-label ou title)', async ({ page }) => {
    await page.goto(`/matching?projet=${PROJET_ID}`)
    await expect(page.getByText(/Trouvez votre financement/i)).toBeVisible({
      timeout: 10000,
    })
    const canvases = page.locator('canvas, svg[role="img"], [role="img"]')
    const count = await canvases.count()
    for (let i = 0; i < count; i++) {
      const el = canvases.nth(i)
      const labelled = await el.evaluate((node) => {
        const e = node as HTMLElement
        return Boolean(
          e.getAttribute('aria-label') ||
            e.getAttribute('aria-labelledby') ||
            e.getAttribute('title') ||
            e.querySelector('title'),
        )
      })
      expect(
        labelled,
        `chart #${i} sans libellé accessible (aria-label/aria-labelledby/title)`,
      ).toBe(true)
    }
  })
})
