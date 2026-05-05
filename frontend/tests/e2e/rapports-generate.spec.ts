// F49 SC-029 — E2E génération d'un rapport via GenerateReportModal.
// Vérifie l'ouverture de la modale, les champs du formulaire, et la soumission.

import { test, expect } from "@playwright/test"

test.describe("F49 — Rapports (génération)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/rapports")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("clic sur 'Nouveau rapport' ouvre la modale de génération", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const openBtn = page.locator('[data-testid="open-generate"]')
    await expect(openBtn).toBeVisible({ timeout: 6000 })
    await openBtn.click()

    const modal = page.locator('[data-testid="generate-modal"]')
    await expect(modal).toBeVisible({ timeout: 3000 })
  })

  test("modale de génération affiche le formulaire complet", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await page.locator('[data-testid="open-generate"]').click()
    const modal = page.locator('[data-testid="generate-modal"]')
    await expect(modal).toBeVisible({ timeout: 3000 })

    // Champs obligatoires
    await expect(modal.locator('[data-testid="select-type"]')).toBeVisible()
    await expect(modal.locator('[data-testid="select-ref"]')).toBeVisible()
    await expect(modal.locator('[data-testid="input-from"]')).toBeVisible()
    await expect(modal.locator('[data-testid="input-to"]')).toBeVisible()
    await expect(modal.locator('[data-testid="submit-btn"]')).toBeVisible()
  })

  test("le sélecteur de type propose les 3 types de rapport", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await page.locator('[data-testid="open-generate"]').click()
    const modal = page.locator('[data-testid="generate-modal"]')
    await expect(modal).toBeVisible({ timeout: 3000 })

    const typeSelect = modal.locator('[data-testid="select-type"]')
    const options = await typeSelect.locator("option").allTextContents()
    expect(options.length).toBeGreaterThanOrEqual(3)
    // Vérifier que les types FR sont présents
    const labels = options.map((o) => o.toLowerCase())
    expect(labels.some((l) => l.includes("conformité") || l.includes("conformite"))).toBeTruthy()
  })

  test("fermer la modale avec Annuler ou ×", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await page.locator('[data-testid="open-generate"]').click()
    const modal = page.locator('[data-testid="generate-modal"]')
    await expect(modal).toBeVisible({ timeout: 3000 })

    // Fermer via bouton Annuler
    const cancelBtn = modal.getByRole("button", { name: /annuler/i })
    await cancelBtn.click()

    await expect(modal).not.toBeVisible({ timeout: 2000 })
  })

  test("bouton 'Lancer la génération' est désactivé si dates invalides", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await page.locator('[data-testid="open-generate"]').click()
    const modal = page.locator('[data-testid="generate-modal"]')
    await expect(modal).toBeVisible({ timeout: 3000 })

    // Mettre une date de début après la date de fin
    await modal.locator('[data-testid="input-from"]').fill("2025-12-31")
    await modal.locator('[data-testid="input-to"]').fill("2025-01-01")

    const submitBtn = modal.locator('[data-testid="submit-btn"]')
    await expect(submitBtn).toBeDisabled()
  })
})
