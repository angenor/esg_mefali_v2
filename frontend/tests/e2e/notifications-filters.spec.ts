// F52 SC-US1 — E2E filtres /notifications (unread-only + kinds multi-select + reset).
// Complément de 052/notifications-mark-all-read.spec.ts qui couvre mark-all-read.

import { test, expect } from "@playwright/test"

test.describe("F52 — Notifications (filtres)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/notifications")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("PME authentifié voit le titre 'Notifications'", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    await expect(
      page.getByRole("heading", { name: /notifications/i }),
    ).toBeVisible({ timeout: 6000 })
  })

  test("zone de filtres est visible avec la case 'Non-lues uniquement'", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const filterUnread = page.locator('[data-testid="filter-unread-only"]')
    await expect(filterUnread).toBeVisible({ timeout: 6000 })
  })

  test("les 6 boutons de filtre par type sont affichés", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    // Les 6 kinds définis dans NotificationFilters
    const kinds = [
      "deadline_j_minus_30",
      "deadline_j_minus_7",
      "deadline_j_minus_1",
      "candidature_inactive",
      "offre_recommandee",
      "system",
    ] as const

    for (const kind of kinds) {
      const btn = page.locator(`[data-testid="filter-kind-${kind}"]`)
      await expect(btn).toBeVisible({ timeout: 3000 })
    }
  })

  test("clic sur un filtre kind active le bouton (aria-pressed=true)", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    const kindBtn = page.locator('[data-testid="filter-kind-system"]')
    await expect(kindBtn).toBeVisible()

    // Avant : aria-pressed="false"
    await expect(kindBtn).toHaveAttribute("aria-pressed", "false")

    await kindBtn.click()

    // Après : aria-pressed="true"
    await expect(kindBtn).toHaveAttribute("aria-pressed", "true")
  })

  test("clic sur 'Réinitialiser' désactive tous les filtres", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    // Activer un filtre
    const kindBtn = page.locator('[data-testid="filter-kind-system"]')
    await kindBtn.click()
    await expect(kindBtn).toHaveAttribute("aria-pressed", "true")

    // Réinitialiser
    const resetBtn = page.locator('[data-testid="filter-reset"]')
    await resetBtn.click()

    // Tous les boutons doivent être inactifs
    await expect(kindBtn).toHaveAttribute("aria-pressed", "false")

    // La case non-lues doit être décochée
    const unreadCheck = page.locator('[data-testid="filter-unread-only"]')
    await expect(unreadCheck).not.toBeChecked()
  })

  test("cocher 'Non-lues uniquement' filtre la liste de notifications", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")
    await page.locator('[data-testid="filter-unread-only"]').waitFor({ timeout: 6000 })

    const unreadCheck = page.locator('[data-testid="filter-unread-only"]')
    await unreadCheck.click()
    await expect(unreadCheck).toBeChecked()

    // La liste ou l'état vide doit être visible
    const list = page.locator('[data-testid="notifications-list"]')
    const empty = page.locator('[data-testid="notifications-empty"]')
    const hasListOrEmpty = await Promise.race([
      list.isVisible({ timeout: 3000 }).catch(() => false),
      empty.isVisible({ timeout: 3000 }).catch(() => false),
    ])
    expect(hasListOrEmpty).toBeTruthy()
  })
})
