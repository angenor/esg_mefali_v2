// F43 T017 — E2E /profil/entreprise : autosave + reload persistence + toast.
//
// Pré-requis : un compte fixture connecté avec entreprise pré-existante.
// Le test ouvre la page, modifie la raison sociale, attend 800 ms,
// recharge, puis vérifie que la valeur persiste et qu'un toast "Enregistré"
// est apparu.
import { test, expect } from "@playwright/test"

test.describe("F43 — Profil entreprise autosave", () => {
  test("modifier raison sociale → toast → reload persiste", async ({ page }) => {
    // Login fixture (réutilise les helpers F42).
    await page.goto("/login")
    await page.fill("#login-email", "fixture@example.com")
    await page.fill("#login-pwd", "Mefali2026!Vert")
    await page.locator("button[type=submit]").click()
    await page.waitForURL(/\/(dashboard|profil)/)

    await page.goto("/profil/entreprise")
    await expect(page.getByRole("heading", { name: /Profil entreprise/ })).toBeVisible()

    // Bascule la section Identité en édition et modifie la raison sociale.
    const identiteCard = page.locator(".section-card").filter({ hasText: "Identité" })
    await identiteCard.getByRole("button", { name: /Modifier/ }).click()
    const NEW_NAME = `ACME ${Date.now()}`
    await identiteCard.locator('input[type="text"]').first().fill(NEW_NAME)

    // Attendre debounce 800 ms + roundtrip.
    await page.waitForTimeout(1500)
    await expect(page.getByText("Enregistré")).toBeVisible()

    // Reload + vérifie persistence.
    await page.reload()
    await expect(identiteCard.getByText(NEW_NAME)).toBeVisible()
  })
})
