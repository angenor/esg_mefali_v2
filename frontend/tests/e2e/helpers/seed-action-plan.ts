// F45 T019 — Helper E2E pour seeder un plan d'action complet (login + scoring +
// generate). Usage : `await seedPmeWithActionPlan(page, { stepsCount: 5 })`.
//
// Variables d'environnement attendues (alignées avec le pattern dashboard) :
// - PLAYWRIGHT_BACKEND_URL : URL backend (par défaut http://localhost:8010)
// - PLAYWRIGHT_E2E_EMAIL / PLAYWRIGHT_E2E_PASSWORD : credentials d'un compte
//   PME de test pré-provisionné (cf. backend/tests/conftest_e2e.py).
import type { Page } from "@playwright/test"

export interface SeedOptions {
  stepsCount?: number
  withScoring?: boolean
  withGaps?: boolean
  horizon?: 6 | 12 | 24
}

const BACKEND =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8010"

async function login(page: Page): Promise<void> {
  const email = process.env.PLAYWRIGHT_E2E_EMAIL ?? "pme.e2e@example.com"
  const password = process.env.PLAYWRIGHT_E2E_PASSWORD ?? "Test1234!"
  await page.goto("/auth/login")
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/(dashboard|chat|onboarding)/)
}

export async function seedPmeWithActionPlan(
  page: Page,
  opts: SeedOptions = {},
): Promise<void> {
  const { withScoring = true, withGaps = true, horizon = 12 } = opts
  await login(page)
  if (!withScoring) return
  // Trigger scoring + (optionnel) gaps via fixtures backend.
  const ctx = page.context()
  await ctx.request.post(`${BACKEND}/me/scoring/calculate`, {
    headers: { "content-type": "application/json" },
  })
  if (!withGaps) return
  await ctx.request.post(`${BACKEND}/me/action-plan/generate`, {
    params: { horizon: String(horizon) },
  })
}
