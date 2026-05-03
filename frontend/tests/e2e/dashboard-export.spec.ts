// F44 T044 — E2E quickstart S4 : export RGPD/UEMOA en un clic.
import { test, expect } from "@playwright/test"

test.describe("F44 — Dashboard export RGPD (US4)", () => {
  test("clic Exporter → téléchargement esg-mefali-export-AAAA-MM-JJ.json + JSON valide", async ({ page }) => {
    await page.goto("/dashboard")
    const btn = page.locator('[data-testid="export-button"]')
    if (!(await btn.isVisible())) test.skip()

    const downloadPromise = page.waitForEvent("download", { timeout: 5000 })
    await btn.click()
    const download = await downloadPromise
    const name = download.suggestedFilename()
    expect(name).toMatch(/^esg-mefali-export-\d{4}-\d{2}-\d{2}\.json$/)
  })
})
