// F46 T049 [US3] — E2E drilldown indicateur via drawer.
import { test, expect } from "@playwright/test"

test.describe("Scoring — drilldown drawer (US3)", () => {
  test("dérouler Environnement, cliquer indicateur EFFECTIFS_TOTAL → drawer + chart + Escape", async ({
    page,
    request,
  }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    const recomputeRes = await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })
    expect(recomputeRes.ok()).toBeTruthy()

    await page.goto("/scoring/BOAD")
    await page.waitForURL("**/scoring/BOAD")

    const accordion = page.locator('[data-testid="pillar-accordion"]')
    await expect(accordion).toBeVisible({ timeout: 5000 })

    // Dérouler le pilier E (déjà ouvert par défaut, mais tolérant).
    const detailE = page.locator('[data-testid="pillar-accordion-E"]')
    if (await detailE.count()) {
      const isOpen = await detailE.evaluate((el) => (el as HTMLDetailsElement).open)
      if (!isOpen) {
        await detailE.locator("summary").click()
      }
    }

    const row = page
      .locator('[data-testid^="indicateur-row-"]')
      .first()
    await row.click()

    const drawer = page.locator('[data-testid="indicateur-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 2000 })

    // Graphique linéaire visible.
    await expect(drawer.locator(".stub-line-chart, canvas, .viz-chart")).toBeVisible()

    // Escape ferme.
    await page.keyboard.press("Escape")
    await expect(drawer).toBeHidden({ timeout: 2000 })
  })
})
