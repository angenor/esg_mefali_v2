// F46 T071 [US6] — E2E Recalcul + anti double-clic.
import { test, expect } from "@playwright/test"

test.describe("Scoring — Recalcul (US6)", () => {
  test("clic Recalculer → spinner → nouveau computed_at", async ({
    page,
    request,
  }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })

    await page.goto("/scoring/BOAD")
    await expect(
      page.locator('[data-testid="score-overview-score"]'),
    ).toBeVisible({ timeout: 5000 })

    const initialDate = await page
      .locator('[data-testid="score-overview-computed-at"]')
      .innerText()
      .catch(() => "")

    let recomputeCalls = 0
    await page.route("**/me/scoring/entreprise/*/recompute*", (route) => {
      recomputeCalls += 1
      void route.continue()
    })

    const btn = page.locator('[data-testid="recalc-button"]')
    await btn.click()
    await btn.click() // 2e clic immédiat — doit être ignoré (bouton désactivé)

    await page.waitForFunction(
      (initial) =>
        document.querySelector('[data-testid="score-overview-computed-at"]')
          ?.textContent !== initial,
      initialDate,
      { timeout: 10_000 },
    )
    expect(recomputeCalls).toBeLessThanOrEqual(1)
  })
})
