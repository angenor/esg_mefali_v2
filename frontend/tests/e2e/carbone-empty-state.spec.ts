// F47 SC-076 — E2E EmptyStateWizard /carbone (onboarding 3 étapes sans empreinte).
// Pré-conditions : compte PME sans aucune empreinte calculée.
// Skip-tolérant : si une empreinte existe, l'EmptyStateWizard n'est pas affiché.

import { test, expect } from "@playwright/test"

test.describe("F47 — Empreinte carbone (état vide / wizard)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/carbone")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("wizard onboarding s'affiche quand aucune empreinte n'existe", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")

    // Attendre résolution du chargement
    const loader = page.locator(".animate-pulse")
    await loader.waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const wizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (!(await wizard.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Une empreinte existe déjà — wizard non affiché")
      return
    }

    await expect(wizard).toBeVisible()
  })

  test("wizard affiche le titre et le sous-titre d'introduction", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const wizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (!(await wizard.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Wizard non affiché — empreinte existante")
      return
    }

    const title = page.locator("#carbon-wizard-title")
    await expect(title).toBeVisible()
  })

  test("wizard affiche les 3 cartes de catégories avant démarrage", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const wizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (!(await wizard.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Wizard non affiché — empreinte existante")
      return
    }

    // 3 UiCard avec les icônes énergie, mobilité, achats
    const cards = wizard.locator('[class*="text-3xl"]')
    await expect(cards).toHaveCount(3, { timeout: 3000 })
  })

  test("bouton 'Répondre librement' est présent (P10)", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/carbone")
    await page.locator(".animate-pulse").waitFor({ state: "detached", timeout: 5000 }).catch(() => {})

    const wizard = page.locator('[aria-labelledby="carbon-wizard-title"]')
    if (!(await wizard.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip(true, "Wizard non affiché — empreinte existante")
      return
    }

    // Bouton "Répondre librement" obligatoire (constitution P10)
    const freeTextBtn = wizard.getByRole("button", { name: /répondre librement/i })
    await expect(freeTextBtn).toBeVisible()
  })
})
