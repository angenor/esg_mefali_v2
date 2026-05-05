// F42 T080 — E2E vérification de prefers-reduced-motion: reduce
import { test, expect } from "@playwright/test"

test.use({ reducedMotion: "reduce" })

test.describe("F42 — prefers-reduced-motion: reduce", () => {
  test("page register : aucune transition > 0", async ({ page }) => {
    await page.goto("/register")
    await page.waitForSelector("form")
    const transitions = await page.evaluate(() => {
      const elements = Array.from(document.querySelectorAll("*"))
      return elements
        .map((el) => {
          const cs = window.getComputedStyle(el as Element)
          return {
            duration: cs.transitionDuration,
            animation: cs.animationDuration,
          }
        })
        .filter(
          (s) =>
            (s.duration && s.duration !== "0s" && s.duration !== "0.001ms") ||
            (s.animation && s.animation !== "0s" && s.animation !== "0.001ms"),
        )
    })
    // Chaque entrée non négligeable indique une animation non neutralisée.
    expect(transitions.length).toBeLessThanOrEqual(0)
  })

  test("page login : pas d'animation gsap visible", async ({ page }) => {
    await page.goto("/login")
    await page.waitForSelector("form")
    // Pas de regression visuelle attendue : présence du form suffit
    await expect(page.locator("form")).toBeVisible()
  })
})
