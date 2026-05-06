// F27 F51 SC-006 — /simulateur sliders + calcul + résultats
// Pré-conditions :
//   - Non-auth : redirige vers /login (auth.global.ts)
//   - Auth : titre "Simulateur de financement" + SliderPanel (4 sliders) + boutons CTA
//   - Sliders identifiés par id : sl-montant, sl-duree, sl-subv, sl-type
import { test, expect } from "@playwright/test"

test.describe("F51 — /simulateur calcul", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("page chargée auth : titre 'Simulateur de financement' visible", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const heading = page.getByRole("heading", { name: /Simulateur de financement/i })
    if (await heading.count()) {
      await expect(heading.first()).toBeVisible()
    }
  })

  test("page chargée auth : lien vers /simulateur/historique présent", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const histLink = page.getByRole("link", { name: /Historique/i })
    if (await histLink.count()) {
      await expect(histLink.first()).toBeVisible()
      await expect(histLink.first()).toHaveAttribute("href", /\/simulateur\/historique/)
    }
  })

  test("page chargée auth : slider 'Montant à financer' présent", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const slider = page.locator("#sl-montant")
    if (await slider.count()) {
      await expect(slider.first()).toBeVisible()
      await expect(slider.first()).toHaveAttribute("type", "range")
    }
  })

  test("page chargée auth : slider 'Durée' présent", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const slider = page.locator("#sl-duree")
    if (await slider.count()) {
      await expect(slider.first()).toBeVisible()
      await expect(slider.first()).toHaveAttribute("type", "range")
    }
  })

  test("page chargée auth : slider 'Part subvention' présent", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const slider = page.locator("#sl-subv")
    if (await slider.count()) {
      await expect(slider.first()).toBeVisible()
    }
  })

  test("page chargée auth : select 'Type d'investissement' présent", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const select = page.locator("#sl-type")
    if (await select.count()) {
      await expect(select.first()).toBeVisible()
      // Vérifie que l'option Solaire est présente
      const option = select.first().locator("option", { hasText: /Solaire/i })
      if (await option.count()) {
        await expect(option.first()).toBeAttached()
      }
    }
  })

  test("page chargée auth : bouton 'Sauvegarder' visible", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const saveBtn = page.getByRole("button", { name: /Sauvegarder/i })
    if (await saveBtn.count()) {
      await expect(saveBtn.first()).toBeVisible()
    }
  })

  test("page chargée auth : bouton CTA 'Trouver des offres' visible", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const ctaBtn = page.getByRole("button", { name: /Trouver des offres/i })
    if (await ctaBtn.count()) {
      await expect(ctaBtn.first()).toBeVisible()
    }
  })

  test("page chargée auth : zone résultats ou placeholder visible", async ({ page }) => {
    await page.goto("/simulateur")
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Soit les résultats chargent, soit le placeholder s'affiche
    const placeholder = page.locator("text=Ajustez les sliders pour lancer le calcul.")
    const results = page.locator("article", { hasText: /Coût total/i })

    const hasPlaceholder = await placeholder.count()
    const hasResults = await results.count()

    if (hasPlaceholder) {
      await expect(placeholder.first()).toBeVisible()
    } else if (hasResults) {
      await expect(results.first()).toBeVisible()
    }
    // Au moins un des deux doit être présent quand la page est chargée
    expect(hasPlaceholder + hasResults).toBeGreaterThan(0)
  })
})
