// F42 T057 — E2E login (Playwright)
import { test, expect } from "@playwright/test"

test.describe("F42 — Login polish", () => {
  test("deep link respecté", async ({ page }) => {
    await page.goto("/login?redirect=/parametres")
    // (suppose un compte existant en fixture)
    await page.fill("#login-email", "fixture@example.com")
    await page.fill("#login-pwd", "Mefali2026!Vert")
    await page.locator("button[type=submit]").click()
    await expect(page).toHaveURL(/\/parametres/)
  })

  test("rememberMe étend le cookie refresh à 30 jours", async ({ page, context }) => {
    await page.goto("/login")
    await page.fill("#login-email", "fixture@example.com")
    await page.fill("#login-pwd", "Mefali2026!Vert")
    await page.locator("input[type=checkbox]").check()
    await page.locator("button[type=submit]").click()

    const cookies = await context.cookies()
    const refresh = cookies.find((c) => c.name === "mefali_rt")
    expect(refresh).toBeDefined()
    // 30 jours ≈ 2_592_000 s
    expect(refresh!.expires).toBeGreaterThan(Date.now() / 1000 + 60 * 60 * 24 * 25)
  })

  test("toggle visibilité mot de passe", async ({ page }) => {
    await page.goto("/login")
    const pwd = page.locator("#login-pwd")
    await expect(pwd).toHaveAttribute("type", "password")
    await page.locator('button[aria-label="Afficher le mot de passe"]').click()
    await expect(pwd).toHaveAttribute("type", "text")
  })
})
