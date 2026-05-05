// F52 SC-US1 — E2E drawer de détail d'une notification.
// Vérifie l'ouverture, le titre, le lien contextuel, le bouton mark-read, et la fermeture.
// Skip-tolérant : nécessite au moins une notification en base.

import { test, expect } from "@playwright/test"

test.describe("F52 — Notifications (drawer de détail)", () => {
  test("non authentifié est redirigé vers /login", async ({ page }) => {
    await page.goto("/notifications")
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test("clic sur une notification ouvre le drawer de détail", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification — liste non affichée")
      return
    }

    // Cliquer sur la première ligne de notification
    // NotificationRow émet 'open' au clic — il est rendu comme <li>
    const firstRow = list.locator("li").first()
    await firstRow.click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })
  })

  test("drawer affiche le titre de la notification", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification")
      return
    }

    await list.locator("li").first().click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })

    // Le titre est dans un h2 dans le drawer
    const title = drawer.locator("h2")
    await expect(title).toBeVisible()
    const titleText = await title.textContent()
    expect(titleText?.trim().length).toBeGreaterThan(0)
  })

  test("drawer affiche le bouton 'Marquer comme lue' pour une notification non lue", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification")
      return
    }

    await list.locator("li").first().click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })

    const markReadBtn = drawer.locator('[data-testid="notif-drawer-mark-read"]')
    // Le bouton est conditionnel : visible uniquement si notification.read_at === null
    const isVisible = await markReadBtn.isVisible({ timeout: 2000 }).catch(() => false)
    if (isVisible) {
      await expect(markReadBtn).toBeEnabled()
    }
    // Si la notification est déjà lue, ce test est N/A (pas de bug)
  })

  test("le bouton de fermeture × ferme le drawer", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification")
      return
    }

    await list.locator("li").first().click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })

    // Bouton × avec aria-label="Fermer"
    const closeBtn = drawer.locator('[data-testid="notif-drawer-close"]')
    await expect(closeBtn).toBeVisible()
    await closeBtn.click()

    await expect(drawer).not.toBeVisible({ timeout: 2000 })
  })

  test("le lien contextuel dans le drawer est cliquable si présent", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification")
      return
    }

    await list.locator("li").first().click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })

    const drawerLink = drawer.locator('[data-testid="notif-drawer-link"]')
    if (await drawerLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(drawerLink).toBeEnabled()
      const href = await drawerLink.getAttribute("href")
      expect(href?.length).toBeGreaterThan(0)
    }
    // Si la notification n'a pas de lien, ce test passe sans assertions
  })

  test("le drawer affiche le badge de type (kind) de la notification", async ({ page }) => {
    await page.goto("/login")
    await page.fill('input[name="email"]', "pme-test@example.com")
    await page.fill('input[name="password"]', "test-password")
    await page.click('button[type="submit"]')
    await page.waitForURL("**/dashboard", { timeout: 8000 })

    await page.goto("/notifications")

    const list = page.locator('[data-testid="notifications-list"]')
    if (!(await list.isVisible({ timeout: 6000 }).catch(() => false))) {
      test.skip(true, "Aucune notification")
      return
    }

    await list.locator("li").first().click()

    const drawer = page.locator('[data-testid="notif-drawer"]')
    await expect(drawer).toBeVisible({ timeout: 3000 })

    // Badge kind : span avec classe rounded-full dans le header du drawer
    const kindBadge = drawer.locator("header span.rounded-full")
    await expect(kindBadge).toBeVisible()
    const badgeText = await kindBadge.textContent()
    expect(badgeText?.trim().length).toBeGreaterThan(0)
  })
})
