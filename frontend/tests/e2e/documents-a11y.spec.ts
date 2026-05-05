// F50 T085 — A11y axe-core sur 4 vues documents :
//   1) liste vide   2) liste peuplée   3) DocPreviewDrawer ouvert   4) OcrSummarySheet ouvert
// Gate CI : zéro violation `serious` ou `critical` (SC-009, WCAG 2.1 AA).
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

function makeDoc(i: number, ocr_status = 'done', validated = true) {
  return {
    id: `doc-${i}`,
    entreprise_id: 'ent-1',
    name: `Document ${i}.pdf`,
    original_filename: `document-${i}.pdf`,
    mime_type: 'application/pdf',
    size_bytes: 12345,
    type: 'statuts',
    ocr_status,
    ocr_error: null,
    uploaded_by: 'user-1',
    created_at: NOW_ISO,
    content_sha256: `sha-${i}`,
    extraction_payload: {
      fields: [
        { key: 'effectif', label: 'Effectif', value: 12, confidence: 0.95 },
        { key: 'raison_sociale', label: 'Raison sociale', value: 'ACME SARL', confidence: 0.92 },
      ],
    },
    extraction_validated_at: validated ? NOW_ISO : null,
    extraction_validated_by: validated ? 'user-1' : null,
    linked_projets: [],
    tags: ['compta'],
    deleted_at: null,
    purge_scheduled_at: null,
  }
}

const EMPTY_LIST = { items: [] }
const POPULATED_LIST = { items: [makeDoc(1), makeDoc(2, 'processing', false), makeDoc(3)] }
const DOC_DETAIL = makeDoc(1, 'done', false) // non validé pour ouvrir OcrSummarySheet

async function mockApi(page: import('@playwright/test').Page, listPayload: unknown) {
  await page.route('**/me', async (route) => {
    const url = route.request().url()
    if (url.includes('/documents') || url.includes('/entreprise')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ME),
    })
  })

  await page.route('**/me/entreprise/documents/*/preview-url**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ url: 'about:blank', expires_at: NOW_ISO }),
    })
  })

  await page.route('**/me/entreprise/documents/*', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(DOC_DETAIL),
    })
  })

  await page.route('**/me/entreprise/documents**', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(listPayload),
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
      `[a11y][${label}] violations serious/critical:`,
      JSON.stringify(blocking, null, 2),
    )
  }
  expect(blocking, `axe a11y violations on ${label}`).toEqual([])
}

test.describe('F50 T085 — Documents a11y (axe-core)', () => {
  test('vue 1 : liste vide — 0 violation serious/critical', async ({ page }) => {
    await mockApi(page, EMPTY_LIST)
    await page.goto('/documents')
    await expect(page.getByText(/Téléverser/i).first()).toBeVisible({ timeout: 10000 })
    await runAxe(page, 'empty-list')
  })

  test('vue 2 : liste peuplée — 0 violation serious/critical', async ({ page }) => {
    await mockApi(page, POPULATED_LIST)
    await page.goto('/documents')
    await expect(page.getByText('Document 1.pdf')).toBeVisible({ timeout: 10000 })
    await runAxe(page, 'populated-list')
  })

  test('vue 3 : DocPreviewDrawer ouvert — 0 violation serious/critical', async ({ page }) => {
    await mockApi(page, POPULATED_LIST)
    await page.goto('/documents')
    await expect(page.getByText('Document 1.pdf')).toBeVisible({ timeout: 10000 })
    // Ouvre le drawer via clic sur le nom (DocumentTable expose le déclencheur).
    await page.getByText('Document 1.pdf').click()
    // Drawer présent : on attend un rôle dialog ou un focus piégé.
    const dialog = page.getByRole('dialog').first()
    await expect(dialog).toBeVisible({ timeout: 5000 })
    await runAxe(page, 'preview-drawer-open')
  })

  test('vue 4 : OcrSummarySheet ouvert — 0 violation serious/critical', async ({ page }) => {
    // Force un doc non validé en tête de liste pour faire apparaître l'action « Vérifier ».
    const list = { items: [{ ...DOC_DETAIL, extraction_validated_at: null }, makeDoc(2)] }
    await mockApi(page, list)
    await page.goto('/documents')
    await expect(page.getByRole('button', { name: /Vérifier/i }).first()).toBeVisible({
      timeout: 10000,
    })
    await page.getByRole('button', { name: /Vérifier/i }).first().click()
    await expect(page.getByRole('dialog').first()).toBeVisible({ timeout: 5000 })
    await runAxe(page, 'ocr-summary-sheet-open')
  })
})
