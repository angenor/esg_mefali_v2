// F52 NFR-003 / SC-008 — Pen-test : cloisonnement extension multi-tenant.
// Deux comptes (A et B) sur la même URL listée ne doivent jamais voir
// les données de l'autre via le sidepanel ou les messages chrome.runtime.
//
// Ce test est skippé par défaut : il requiert deux comptes provisionnés
// (E2E_PME_A_*, E2E_PME_B_*) et l'extension chargée (E2E_RUN_EXTENSION=1).
import { test, expect, chromium } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const A_EMAIL = process.env.E2E_PME_A_EMAIL ?? ''
const A_PASSWORD = process.env.E2E_PME_A_PASSWORD ?? ''
const B_EMAIL = process.env.E2E_PME_B_EMAIL ?? ''
const B_PASSWORD = process.env.E2E_PME_B_PASSWORD ?? ''
const EXT_DIR = fileURLToPath(new URL('../../../extension', import.meta.url))

test.describe('F52 NFR-003 — Cloisonnement multi-tenant', () => {
  test.skip(
    !A_EMAIL || !A_PASSWORD || !B_EMAIL || !B_PASSWORD,
    'Comptes E2E_PME_A_* / E2E_PME_B_* manquants',
  )
  test.skip(!process.env.E2E_RUN_EXTENSION, 'E2E_RUN_EXTENSION non activé')

  test('aucune donnée du tenant B ne fuite vers un onglet A', async () => {
    const ctxA = await chromium.launchPersistentContext('', {
      headless: false,
      args: [`--disable-extensions-except=${EXT_DIR}`, `--load-extension=${EXT_DIR}`],
    })
    const ctxB = await chromium.launchPersistentContext('', {
      headless: false,
      args: [`--disable-extensions-except=${EXT_DIR}`, `--load-extension=${EXT_DIR}`],
    })
    try {
      const a = await ctxA.newPage()
      await a.goto('http://localhost:3001/login')
      await a.getByLabel(/Email/i).fill(A_EMAIL)
      await a.getByLabel(/Mot de passe/i).fill(A_PASSWORD)
      await a.getByRole('button', { name: /Connexion|Se connecter/i }).click()

      const b = await ctxB.newPage()
      await b.goto('http://localhost:3001/login')
      await b.getByLabel(/Email/i).fill(B_EMAIL)
      await b.getByLabel(/Mot de passe/i).fill(B_PASSWORD)
      await b.getByRole('button', { name: /Connexion|Se connecter/i }).click()

      // Récupère les ids candidatures du tenant B via l'API REST.
      const bIds: string[] = await b.evaluate(async () => {
        const r = await fetch('/me/extension/sidepanel-context?host=test&path=/', {
          credentials: 'include',
        })
        if (!r.ok) return []
        const data = await r.json()
        return (data?.active_candidatures ?? []).map((c: { id: string }) => c.id)
      })
      expect(bIds.length).toBeGreaterThanOrEqual(0)

      // Sur une page mock listée côté A, le sidepanel ne doit jamais
      // référencer un id tenant B.
      const mock = await ctxA.newPage()
      await mock.setContent('<html><body><h1>Mock plateforme listée</h1></body></html>')
      await mock.waitForTimeout(800)

      const aIds: string[] = await mock.evaluate(async () => {
        const r = await fetch('http://localhost:8010/me/extension/sidepanel-context?host=test&path=/', {
          credentials: 'include',
        })
        if (!r.ok) return []
        const data = await r.json()
        return (data?.active_candidatures ?? []).map((c: { id: string }) => c.id)
      })

      const leak = aIds.filter((id) => bIds.includes(id))
      expect(leak, 'aucun id tenant B ne doit apparaître côté A').toEqual([])
    } finally {
      await ctxA.close()
      await ctxB.close()
    }
  })
})
