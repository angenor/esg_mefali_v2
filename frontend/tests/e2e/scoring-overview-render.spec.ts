// F46 T025 [US1] — E2E rendu /scoring après seed d'un calcul BOAD.
// Authentification PME → POST recompute → ouvrir /scoring → assertions.
import { test, expect } from "@playwright/test"

test.describe("Scoring — vue d'ensemble (US1)", () => {
  test("PME avec 1 calcul BOAD → /scoring affiche score, radar, sources", async ({
    page,
    request,
  }) => {
    // Authentification + seed (helper attendu cf. tests/e2e/helpers/*).
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    // Seed un calcul BOAD via l'API recompute.
    const recomputeRes = await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })
    expect(recomputeRes.ok()).toBeTruthy()

    await page.goto("/scoring")
    // Redirection vers /scoring/BOAD attendue.
    await page.waitForURL("**/scoring/BOAD", { timeout: 5000 })

    // Score global visible < 2 s.
    const score = page.locator('[data-testid="score-overview-score"]')
    await expect(score).toBeVisible({ timeout: 2000 })

    // Radar (≤6 axes pour BOAD).
    await expect(page.locator('[data-testid="score-overview-radar"]')).toBeVisible()

    // % couverture + date FR + pastille v.X.
    await expect(page.locator('[data-testid="score-overview-coverage"]')).toContainText(/%/)
    await expect(page.locator('[data-testid="score-overview-date"]')).toBeVisible()
    await expect(page.locator('[data-testid="score-overview-version"]')).toContainText(/v\./)

    // Sources cliquables : pastille source ouvre une popover.
    const sourcePin = page.locator('[data-testid="source-pin"]').first()
    if (await sourcePin.count()) {
      await sourcePin.click()
      await expect(
        page.locator('[role="dialog"][aria-label], .viz-source-pin__popover'),
      ).toBeVisible()
    }
  })
})
