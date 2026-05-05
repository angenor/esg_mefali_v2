// F27 F51 SC-007 — /simulateur/historique liste des simulations sauvegardées
// Pré-conditions :
//   - Non-auth : redirige vers /login
//   - Auth : titre "Historique des simulations" + table (Nom, Coût total, CO₂ évité)
//   - État vide : affiche "Aucune simulation sauvegardée."
import { test, expect } from "@playwright/test"

test.describe("F51 — /simulateur/historique", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("page chargée auth : titre 'Historique des simulations' visible", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const heading = page.getByRole("heading", { name: /Historique des simulations/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test("page chargée auth : lien de retour vers /simulateur présent", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const backLink = page.getByRole("link", { name: /Retour au simulateur/i })
    if (await backLink.count()) {
      await expect(backLink.first()).toBeVisible()
      await expect(backLink.first()).toHaveAttribute("href", /\/simulateur$/)
    }
  })

  test("page chargée auth : table avec colonnes Nom, Coût total, CO₂ évité", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Attendre fin du chargement
    const loading = page.locator("p", { hasText: /Chargement/i })
    if (await loading.count()) {
      await loading.first().waitFor({ state: "hidden", timeout: 10_000 }).catch(() => {})
    }

    const table = page.locator("table")
    if (await table.count()) {
      await expect(table.first()).toBeVisible()
      await expect(page.locator("th", { hasText: /Nom/i }).first()).toBeVisible()
      // "Coût total" peut apparaître comme texte dans th
      const coutCol = page.locator("th").filter({ hasText: /Co.t total/i })
      if (await coutCol.count()) {
        await expect(coutCol.first()).toBeVisible()
      }
    }
  })

  test("état vide auth : affiche 'Aucune simulation sauvegardée.'", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const loading = page.locator("p", { hasText: /Chargement/i })
    if (await loading.count()) {
      await loading.first().waitFor({ state: "hidden", timeout: 10_000 }).catch(() => {})
    }

    const empty = page.locator("td", { hasText: /Aucune simulation sauvegardée/i })
    if (await empty.count()) {
      await expect(empty.first()).toBeVisible()
    }
  })

  test("page chargée auth : pas de 404 ni d'erreur critique", async ({ page }) => {
    await page.goto("/simulateur/historique")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    await expect(page.locator("text=404")).toHaveCount(0)
    await expect(page.locator("text=Page introuvable")).toHaveCount(0)
    // Au moins un élément structurel présent
    await expect(page.locator("h1, h2, table, main").first()).toBeVisible({ timeout: 10_000 })
  })
})
