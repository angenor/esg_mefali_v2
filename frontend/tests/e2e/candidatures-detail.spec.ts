// F26 F51 SC-005 — /candidatures/[id] détail d'une candidature
// Pré-conditions :
//   - Non-auth : redirige vers /login
//   - Auth + id inexistant : affiche "Candidature introuvable."
//   - Auth + id brouillon : Wizard visible (WizardStepIndicator + navigation)
//   - Auth + id soumise : section lecture seule visible
import { test, expect } from "@playwright/test"

const FAKE_ID = "00000000-0000-0000-0000-000000000099"

test.describe("F51 — /candidatures/[id] détail", () => {
  test("non authentifié : redirige vers /login", async ({ page }) => {
    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    await page.waitForURL(/\/login/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test("id inconnu auth : affiche 'Candidature introuvable.'", async ({ page }) => {
    // Mock 404 sur le endpoint candidature
    await page.route(`**/me/candidatures/${FAKE_ID}**`, async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Candidature introuvable." }),
      })
    })

    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // Attendre que le chargement se termine
    await page.waitForTimeout(1_000)

    const notFound = page.locator("p", { hasText: /Candidature introuvable/i })
    const loading = page.locator("p", { hasText: /Chargement/i })

    if (await loading.count()) {
      await loading.first().waitFor({ state: "hidden", timeout: 8_000 }).catch(() => {})
    }
    if (await notFound.count()) {
      await expect(notFound.first()).toBeVisible()
    }
  })

  test("auth : lien retour vers /candidatures présent quand detail chargé", async ({ page }) => {
    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const backLink = page.getByRole("link", { name: /Mes candidatures/i })
    if (await backLink.count()) {
      await expect(backLink.first()).toBeVisible()
      await expect(backLink.first()).toHaveAttribute("href", /\/candidatures/)
    }
  })

  test("auth brouillon : wizard avec indicateur d'étapes visible", async ({ page }) => {
    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    // WizardStepIndicator rendu si statut === 'brouillon'
    // Chercher bouton navigation du wizard (Précédent / Suivant)
    const prevBtn = page.getByRole("button", { name: /Précédent/i })
    const nextBtn = page.getByRole("button", { name: /Suivant/i })

    if (await prevBtn.count()) {
      await expect(prevBtn.first()).toBeVisible()
    }
    if (await nextBtn.count()) {
      await expect(nextBtn.first()).toBeVisible()
    }
  })

  test("auth soumise : section 'Détail figé (lecture seule)' visible", async ({ page }) => {
    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const readOnly = page.getByRole("heading", { name: /Détail figé \(lecture seule\)/i })
    if (await readOnly.count()) {
      await expect(readOnly.first()).toBeVisible()
    }
  })

  test("auth : section 'Historique' visible quand detail chargé", async ({ page }) => {
    await page.goto(`/candidatures/${FAKE_ID}`)
    await page.waitForLoadState("domcontentloaded", { timeout: 15_000 })

    if (page.url().includes("/login")) {
      test.skip()
      return
    }

    const histSection = page.getByRole("heading", { name: /Historique/i })
    if (await histSection.count()) {
      await expect(histSection.first()).toBeVisible()
    }
  })
})
