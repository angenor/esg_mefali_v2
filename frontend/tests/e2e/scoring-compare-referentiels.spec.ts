// F46 T038 [US2] — E2E comparaison de référentiels.
import { test, expect } from "@playwright/test"

test.describe("Scoring — Compare drawer (US2)", () => {
  test("ouvrir drawer + cocher BOAD/CDP → bar chart 2 séries", async ({ page, request }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "BOAD" },
    })
    await request.post("/me/scoring/entreprise/recompute", {
      data: { referentiel_code: "CDP" },
    })

    await page.goto("/scoring/BOAD")
    await expect(page.locator('[data-testid="score-overview-score"]')).toBeVisible({
      timeout: 5000,
    })

    await page.locator('[data-testid="compare-button"]').click()
    const drawer = page.locator('[data-testid="compare-drawer"]')
    await expect(drawer).toBeVisible()

    // Cocher CDP (BOAD est par défaut).
    const cdpCheckbox = drawer.locator('input[type="checkbox"][value="CDP"]')
    if (!(await cdpCheckbox.isChecked())) {
      await cdpCheckbox.check()
    }

    // Bar chart côté à côté.
    await expect(drawer.locator("canvas")).toBeVisible({ timeout: 3000 })
    const legend = drawer.locator('[data-testid="compare-drawer-legend"]')
    await expect(legend).toContainText("BOAD")
    await expect(legend).toContainText("CDP")
  })
})
