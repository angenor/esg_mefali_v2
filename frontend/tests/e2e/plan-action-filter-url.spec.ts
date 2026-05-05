// F45 T027 — E2E persistence URL des filtres.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test.describe("Plan d'action — filter URL", () => {
  test.beforeEach(async ({ page }) => {
    await seedPmeWithActionPlan(page, { stepsCount: 10 })
  })

  test("toggle filtre priorité=haute met à jour l'URL", async ({ page }) => {
    await page.goto("/plan-action")
    await page.locator('button[aria-pressed="false"]', { hasText: "Haute" }).first().click()
    await expect(page).toHaveURL(/priority=haute/)
  })

  test("ouverture directe ?priority=haute&status=todo applique les filtres", async ({ page }) => {
    await page.goto("/plan-action?priority=haute&status=todo")
    await expect(
      page.locator('button[aria-pressed="true"]', { hasText: "Haute" }),
    ).toBeVisible()
    await expect(
      page.locator('button[aria-pressed="true"]', { hasText: "À faire" }),
    ).toBeVisible()
  })

  test("?priority=zzz ignoré silencieusement", async ({ page }) => {
    await page.goto("/plan-action?priority=zzz")
    await expect(page.locator('[data-testid="timeline"]')).toBeVisible()
  })
})
