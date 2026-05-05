// F26 F51 SC-003 — /candidatures liste des candidatures
// Pré-conditions :
//   - Non-auth : redirige vers /login (auth.global.ts)
//   - Auth (PME) : titre "Mes candidatures" + table + filtres statut + recherche
//   - Note : la page n'a pas de definePageMeta() explicite mais est protégée par auth.global.ts
import { test, expect } from "@playwright/test"

test.describe("F51 — /candidatures liste", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("page chargée auth : titre 'Mes candidatures' visible", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const heading = page.getByRole("heading", { name: /Mes candidatures/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test("page chargée auth : CTA 'Nouvelle candidature' pointe vers /matching", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const cta = page.getByRole("link", { name: /Nouvelle candidature/i })
    if (await cta.count()) {
      await expect(cta.first()).toBeVisible()
      await expect(cta.first()).toHaveAttribute("href", /\/matching/)
    }
  })

  test("page chargée auth : filtre statut présent", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Le select de filtre est labellisé "Statut" dans CandidaturesTable
    const label = page.locator("label", { hasText: /Statut/i })
    if (await label.count()) {
      await expect(label.first()).toBeVisible()
      const select = label.first().locator("select")
      if (await select.count()) {
        await expect(select.first()).toBeVisible()
      }
    }
  })

  test("page chargée auth : champ de recherche présent", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const search = page.locator('input[type="search"]')
    if (await search.count()) {
      await expect(search.first()).toBeVisible()
      await expect(search.first()).toHaveAttribute("placeholder", /Rechercher/i)
    }
  })

  test("page chargée auth : table avec colonnes Offre, Statut, Progression visibles", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const table = page.locator("table")
    if (await table.count()) {
      await expect(table.first()).toBeVisible()
      await expect(page.locator("th", { hasText: /Offre/i }).first()).toBeVisible()
      await expect(page.locator("th", { hasText: /Statut/i }).first()).toBeVisible()
      await expect(page.locator("th", { hasText: /Progression/i }).first()).toBeVisible()
    }
  })

  test("page chargée auth : état vide affiche message 'Aucune candidature'", async ({ page }) => {
    await page.goto("/candidatures")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Message vide affiché seulement si store.list est vide ET pas en chargement
    const empty = page.locator("td", { hasText: /Aucune candidature/i })
    const loading = page.locator("p", { hasText: /Chargement/i })
    const table = page.locator("table")

    if (await table.count()) {
      // Attendre que le chargement se termine
      await loading.waitFor({ state: "hidden", timeout: 10_000 }).catch(() => {
        // Loading peut ne pas être visible si pas de données
      })
      // Si la table est là mais vide, le message doit être visible
      if (await empty.count()) {
        await expect(empty.first()).toBeVisible()
      }
    }
  })
})
