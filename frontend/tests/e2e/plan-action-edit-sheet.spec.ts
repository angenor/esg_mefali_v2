// F45 T034 — E2E édition via bottom sheet.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("ouvre la sheet, modifie statut → doing, valide", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")
  await page.getByRole("button", { name: "Modifier" }).first().click()
  await page.getByRole("dialog").waitFor()
  await page.locator('input[name=status][value=doing]').check()
  await page.getByRole("button", { name: "Enregistrer" }).click()
  await expect(page.getByRole("dialog")).toBeHidden()
  await expect(page.locator(".pa-step").first()).toContainText("En cours")
})

test("Esc ferme la sheet sans modifier", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")
  await page.getByRole("button", { name: "Modifier" }).first().click()
  await page.keyboard.press("Escape")
  await expect(page.getByRole("dialog")).toBeHidden()
})
