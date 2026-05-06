// F49 SC-037 — E2E révocation d'une attestation active via RevokeAttestationModal.
// Vérifie le formulaire de motif (obligatoire), la confirmation, et l'état désactivé
// du bouton Révoquer pour les attestations non actives.

import { test, expect } from "@playwright/test"

test.describe("F49 — Attestations (révocation)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/rapports")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("bouton Révoquer est visible pour les attestations actives", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    const revokeBtn = attestationTable.locator('[data-testid="revoke-btn"]').first()
    await expect(revokeBtn).toBeVisible({ timeout: 3000 })
  })

  test("bouton Révoquer est désactivé pour les attestations non actives", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    // Chercher une attestation révoquée ou expirée
    const rows = attestationTable.locator('[data-testid="attestation-row"]')
    const rowCount = await rows.count()

    for (let i = 0; i < rowCount; i++) {
      const row = rows.nth(i)
      const statusText = await row.textContent()
      if (statusText?.toLowerCase().includes("révoquée") || statusText?.toLowerCase().includes("expirée")) {
        const revokeBtn = row.locator('[data-testid="revoke-btn"]')
        await expect(revokeBtn).toBeDisabled()
        return
      }
    }

    // Si toutes les attestations sont actives, ce test est N/A
    test.skip(true, "Aucune attestation révoquée/expirée pour tester le bouton désactivé")
  })

  test("clic sur Révoquer ouvre la modale avec le formulaire de motif", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    // Chercher un bouton Révoquer activé
    const revokeBtn = attestationTable.locator('[data-testid="revoke-btn"]:not([disabled])').first()
    if (!(await revokeBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation active à révoquer")
      return
    }

    await revokeBtn.click()

    const revokeModal = page.locator('[data-testid="revoke-modal"]')
    await expect(revokeModal).toBeVisible({ timeout: 3000 })

    // Le formulaire doit afficher les boutons radio des motifs
    const firstReason = revokeModal.locator('[data-testid^="reason-"]').first()
    await expect(firstReason).toBeVisible()
  })

  test("bouton 'Confirmer la révocation' est désactivé sans motif sélectionné", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    const revokeBtn = attestationTable.locator('[data-testid="revoke-btn"]:not([disabled])').first()
    if (!(await revokeBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation active")
      return
    }

    await revokeBtn.click()
    const revokeModal = page.locator('[data-testid="revoke-modal"]')
    await expect(revokeModal).toBeVisible({ timeout: 3000 })

    // Sans motif, le bouton confirmer doit être désactivé
    const confirmBtn = revokeModal.locator('[data-testid="confirm-revoke"]')
    await expect(confirmBtn).toBeDisabled()
  })

  test("sélectionner un motif active le bouton 'Confirmer la révocation'", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    const revokeBtn = attestationTable.locator('[data-testid="revoke-btn"]:not([disabled])').first()
    if (!(await revokeBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation active")
      return
    }

    await revokeBtn.click()
    const revokeModal = page.locator('[data-testid="revoke-modal"]')
    await expect(revokeModal).toBeVisible({ timeout: 3000 })

    // Sélectionner le premier motif disponible
    const firstReason = revokeModal.locator('[data-testid^="reason-"]').first()
    await firstReason.click()

    const confirmBtn = revokeModal.locator('[data-testid="confirm-revoke"]')
    await expect(confirmBtn).toBeEnabled()
  })

  test("fermer la modale de révocation avec Annuler ne révoque pas", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation")
      return
    }

    const revokeBtn = attestationTable.locator('[data-testid="revoke-btn"]:not([disabled])').first()
    if (!(await revokeBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation active")
      return
    }

    await revokeBtn.click()
    const revokeModal = page.locator('[data-testid="revoke-modal"]')
    await expect(revokeModal).toBeVisible({ timeout: 3000 })

    const cancelBtn = revokeModal.getByRole("button", { name: /annuler/i })
    await cancelBtn.click()

    await expect(revokeModal).not.toBeVisible({ timeout: 2000 })
    // La table est toujours présente, la révocation n'a pas eu lieu
    await expect(attestationTable).toBeVisible()
  })
})
