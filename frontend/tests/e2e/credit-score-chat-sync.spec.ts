// F48 T110 [US9] — Chat sync: EventBus internal singleton (mitt) inaccessible from Playwright.
// Strategy: The EventBus (useChatEventBus) is a pure in-memory mitt singleton — it cannot be
// triggered from page.evaluate() without exposing an explicit window bridge.
// US9 sync is covered indirectly by credit-score-edit-data-flow.spec.ts (T080/US5) which
// exercises the full mutation → EventBus → store refresh cycle via the CreditDataDrawer.
// This file documents the limitation and skips accordingly.
import { test } from '@playwright/test'

test.describe('Credit Score — Chat sync (F48 T110 US9)', () => {
  test('EventBus entity_updated{credit_score} → gauge mise à jour sans rechargement', async ({ page }) => {
    test.skip(
      true,
      [
        'US9 EventBus sync is implemented via useChatEventBus (mitt singleton).',
        'The bus is purely in-memory and not exposed on window — Playwright cannot',
        'dispatch events to it directly via page.evaluate().',
        'Coverage: US9 is indirectly verified by T080 (credit-score-edit-data-flow.spec.ts)',
        'which triggers the full mutation → EventBus emit → store.applyRecomputeResult cycle.',
        'A dedicated integration test would require window.__chatEventBus exposure in dev mode.',
        'Tracking issue: add window.__chatEventBus = bus in dev/test build to enable E2E US9.',
      ].join(' '),
    )
    // Intentionally empty — see skip reason above.
    void page
  })
})
