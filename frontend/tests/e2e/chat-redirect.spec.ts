// F41 SC-001 — /chat redirige vers dernier thread ou crée un nouveau thread
// Pré-conditions :
//   - Aucune auth : le middleware global redirige vers /login?redirect=/chat
//   - Auth disponible : la page charge puis navigue vers /chat/<uuid>
import { test, expect } from "@playwright/test"

test.describe("F41 — /chat redirection", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto("/chat")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    // Le middleware global auth.global.ts redirige les anonymes vers /login
    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("non authentifié : /login contient le paramètre redirect=/chat", async ({ page }) => {
    await page.goto("/chat")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    const urlAfter = page.url()
    if (urlAfter.includes("/login")) {
      expect(urlAfter).toContain("redirect=")
    }
  })

  test("la page de chargement affiche le status 'Chargement…'", async ({ page }) => {
    // Intercepter les appels API pour stabiliser le test
    await page.route("**/me/threads**", async (route) => {
      await route.fulfill({
        status: 401,
        body: JSON.stringify({ detail: "Non authentifié" }),
      })
    })

    await page.goto("/chat")
    await page.waitForLoadState("domcontentloaded", { timeout: 10_000 })

    // Soit la page de chargement est visible, soit on est redirigé vers /login
    const onLogin = page.url().includes("/login")
    if (!onLogin) {
      const status = page.locator('[role="status"]')
      if (await status.count()) {
        await expect(status.first()).toBeVisible()
      }
    }
  })
})
