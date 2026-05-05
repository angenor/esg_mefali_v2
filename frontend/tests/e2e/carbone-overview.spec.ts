// F47 SC-034 — E2E rendu /carbone (synthèse, KPI, scopes) avec empreinte existante.
// Pré-conditions : compte PME authentifié avec un calcul carbone existant.
// Skip-tolérant : redirige vers /login si non-auth, skip si pas d'empreinte.

import { test, expect } from "@playwright/test"

test.describe("F47 — Empreinte carbone (synthèse)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/carbone")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("PME authentifié voit le titre de la page /carbone", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    // Soit on a un EmptyStateWizard, soit on a la synthèse
    const heading = page.getByRole("heading", { level: 1 })
    await expect(heading).toBeVisible({ timeout: 6000 })
  })

  test("page /carbone affiche le sélecteur d'année", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    const yearSelect = page.locator("#carbon-year-select")
    await expect(yearSelect).toBeVisible({ timeout: 6000 })
  })

  test("synthèse affiche KPI total tCO2e si empreinte présente", async ({ page, request }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    // Skip si EmptyStateWizard est affiché (pas de données)
    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Aucune empreinte carbone seed — vue EmptyStateWizard")
      return
    }

    // KPI total : section aria-label contenant le chiffre tCO2e
    const overviewSection = page
      .locator('[aria-label]')
      .filter({ hasText: /tCO₂e|tCO2e/ })
      .first()
    await expect(overviewSection).toBeVisible({ timeout: 5000 })
  })

  test("synthèse affiche les 3 accordéons de scopes si empreinte présente", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Aucune empreinte carbone seed — vue EmptyStateWizard")
      return
    }

    // 3 scopes rendus comme <details>
    const scopeAccordions = page.locator("#carbon-scopes details")
    await expect(scopeAccordions).toHaveCount(3, { timeout: 5000 })
  })

  test("bandeau RecalcStrip visible si empreinte présente", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Aucune empreinte carbone seed")
      return
    }

    // RecalcStrip : div avec data-year
    const recalcStrip = page.locator('[data-year]').first()
    await expect(recalcStrip).toBeVisible({ timeout: 5000 })
  })
})
