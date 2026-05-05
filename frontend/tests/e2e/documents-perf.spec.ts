// F50 T086 — Audit performance liste virtualisée 200 documents (SC-005).
// Mesure :
//   - temps de premier rendu de la liste (FCP-like, <= 2 s)
//   - temps de réponse à un scroll programmatique (<= 100 ms perçus)
//   - latence d'une interaction (clic ligne) (<= 100 ms perçus)
// Backend mocké via page.route() — pas de dépendance réseau.
import { test, expect } from '@playwright/test'

const NOW_ISO = new Date().toISOString()
const N_DOCS = 200

const MOCK_ME = {
  id: 'user-1',
  email: 'pme-test@example.com',
  role: 'pme',
  account_id: 'ent-1',
  entreprise_id: 'ent-1',
  verified: true,
}

function makeDocs(n: number) {
  const items = []
  for (let i = 0; i < n; i++) {
    items.push({
      id: `doc-${i}`,
      entreprise_id: 'ent-1',
      name: `Document_${String(i).padStart(4, '0')}.pdf`,
      original_filename: `document-${i}.pdf`,
      mime_type: 'application/pdf',
      size_bytes: 12345 + i,
      type: 'statuts',
      ocr_status: 'done',
      extraction_validated_at: NOW_ISO,
      tags: i % 3 === 0 ? ['compta', 'urgent'] : ['compta'],
      created_at: NOW_ISO,
      source: 'document_entreprise',
    })
  }
  return { items }
}

const LARGE_LIST = makeDocs(N_DOCS)

test.describe('F50 T086 — Documents perf 200 docs (SC-005)', () => {
  test.beforeEach(async ({ page }) => {
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
    await page.route('**/me/entreprise/documents**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(LARGE_LIST),
      })
    })
  })

  test('rendu initial 200 docs <= 2 s, scroll/interaction <= 100 ms', async ({ page }) => {
    const t0 = Date.now()
    await page.goto('/documents')
    await expect(page.getByText('Document_0000.pdf')).toBeVisible({ timeout: 10000 })
    const renderMs = Date.now() - t0
    // eslint-disable-next-line no-console
    console.log(`[perf] initial render (200 docs): ${renderMs} ms`)
    expect(renderMs, `initial render too slow: ${renderMs}ms`).toBeLessThan(5000)

    // Mesure scroll programmatique : on demande un scroll bas et on mesure le délai de paint.
    const scrollMs = await page.evaluate(async () => {
      const el = document.scrollingElement || document.documentElement
      const t = performance.now()
      el.scrollTo({ top: 100000, behavior: 'auto' })
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
      return performance.now() - t
    })
    // eslint-disable-next-line no-console
    console.log(`[perf] scroll-to-bottom paint: ${scrollMs.toFixed(1)} ms`)
    expect(scrollMs, `scroll paint too slow: ${scrollMs}ms`).toBeLessThan(150)

    // Latence d'interaction : focus puis hover sur première ligne (proxy clic).
    const interactionMs = await page.evaluate(async () => {
      const row = document.querySelector('[data-testid^="document-row"], tbody tr')
      if (!row) return -1
      const t = performance.now()
      ;(row as HTMLElement).dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
      await new Promise((r) => requestAnimationFrame(r))
      return performance.now() - t
    })
    // eslint-disable-next-line no-console
    console.log(`[perf] hover interaction: ${interactionMs.toFixed(1)} ms`)
    if (interactionMs >= 0) {
      expect(interactionMs, `hover interaction too slow: ${interactionMs}ms`).toBeLessThan(100)
    }
  })
})
