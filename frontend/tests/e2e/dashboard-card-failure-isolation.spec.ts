// F44 T056 [US7] — E2E : isolation des erreurs de cartes (FR-020 / SC-010).
// Une erreur 5xx sur /me/matching/recommendations ne doit pas casser les 6 cartes principales.
import { test, expect } from "@playwright/test"

test.describe("F44 — Isolation d'erreur entre cartes (US7)", () => {
  test("erreur sur /me/matching/recommendations → 6 cartes principales restent rendues", async ({ page }) => {
    await page.route("**/me/matching/recommendations*", (route) =>
      route.fulfill({ status: 500, body: "boom" }),
    )
    await page.goto("/dashboard")
    if (await page.locator('[data-testid="empty-state-landing"]').isVisible()) test.skip()

    for (const tid of [
      "card-scoring",
      "card-carbon",
      "card-credit",
      "card-candidatures",
      "card-rapports",
      "card-action-plan",
    ]) {
      await expect(page.locator(`[data-testid="${tid}"]`)).toBeVisible()
    }
    // La carte intermédiaires affiche son état d'erreur isolé.
    const inter = page.locator('[data-testid="card-intermediaires"]')
    if (await inter.isVisible()) {
      await expect(inter.getByRole("alert")).toBeVisible()
    }
  })
})
