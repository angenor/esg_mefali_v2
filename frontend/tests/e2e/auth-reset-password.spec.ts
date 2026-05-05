// F42 T058 — E2E reset password (Playwright)
import { test, expect } from "@playwright/test"

test.describe("F42 — Reset password flow", () => {
  test("forgot retourne le même message pour email connu et inconnu", async ({ page }) => {
    await page.goto("/forgot-password")
    await page.fill("#fp-email", "known@example.com")
    await page.locator("button[type=submit]").click()
    const msgKnown = await page.locator('[role=status]').first().textContent()

    await page.goto("/forgot-password")
    await page.fill("#fp-email", `unknown_${Date.now()}@example.com`)
    await page.locator("button[type=submit]").click()
    const msgUnknown = await page.locator('[role=status]').first().textContent()

    expect(msgKnown?.trim()).toEqual(msgUnknown?.trim())
  })

  test("ResendCooldownButton verrouille 60 s", async ({ page }) => {
    await page.goto("/forgot-password")
    await page.fill("#fp-email", "known@example.com")
    await page.locator("button[type=submit]").click()
    const resend = page.locator("button", { hasText: /Renvoyer/ })
    await resend.click()
    await expect(resend).toBeDisabled()
    await expect(resend).toContainText(/Renvoyer dans \d+/)
  })

  test("token invalide → page d'erreur dédiée", async ({ page }) => {
    await page.goto("/reset-password?token=this-is-not-a-real-token-12345678")
    await page.fill("#rp-pwd", "Mefali2026!Vert")
    await page.fill("#rp-pwd2", "Mefali2026!Vert")
    await page.locator("button[type=submit]").click()
    await expect(page.locator("h1")).toContainText("Lien invalide")
  })
})
