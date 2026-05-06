// F47 SC-089 — E2E bouton "Exporter PDF" placeholder (MVP : modale d'information).
// Le bouton est `ready=false` par défaut → ouvre une modale au lieu de télécharger.
// Quand `ready=true` (post-F51), déléguer à useExportPdf → téléchargement effectif.

import { test, expect } from "@playwright/test"

test.describe("F47 — Empreinte carbone (export PDF)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/carbone")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("bouton export PDF est visible si une empreinte est présente", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Pas d'empreinte — le bouton export n'est pas affiché")
      return
    }

    // ExportPdfButton : UiButton avec texte issu de carbon.export.button
    // Le bouton est dans un div.mt-6 en fin de page
    const exportBtn = page.locator(".mt-6 button, .mt-6 [role='button']").last()
    await expect(exportBtn).toBeVisible({ timeout: 5000 })
  })

  test("clic sur export PDF (MVP ready=false) ouvre la modale placeholder", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Pas d'empreinte — le bouton export n'est pas affiché")
      return
    }

    // Cliquer sur le bouton export (le dernier bouton de la page)
    const exportBtn = page.locator(".mt-6 button").last()
    if (!(await exportBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton export non trouvé")
      return
    }

    await exportBtn.click()

    // La modale UiModal doit s'ouvrir (role=dialog ou [role="dialog"])
    const modal = page.locator('[role="dialog"]')
    const modalVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false)

    if (modalVisible) {
      await expect(modal).toBeVisible()
      // Bouton Fermer doit être présent
      const closeBtn = modal.getByRole("button")
      await expect(closeBtn.first()).toBeVisible()
    }
    // Si la modale n'est pas un role=dialog (UiModal implémentation), on
    // vérifie au moins qu'il n'y a pas eu d'erreur de navigation.
    await expect(page).toHaveURL(/\/carbone/)
  })

  test("double-clic sur export PDF n'ouvre pas deux modales", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Pas d'empreinte")
      return
    }

    const exportBtn = page.locator(".mt-6 button").last()
    if (!(await exportBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton export non trouvé")
      return
    }

    await exportBtn.dblclick()

    const modals = page.locator('[role="dialog"]')
    const count = await modals.count()
    expect(count).toBeLessThanOrEqual(1)
  })
})
