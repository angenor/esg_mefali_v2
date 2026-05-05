// F46 T037 [US2] — E2E switch entre référentiels via tabs.
import { test, expect } from "@playwright/test"

test.describe("Scoring — switch tab référentiel (US2)", () => {
  test("BOAD → CDP met à jour l'URL sans full-reload", async ({ page, request }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard")

    // Seed BOAD + CDP via API.
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

    // Sentinel pour vérifier l'absence de full-reload.
    await page.evaluate(() => {
      ;(window as unknown as { __navigationSentinel: boolean }).__navigationSentinel = true
    })

    const cdpTab = page.locator('[role="tab"][data-code="CDP"]')
    await expect(cdpTab).toBeVisible()
    const start = Date.now()
    await cdpTab.click()
    await page.waitForURL("**/scoring/CDP", { timeout: 1000 })
    const elapsed = Date.now() - start
    expect(elapsed).toBeLessThan(1000)

    // Sentinel toujours présente → SPA navigation.
    const sentinel = await page.evaluate(
      () => (window as unknown as { __navigationSentinel?: boolean }).__navigationSentinel,
    )
    expect(sentinel).toBe(true)
  })
})
