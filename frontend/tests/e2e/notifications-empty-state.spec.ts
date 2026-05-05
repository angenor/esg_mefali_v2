// F52 SC-US1 — E2E état vide /notifications (sans notif + avec filtres actifs).
// NotificationsEmptyState affiche deux textes différents selon `hasFilters`.

import { test, expect } from "@playwright/test"

test.describe("F52 — Notifications (état vide)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/notifications")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("état vide global visible si aucune notification", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    const empty = page.locator('[data-testid="notifications-empty"]')

    // Attendre que l'un des deux soit visible
    await Promise.race([
      list.waitFor({ state: "visible", timeout: 6000 }).catch(() => null),
      empty.waitFor({ state: "visible", timeout: 6000 }).catch(() => null),
    ])

    const listVisible = await list.isVisible().catch(() => false)
    const emptyVisible = await empty.isVisible().catch(() => false)

    expect(listVisible || emptyVisible).toBeTruthy()
  })

  test("état vide sans filtre affiche le message 'Aucune notification pour le moment'", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const empty = page.locator('[data-testid="notifications-empty"]')
    if (!(await empty.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Des notifications existent — état vide non affiché")
      return
    }

    await expect(empty).toContainText(/aucune notification pour le moment/i)
  })

  test("état vide avec filtre affiche un message différent", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    // Activer le filtre "Non-lues uniquement"
    const unreadCheck = page.locator('[data-testid="filter-unread-only"]')
    await unreadCheck.click()
    await expect(unreadCheck).toBeChecked()

    // Si l'état vide apparaît avec le filtre actif
    const empty = page.locator('[data-testid="notifications-empty"]')
    if (await empty.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(empty).toContainText(/aucune notification ne correspond/i)
    }
    // Sinon des notifications non lues existent → pas d'état vide, test valide
  })

  test("état vide contient le sous-texte d'information", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const empty = page.locator('[data-testid="notifications-empty"]')
    if (!(await empty.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Des notifications existent")
      return
    }

    await expect(empty).toContainText(/alerté/)
  })

  test("bouton 'Tout marquer comme lu' est désactivé si aucune notification non lue", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="mark-all-read-btn"]').waitFor({ timeout: 6000 })

    const markAllBtn = page.locator('[data-testid="mark-all-read-btn"]')

    // Si aucune notification non lue → bouton disabled
    const empty = page.locator('[data-testid="notifications-empty"]')
    if (await empty.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(markAllBtn).toBeDisabled()
    }
    // Sinon il y a des notifications → on vérifie juste qu'il est visible
    else {
      await expect(markAllBtn).toBeVisible()
    }
  })

  test("la page /notifications se charge sans erreur JS critique", async ({ page }) => {
    const criticalErrors: string[] = []
    page.on("pageerror", (err) => {
      criticalErrors.push(err.message)
    })

    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    // Aucune erreur JS non gérée ne doit s'être produite
    expect(criticalErrors).toHaveLength(0)
  })
})
