// F46 T066 [US5] — E2E CTA Compléter sur indicateur manquant.
import { test, expect } from "@playwright/test"

test.describe("Scoring — CTA Compléter (US5)", () => {
  test("clic Compléter dispatch open_chat_for_indicateur", async ({
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

    const list = page.locator('[data-testid="missing-indicators-list"]')
    if (await list.count() === 0) {
      test.skip(true, "Pas d'indicateur manquant pour ce compte")
    }

    await page.evaluate(() => {
      ;(window as unknown as { __chatOpen: number }).__chatOpen = 0
      window.addEventListener("open_chat_for_indicateur", () => {
        ;(window as unknown as { __chatOpen: number }).__chatOpen += 1
      })
    })

    await page
      .locator('[data-testid="missing-complete-cta"]')
      .first()
      .click()

    const count = await page.evaluate(
      () => (window as unknown as { __chatOpen?: number }).__chatOpen ?? 0,
    )
    expect(count).toBeGreaterThanOrEqual(1)
  })
})
