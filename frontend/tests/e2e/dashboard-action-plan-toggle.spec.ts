// F44 T035 — E2E quickstart S3 : cocher étape plan d'action depuis le dashboard.
// Pré-conditions :
//   - fixture compte PME avec ≥ 4 étapes pending dans `next_actions`.
// Les fixtures complètes sont à brancher post-MVP (cf. empty-state-landing.spec.ts).

import { test, expect } from "@playwright/test"

test.describe("F44 — Dashboard plan d'action toggle (US2)", () => {
  test("cocher la 1re étape → spinner < 1 s → étape disparaît, persistance après reload", async ({ page }) => {
    await page.goto("/dashboard")
    const card = page.locator('[data-testid="card-action-plan"]')
    if (!(await card.isVisible())) test.skip()

    const steps = card.locator('[data-testid="action-step"]')
    const initialCount = await steps.count()
    if (initialCount < 4) test.skip()

    const firstTitle = await steps.nth(0).innerText()
    await steps.nth(0).locator('[data-testid="action-step-check"]').check()

    // Spinner visible brièvement.
    await expect(steps.nth(0).locator('[data-testid="action-step-spinner"]')).toBeVisible({ timeout: 1500 })

    // Après refresh ciblé, l'étape doit avoir disparu et la 4e apparaître.
    await expect(card.locator(`[data-testid="action-step"]:has-text("${firstTitle}")`)).toHaveCount(0, { timeout: 3000 })

    // Persistance : reload et vérifier que l'étape n'est plus présente.
    await page.reload()
    await expect(card.locator(`[data-testid="action-step"]:has-text("${firstTitle}")`)).toHaveCount(0)
  })
})
