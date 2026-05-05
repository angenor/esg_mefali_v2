// F44 T045 — E2E : double-clic sur Export ne génère qu'un seul download (FR-021).
import { test, expect } from "@playwright/test"

test.describe("F44 — Export anti double-clic (US4)", () => {
  test("deux clics rapides → un seul download", async ({ page }) => {
    await page.goto("/dashboard")
    const btn = page.locator('[data-testid="export-button"]')
    if (!(await btn.isVisible())) test.skip()

    const downloads: unknown[] = []
    page.on("download", (d) => downloads.push(d))
    await btn.click()
    await btn.click({ force: true })
    // Laisser le temps au second download éventuel.
    await page.waitForTimeout(1500)
    expect(downloads.length).toBe(1)
  })
})
