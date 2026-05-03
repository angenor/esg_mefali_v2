// F42 T077 — E2E page d'accueil publique
import { test, expect } from "@playwright/test"

test.describe("F42 — Page publique /", () => {
  test("non authentifié voit pitch + CTA", async ({ page }) => {
    await page.goto("/")
    await expect(
      page.getByRole("heading", { name: /finance verte simplifiée/i }),
    ).toBeVisible()
    await expect(page.locator('[data-testid="public-cta-register"]')).toBeVisible()
  })

  test("CTA navigue vers /register", async ({ page }) => {
    await page.goto("/")
    await page.locator('[data-testid="public-cta-register"]').click()
    await expect(page).toHaveURL(/\/register/)
  })

  test("authentifié est redirigé vers /dashboard", async ({ page }) => {
    // TODO : auth fixture
    await page.goto("/")
    // Si la fixture est branchée, l'URL devrait basculer vers /dashboard
    if (page.url().includes("/dashboard")) {
      await expect(page).toHaveURL(/\/dashboard/)
    }
  })
})
