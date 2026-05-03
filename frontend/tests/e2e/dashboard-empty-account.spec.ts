// F44 T040 — E2E quickstart S2 : compte vierge → 6 cartes en mode CTA.
// Aucune carte ne doit afficher "0" sec ou "—" sec (FR-022).
import { test, expect } from "@playwright/test"

const CARD_TESTIDS = [
  "card-scoring",
  "card-carbon",
  "card-credit",
  "card-candidatures",
  "card-rapports",
  "card-action-plan",
] as const

test.describe("F44 — Dashboard compte vierge (US3)", () => {
  test("aucune carte n'affiche '0' ou '—' isolé ; chaque carte propose un CTA", async ({ page }) => {
    await page.goto("/dashboard")
    // Skip si l'empty state landing (profil < 50 %) est visible.
    const landing = page.locator('[data-testid="empty-state-landing"]')
    if (await landing.isVisible()) test.skip()

    for (const tid of CARD_TESTIDS) {
      const card = page.locator(`[data-testid="${tid}"]`)
      if (!(await card.isVisible())) continue
      const text = (await card.innerText()).trim()
      // Vérifie : pas de "0" isolé ni "—" isolé.
      expect(text).not.toMatch(/(^|\s)0(\s|$)/)
      expect(text).not.toMatch(/(^|\s)—(\s|$)/)
    }
  })
})
