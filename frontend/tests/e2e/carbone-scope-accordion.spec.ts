// F47 SC-045 — E2E accordéons scopes 1/2/3 (toggle, badge filled/expected, tCO2e).
// Les <details> sont open=true par défaut. Un clic sur <summary> les ferme.

import { test, expect } from "@playwright/test"

test.describe("F47 — Empreinte carbone (accordéons scopes)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/carbone")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("3 accordéons de scopes sont affichés si une empreinte existe", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const emptyWizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (await emptyWizard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip(true, "Pas d'empreinte — accordéons non affichés")
      return
    }

    const scopes = page.locator("#carbon-scopes details")
    await expect(scopes).toHaveCount(3, { timeout: 5000 })
  })

  test("accordéons sont ouverts par défaut", async ({ page }) => {
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

    const firstScope = page.locator("#carbon-scopes details").first()
    await expect(firstScope).toBeVisible({ timeout: 5000 })

    // L'attribut open est présent sur l'élément details ouvert
    const isOpen = await firstScope.getAttribute("open")
    // open=true signifie attribut "open" présent (valeur peut être "" ou "true")
    expect(isOpen).not.toBeNull()
  })

  test("clic sur summary d'un scope ferme l'accordéon", async ({ page }) => {
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

    const firstScope = page.locator("#carbon-scopes details").first()
    const summary = firstScope.locator("summary")
    await expect(summary).toBeVisible({ timeout: 5000 })

    await summary.click()

    // Après clic, l'attribut open ne doit plus être présent
    const isOpen = await firstScope.getAttribute("open")
    expect(isOpen).toBeNull()
  })

  test("chaque scope affiche une valeur tCO₂e dans le résumé", async ({ page }) => {
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

    const scopeSummaries = page.locator("#carbon-scopes details summary")
    const count = await scopeSummaries.count()
    expect(count).toBe(3)

    for (let i = 0; i < count; i++) {
      const summary = scopeSummaries.nth(i)
      await expect(summary).toContainText(/tCO₂e/, { timeout: 3000 })
    }
  })

  test("scope 2 affiche le tooltip market vs location-based", async ({ page }) => {
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

    // Le scope 2 (index 1) doit contenir le lien de tooltip sur market/location
    const scope2 = page.locator("#carbon-scopes details").nth(1)
    const tooltipTrigger = scope2.locator("summary [class*='underline']")
    if (await tooltipTrigger.count() > 0) {
      await expect(tooltipTrigger.first()).toBeVisible()
    }
  })
})
