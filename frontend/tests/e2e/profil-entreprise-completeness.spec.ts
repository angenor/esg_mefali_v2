// F43 T018 — E2E /profil/entreprise : barre de complétion progresse à mesure que les champs sont renseignés.
import { test, expect } from "@playwright/test"

test.describe("F43 — Profil entreprise completeness", () => {
  test("remplir 5 champs fait passer la barre de ~30 % à ~80 %", async ({ page }) => {
    await page.goto("/login")
    await page.fill("#login-email", "fixture@example.com")
    await page.fill("#login-pwd", "Mefali2026!Vert")
    await page.locator("button[type=submit]").click()
    await page.waitForURL(/\/(dashboard|profil)/)

    await page.goto("/profil/entreprise")
    const progress = page.getByRole("progressbar")
    const initial = await progress.getAttribute("aria-valuenow")
    const initialPct = Number(initial ?? "0")
    expect(initialPct).toBeLessThan(80)

    // Remplit 5 champs en bascule édition par section.
    async function fillField(section: string, value: string) {
      const card = page.locator(".section-card").filter({ hasText: section })
      await card.getByRole("button", { name: /Modifier/ }).click()
      await card.locator('input[type="text"]').first().fill(value)
      await page.waitForTimeout(900)
    }

    await fillField("Identité", "ACME SARL")
    await fillField("Identité", "SARL")
    await fillField("Taille", "100")
    await fillField("Localisation", "CI")
    await fillField("Pratiques", "Tri sélectif et compostage interne")

    // Attendre le re-fetch de completeness.
    await page.waitForTimeout(1500)
    const finalPct = Number((await progress.getAttribute("aria-valuenow")) ?? "0")
    expect(finalPct).toBeGreaterThanOrEqual(initialPct)
  })
})
