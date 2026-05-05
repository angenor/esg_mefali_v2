// F46 T059 [US4] — E2E indicateur non mappé : pas de mutation backend.
import { test, expect } from "@playwright/test"

test.describe("Scoring — édition indicateur non mappé (US4)", () => {
  test("indicateur hors mapping → bouton Modifier désactivé OU dispatch chat", async ({
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

    let patchCalls = 0
    await page.route("**/me/entreprise", (route) => {
      if (route.request().method() === "PATCH") patchCalls += 1
      void route.continue()
    })

    await page.goto("/scoring/BOAD")
    await expect(
      page.locator('[data-testid="score-overview-score"]'),
    ).toBeVisible({ timeout: 5000 })

    // Ouvrir un indicateur non éditable (n'importe quel indicateur hors mapping).
    const rows = page.locator(".indicateur-row")
    const count = await rows.count()
    let opened = false
    for (let i = 0; i < count; i++) {
      const r = rows.nth(i)
      const editable = await r.getAttribute("data-editable")
      if (editable === "false") {
        await r.click()
        opened = true
        break
      }
    }
    if (!opened) test.skip(true, "Aucun indicateur non éditable disponible")

    const editBtn = page.locator('[data-testid="indicateur-drawer-edit"]')
    const isDisabled = await editBtn.isDisabled().catch(() => true)
    if (!isDisabled) {
      await editBtn.click()
    }

    // Aucune PATCH ne doit avoir été émise.
    await page.waitForTimeout(500)
    expect(patchCalls).toBe(0)
  })
})
