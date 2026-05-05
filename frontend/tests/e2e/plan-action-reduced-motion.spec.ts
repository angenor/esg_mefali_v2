// F45 T022 — E2E prefers-reduced-motion.
import { test, expect } from "@playwright/test"
import { seedPmeWithActionPlan } from "./helpers/seed-action-plan"

test("timeline rend sans animation si reduced-motion", async ({ page, browserName: _ }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await seedPmeWithActionPlan(page)
  await page.goto("/plan-action")
  const timeline = page.locator('[data-testid="timeline"]')
  await timeline.waitFor()
  await expect(timeline).toHaveClass(/pa-timeline--no-anim/)
})
