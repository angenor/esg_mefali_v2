/**
 * Helper E2E auth — résout les bugs 1A (SSE keepalive ≠ networkidle)
 * et 1B (CSRF middleware bloque les POST mutants sans X-CSRF-Token).
 *
 * Usage côté tests `request` (API only) :
 *
 *     const { headers } = await registerLoginCsrf(request)
 *     const r = await request.post('/me/chat/threads', {
 *       headers,
 *       data: { ... },
 *     })
 *
 * Usage côté tests `page` (UI) :
 *
 *     await registerThenLoginViaUI(page, request)
 *     await page.goto('/chat')
 *     await waitForPageReady(page) // évite networkidle qui timeout sur SSE
 */
import type { APIRequestContext, Page } from '@playwright/test'

export interface LoginResult {
  email: string
  password: string
  headers: Record<string, string>
}

const DEFAULT_API_BASE = process.env.E2E_API_BASE || 'http://localhost:8010'
const DEFAULT_PASSWORD = 'E2eTestPass123!'

/**
 * Register + login via l'API et retourne les headers CSRF prêts à utiliser
 * pour les POST/DELETE/PATCH/PUT mutants.
 *
 * Le `APIRequestContext` Playwright partage les cookies entre appels — donc
 * `mefali_at`, `mefali_rt`, `mefali_csrf` sont stockés et envoyés
 * automatiquement par les requêtes suivantes. Mais le CSRF middleware backend
 * exige aussi le header `X-CSRF-Token` à matcher : on l'extrait du
 * storageState après login et on le retourne.
 */
export async function registerLoginCsrf(
  request: APIRequestContext,
  options?: { email?: string; password?: string; apiBase?: string },
): Promise<LoginResult> {
  const apiBase = options?.apiBase ?? DEFAULT_API_BASE
  const email = options?.email ?? `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@example.com`
  const password = options?.password ?? DEFAULT_PASSWORD

  await request.post(`${apiBase}/auth/register`, {
    data: { email, password },
  })
  // Login peut échouer si register déjà passé pour un email recyclé — on
  // tente quand même login pour récupérer le cookie CSRF frais.
  await request.post(`${apiBase}/auth/login`, {
    data: { email, password },
  })

  const state = await request.storageState()
  const cookie = state.cookies.find((c) => c.name === 'mefali_csrf')
  const headers: Record<string, string> = {}
  if (cookie?.value) {
    headers['X-CSRF-Token'] = cookie.value
  }
  return { email, password, headers }
}

/**
 * Login via l'UI Nuxt et attend la redirection post-login. Utilise les
 * locators stables `#login-email`, `#login-pwd`, button submit. Doit être
 * appelé après `registerLoginCsrf` (ou un register manuel).
 *
 * Important : on évite `waitForLoadState('networkidle')` car le frontend
 * ouvre une SSE permanente (`/me/notifications/stream`) qui empêche le
 * réseau d'être idle. On attend une URL post-login OU un selector stable.
 */
export async function loginViaUI(
  page: Page,
  email: string,
  password: string,
  options?: { frontUrl?: string },
): Promise<void> {
  const frontUrl = options?.frontUrl ?? process.env.E2E_FRONT_URL ?? 'http://localhost:3001'
  await page.goto(`${frontUrl}/login`)

  // Attendre l'hydration : visibility de l'input + visibility du button
  // submit + 500 ms pour absorber le tick post-mounted hook (Vue 3 attache
  // les listeners @submit.prevent / @click en mounted, qui s'exécute dans
  // le micro-task queue post-DOM). ``networkidle`` ne marche pas (Vite HMR
  // websocket) ni ``load`` (idem).
  const emailInput = page.locator('#login-email')
  const submitBtn = page.locator('button[type="submit"]')
  await emailInput.waitFor({ state: 'visible', timeout: 15_000 })
  await submitBtn.waitFor({ state: 'visible', timeout: 5_000 })
  await page.waitForTimeout(500)

  await emailInput.fill(email)
  await page.locator('#login-pwd').fill(password)

  // Soumettre par click — le button[type=submit] dispatch un submit event
  // natif que @submit.prevent du form intercepte. On observe la response
  // /auth/login pour propager une vraie erreur si le backend rejette.
  const [loginResp] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().endsWith('/auth/login') && r.request().method() === 'POST',
      { timeout: 15_000 },
    ),
    submitBtn.click(),
  ])
  if (!loginResp.ok()) {
    throw new Error(
      `loginViaUI: /auth/login returned ${loginResp.status()} — ${await loginResp.text()}`,
    )
  }

  // Accepte toute destination post-login standard.
  await page.waitForURL(/\/(dashboard|chat|onboarding|home|projets|profil)\b|\/$/, {
    timeout: 20_000,
  })
}

/**
 * Combo : register côté API puis login côté UI. Fixe automatiquement
 * la propagation CSRF (le browser context partage les cookies entre
 * `request` et `page`).
 */
export async function registerThenLoginViaUI(
  page: Page,
  request: APIRequestContext,
  options?: { email?: string; password?: string; apiBase?: string; frontUrl?: string },
): Promise<LoginResult> {
  const result = await registerLoginCsrf(request, options)
  await loginViaUI(page, result.email, result.password, { frontUrl: options?.frontUrl })
  return result
}

/**
 * Remplace `waitForLoadState('networkidle')` qui timeout systématiquement
 * sur les pages avec SSE keepalive (chat, notifications). On attend simplement
 * que le DOM soit chargé puis qu'un selector stable apparaisse (caller-defined).
 */
export async function waitForPageReady(
  page: Page,
  options?: { selector?: string; timeout?: number },
): Promise<void> {
  await page.waitForLoadState('domcontentloaded', { timeout: options?.timeout ?? 15_000 })
  if (options?.selector) {
    await page.waitForSelector(options.selector, { timeout: options?.timeout ?? 15_000 })
  }
}
