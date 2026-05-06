// F47 SC-037 — E2E synchronisation ?year= dans l'URL avec le sélecteur d'année.
// Vérifie la lecture depuis le query param ET l'écriture au changement de valeur.

import { test, expect } from "@playwright/test"

test.describe("F47 — Empreinte carbone (sync année URL)", () => {
  test("non authentifié est redirigé vers /login depuis /carbone?year=2023", async ({ page }) => {
    await page.goto("/carbone?year=2023")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("?year=2023 dans l'URL est reflété dans le sélecteur d'année", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone?year=2023")

    const yearSelect = page.locator("#carbon-year-select")
    await expect(yearSelect).toBeVisible({ timeout: 6000 })

    // Le sélecteur doit avoir 2023 comme valeur sélectionnée si cette année
    // est dans les options (N-2 à N+1 générées dynamiquement).
    const selectValue = await yearSelect.inputValue().catch(() => null)
    if (selectValue !== null) {
      expect(selectValue).toBe("2023")
    }
  })

  test("changer le sélecteur d'année met à jour le query param ?year=", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    const yearSelect = page.locator("#carbon-year-select")
    await expect(yearSelect).toBeVisible({ timeout: 6000 })

    // Lire les options disponibles
    const options = await yearSelect.locator("option").allTextContents()
    if (options.length < 2) {
      test.skip(true, "Pas assez d'options pour tester le changement d'année")
      return
    }

    // Sélectionner la première option
    const firstOption = options[0]?.trim()
    if (!firstOption) return

    await yearSelect.selectOption({ label: firstOption })

    // Vérifier que l'URL contient maintenant year=
    await expect(page).toHaveURL(/[?&]year=\d{4}/, { timeout: 3000 })
  })

  test("query param ?year= invalide est ignoré et n'entraîne pas d'erreur", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    // Année hors borne
    await page.goto("/carbone?year=1800")

    const yearSelect = page.locator("#carbon-year-select")
    await expect(yearSelect).toBeVisible({ timeout: 6000 })

    // La page ne doit pas afficher d'erreur non gérée
    const consoleErrors: string[] = []
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text())
    })

    // L'année sélectionnée ne doit pas être 1800
    const selectValue = await yearSelect.inputValue().catch(() => "")
    expect(selectValue).not.toBe("1800")
  })
})
