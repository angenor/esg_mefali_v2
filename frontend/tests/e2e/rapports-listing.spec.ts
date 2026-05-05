// F49 SC-022 — E2E listing /rapports : table rapports PDF + table attestations.
// Vérifie les en-têtes, états vides, et structure de la page.

import { test, expect } from "@playwright/test"

test.describe("F49 — Rapports & attestations (listing)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/rapports")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("PME authentifié voit le titre 'Rapports & attestations'", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await expect(
      page.getByRole("heading", { name: /rapports.*attestations/i }),
    ).toBeVisible({ timeout: 6000 })
  })

  test("bouton 'Nouveau rapport' est visible et cliquable", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const openGenerate = page.locator('[data-testid="open-generate"]')
    await expect(openGenerate).toBeVisible({ timeout: 6000 })
    await expect(openGenerate).toBeEnabled()
  })

  test("section 'Rapports PDF' est présente", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await expect(
      page.getByRole("heading", { name: /rapports pdf/i }),
    ).toBeVisible({ timeout: 6000 })
  })

  test("section 'Attestations' est présente", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    await expect(
      page.getByRole("heading", { name: /attestations/i }),
    ).toBeVisible({ timeout: 6000 })
  })

  test("état vide rapports : CTA 'Générer mon premier rapport' visible si aucun rapport", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const reportTable = page.locator('[data-testid="report-table"]')
    const tableVisible = await reportTable.isVisible({ timeout: 4000 }).catch(() => false)

    if (!tableVisible) {
      // État vide : vérifier le CTA
      const emptyCta = page.locator('[data-testid="empty-cta"]')
      await expect(emptyCta).toBeVisible({ timeout: 5000 })
    } else {
      // Des rapports existent : la table doit avoir au moins une ligne
      const rows = reportTable.locator('[data-testid="report-row"]')
      const rowCount = await rows.count()
      expect(rowCount).toBeGreaterThan(0)
    }
  })

  test("table rapports affiche les colonnes clés si des rapports existent", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const reportTable = page.locator('[data-testid="report-table"]')
    if (!(await reportTable.isVisible({ timeout: 4000 }).catch(() => false))) {
      test.skip(true, "Aucun rapport — table non affichée")
      return
    }

    // Colonnes obligatoires
    await expect(reportTable.getByRole("columnheader", { name: /titre/i })).toBeVisible()
    await expect(reportTable.getByRole("columnheader", { name: /statut/i })).toBeVisible()
  })
})
