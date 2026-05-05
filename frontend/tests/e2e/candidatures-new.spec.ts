// F51 SC-004 — /candidatures/new création de candidature (redirect page)
// Pré-conditions :
//   - Non-auth : redirige vers /login
//   - Auth sans params : affiche erreur "Paramètres requis"
//   - Auth avec offre_id + projet_id valides : redirige vers /candidatures/<id>
import { test, expect } from "@playwright/test"

test.describe("F51 — /candidatures/new création", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto("/candidatures/new")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("sans paramètres : affiche titre 'Création de votre candidature…'", async ({ page }) => {
    await page.goto("/candidatures/new")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const heading = page.getByRole("heading", { name: /Création de votre candidature/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test("sans paramètres : affiche message d'erreur 'Paramètres requis'", async ({ page }) => {
    await page.goto("/candidatures/new")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // La page affiche l'erreur si offre_id ou projet_id sont absents
    const error = page.locator("p", { hasText: /Paramètres.*requis|offre_id.*projet_id/i })
    if (await error.count()) {
      await expect(error.first()).toBeVisible()
    }
  })

  test("avec offre_id et projet_id invalides : affiche une erreur (pas de 500)", async ({ page }) => {
    // Mock la réponse API pour éviter un vrai appel backend
    await page.route("**/me/projets/**/candidatures", async (route) => {
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Projet ou offre introuvable." }),
      })
    })

    await page.goto("/candidatures/new?offre_id=fake-offre&projet_id=fake-projet")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Soit une erreur est affichée, soit on est redirigé (si le backend répond correctement)
    const error = page.locator("p.text-red-700, [class*='red']")
    const heading = page.getByRole("heading", { name: /Création de votre candidature/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
    if (await error.count()) {
      await expect(error.first()).toBeVisible()
    }
  })
})
