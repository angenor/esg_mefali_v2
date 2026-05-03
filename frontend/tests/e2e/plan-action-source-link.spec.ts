// F45 T064 — E2E lien vers la fiche indicateur source.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("clic pin source d'une carte → /scoring/indicateurs/{id}", async ({ page }) => {
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")

  const sourceLink = page.locator(".pa-step__source").first()
  // Si la première carte n'a pas de source, on cherche celle qui en a une
  const links = page.locator(".pa-step a.pa-step__source")
  const count = await links.count()
  test.skip(count === 0, "Aucune carte n'a d'indicateur source dans le seed")

  const href = await links.first().getAttribute("href")
  expect(href).toMatch(/^\/scoring\/indicateurs\//)
  await sourceLink.first().click()
})
