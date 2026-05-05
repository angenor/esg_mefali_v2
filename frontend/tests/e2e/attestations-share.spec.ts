// F49 SC-036 — E2E partage d'une attestation via ShareAttestationModal.
// Vérifie l'URL publique lisible, le bouton Copier, et le QR code.
// Skip-tolérant : nécessite une attestation active en base.

import { test, expect } from "@playwright/test"

test.describe("F49 — Attestations (partage)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/rapports")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("table attestations affiche le bouton Partager si des attestations existent", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/rapports")

    const attestationTable = page.locator('[data-testid="attestation-table"]')
    if (!(await attestationTable.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Aucune attestation — table non affichée")
      return
    }

    const shareBtn = attestationTable.locator('[data-testid="share-btn"]').first()
    await expect(shareBtn).toBeVisible({ timeout: 3000 })
  })

  test("clic sur Partager ouvre la modale ShareAttestationModal", async ({ page }) => {
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

    const shareBtn = attestationTable.locator('[data-testid="share-btn"]').first()
    if (!(await shareBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton Partager non visible")
      return
    }

    await shareBtn.click()

    const shareModal = page.locator('[data-testid="share-modal"]')
    await expect(shareModal).toBeVisible({ timeout: 3000 })
  })

  test("modale de partage affiche l'URL publique et le bouton Copier", async ({ page }) => {
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

    const shareBtn = attestationTable.locator('[data-testid="share-btn"]').first()
    if (!(await shareBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton Partager non visible")
      return
    }

    await shareBtn.click()
    const shareModal = page.locator('[data-testid="share-modal"]')
    await expect(shareModal).toBeVisible({ timeout: 3000 })

    // URL publique (input readonly)
    const urlInput = shareModal.locator('[data-testid="share-url"]')
    await expect(urlInput).toBeVisible()
    const urlValue = await urlInput.inputValue()
    expect(urlValue).toMatch(/\/verify\//)

    // Bouton Copier
    const copyBtn = shareModal.locator('[data-testid="copy-btn"]')
    await expect(copyBtn).toBeVisible()
    await expect(copyBtn).toBeEnabled()
  })

  test("modale de partage affiche le QR code ou l'indicateur de chargement", async ({ page }) => {
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

    const shareBtn = attestationTable.locator('[data-testid="share-btn"]').first()
    if (!(await shareBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton Partager non visible")
      return
    }

    await shareBtn.click()
    const shareModal = page.locator('[data-testid="share-modal"]')
    await expect(shareModal).toBeVisible({ timeout: 3000 })

    // Soit le QR est en cours de génération, soit il est affiché
    const qrLoading = shareModal.locator('[data-testid="qr-loading"]')
    const qrImage = shareModal.locator('[data-testid="qr-image"]')

    const hasLoading = await qrLoading.isVisible({ timeout: 1000 }).catch(() => false)
    const hasImage = await qrImage.isVisible({ timeout: 5000 }).catch(() => false)

    expect(hasLoading || hasImage).toBeTruthy()
  })

  test("fermer la modale de partage avec le bouton Fermer", async ({ page }) => {
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

    const shareBtn = attestationTable.locator('[data-testid="share-btn"]').first()
    if (!(await shareBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Bouton Partager non visible")
      return
    }

    await shareBtn.click()
    const shareModal = page.locator('[data-testid="share-modal"]')
    await expect(shareModal).toBeVisible({ timeout: 3000 })

    const closeBtn = shareModal.getByRole("button", { name: /fermer/i })
    await closeBtn.click()

    await expect(shareModal).not.toBeVisible({ timeout: 2000 })
  })
})
