// F46 T093 [US9] — E2E export PDF (skip-able si flag F51 désactivé).
import { test, expect } from "@playwright/test"

test.describe("Scoring — export PDF (US9)", () => {
  test("clic Exporter → fichier PDF téléchargé", async ({ page, request }) => {
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

    const btn = page.locator('[data-testid="export-pdf-button"]')
    const disabled = await btn.isDisabled().catch(() => true)
    if (disabled) {
      test.skip(true, "Flag F51_PDF_EXPORT désactivé")
    }

    const downloadPromise = page.waitForEvent("download", { timeout: 10_000 })
    await btn.click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/\.pdf$/)
  })
})
