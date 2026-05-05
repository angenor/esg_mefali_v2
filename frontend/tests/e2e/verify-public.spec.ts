// F49 T050 + T056 — E2E page publique /verify/[id] (Playwright)
//
// Couvre :
//  - actif → badge ✓
//  - révoqué → bandeau rouge above-the-fold
//  - inconnu → 404 sobre
//  - bascule FR/EN persistée par cookie
//  - rendu no-JS lisible (essentiel visible côté SSR)
//
// Pré-requis fixtures (alimentées par seed F30) :
//   E2E_VERIFY_ACTIVE_ID, E2E_VERIFY_REVOKED_ID
import { test, expect } from "@playwright/test"

const ACTIVE_ID = process.env.E2E_VERIFY_ACTIVE_ID ?? "active-fixture"
const REVOKED_ID = process.env.E2E_VERIFY_REVOKED_ID ?? "revoked-fixture"
const UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"

test.describe("F49 — page publique /verify", () => {
  test("attestation active → badge ✓ vert et identité visible", async ({
    page,
  }) => {
    await page.goto(`/verify/${ACTIVE_ID}`)
    const badge = page.getByTestId("signature-badge")
    await expect(badge).toBeVisible()
    await expect(badge).toHaveAttribute("data-valid", "true")
    await expect(page.getByTestId("identity-block")).toBeVisible()
    await expect(page.getByTestId("revoked-banner")).toHaveCount(0)
  })

  test("attestation révoquée → bandeau rouge above-the-fold", async ({
    page,
  }) => {
    await page.goto(`/verify/${REVOKED_ID}`)
    const banner = page.getByTestId("revoked-banner")
    await expect(banner).toBeVisible()
    // above-the-fold : bbox.y < hauteur viewport
    const box = await banner.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.y).toBeLessThan(800)
  })

  test("identifiant inconnu → 404 sobre", async ({ page }) => {
    const resp = await page.goto(`/verify/${UNKNOWN_ID}`)
    expect(resp?.status()).toBe(404)
    await expect(page.getByTestId("verify-error")).toBeVisible()
  })

  test("rendu no-JS reste lisible (SSR complet)", async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false })
    const page = await context.newPage()
    const resp = await page.goto(`/verify/${ACTIVE_ID}`)
    expect(resp?.ok()).toBe(true)
    const html = await page.content()
    expect(html).toContain("Signature")
    expect(html).toMatch(/identity-block|entity-legal|legal-name/i)
    await context.close()
  })

  test("bascule FR → EN persistée par cookie", async ({ page, context }) => {
    await page.goto(`/verify/${ACTIVE_ID}`)
    await page.waitForLoadState("networkidle")
    // Le clic met à jour le cookie et bascule la langue via réactivité Vue
    // (lang ref → t() réactif, sans reload page).
    await page.getByTestId("lang-en").click()
    // Attendre que le DOM reflète la langue anglaise.
    // On assertit le badge via aria-label (mis à jour par le computed label).
    await expect(page.getByTestId("lang-en")).toHaveAttribute("aria-pressed", "true", {
      timeout: 5_000,
    })
    await expect(page.getByTestId("signature-badge")).toHaveAttribute("aria-label", /Valid signature/i, {
      timeout: 5_000,
    })
    const cookies = await context.cookies()
    expect(cookies.find((c) => c.name === "mefali_verify_lang")?.value).toBe(
      "en",
    )
    await expect(page.getByTestId("identity-block")).toBeVisible()
  })
})
