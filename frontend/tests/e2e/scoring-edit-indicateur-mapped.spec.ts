// F46 T058 [US4] — E2E édition indicateur mappé.
import { test, expect } from "@playwright/test"

test.describe("Scoring — édition indicateur mappé (US4)", () => {
  test("EFFECTIFS_TOTAL : ouvrir drawer, modifier, score change", async ({
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

    const initialScore = await page
      .locator('[data-testid="score-overview-score"]')
      .innerText()

    // Ouvrir le pilier S puis l'indicateur EFFECTIFS_TOTAL.
    await page.locator('details[data-pillar="S"]').click()
    await page
      .locator('[data-indicateur-code="EFFECTIFS_TOTAL"]')
      .first()
      .click()

    await expect(
      page.locator('[data-testid="indicateur-drawer"]'),
    ).toBeVisible()

    await page.locator('[data-testid="indicateur-drawer-edit"]').click()

    // Le bottom sheet ask_number s'affiche.
    await expect(page.locator('[data-tool="ask_number"]')).toBeVisible({
      timeout: 5000,
    })

    await page.fill('input[type="number"]', "200")
    await page.click('[data-testid="bottom-sheet-submit"]')

    await page.waitForFunction(
      (initial) =>
        document.querySelector('[data-testid="score-overview-score"]')
          ?.textContent !== initial,
      initialScore,
      { timeout: 10_000 },
    )
  })
})
