// F52 NFR — Audit accessibilité (axe-core) sur /notifications et /parametres/*.
// Le test exécute axe-core injecté manuellement via CDN si la dépendance npm
// n'est pas disponible — fallback sans dépendance dure.
import { test, expect, type Page } from '@playwright/test'

const PME_EMAIL = process.env.E2E_PME_EMAIL ?? ''
const PME_PASSWORD = process.env.E2E_PME_PASSWORD ?? ''

interface AxeNode {
  html: string
  target: string[]
}
interface AxeViolation {
  id: string
  impact: 'minor' | 'moderate' | 'serious' | 'critical' | null
  description: string
  help: string
  nodes: AxeNode[]
}
interface AxeResult {
  violations: AxeViolation[]
}

async function login(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByLabel(/Email/i).fill(PME_EMAIL)
  await page.getByLabel(/Mot de passe/i).fill(PME_PASSWORD)
  await page.getByRole('button', { name: /Connexion|Se connecter/i }).click()
  await page.waitForLoadState('networkidle')
}

async function runAxe(page: Page): Promise<AxeResult> {
  await page.addScriptTag({
    url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js',
  })
  const result = await page.evaluate(async () => {
    const a = (window as unknown as {
      axe: { run: (ctx: Document, opts: unknown) => Promise<AxeResult> }
    }).axe
    return await a.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    })
  })
  return result
}

function formatViolations(v: AxeViolation[]): string {
  return v
    .map((x) => `[${x.impact ?? 'n/a'}] ${x.id} — ${x.help} (${x.nodes.length} nodes)`)
    .join('\n')
}

test.describe('F52 NFR — Accessibilité axe-core', () => {
  test.skip(!PME_EMAIL || !PME_PASSWORD, 'E2E_PME_EMAIL/PASSWORD non définis')

  const routes = [
    '/notifications',
    '/parametres/profil',
    '/parametres/notifications',
    '/parametres/consents',
    '/parametres/securite',
    '/parametres/donnees',
    '/parametres/suppression',
  ]

  for (const route of routes) {
    test(`pas de violation critical/serious sur ${route}`, async ({ page }) => {
      await login(page)
      await page.goto(route)
      await page.waitForLoadState('networkidle')
      const { violations } = await runAxe(page)
      const blocking = violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious',
      )
      expect(blocking, `violations bloquantes:\n${formatViolations(blocking)}`).toEqual([])
    })
  }
})
