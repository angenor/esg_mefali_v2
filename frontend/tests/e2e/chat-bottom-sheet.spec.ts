/**
 * F55 / T061 — Playwright E2E : bottom sheet flow ASK (US2 / SC-001).
 *
 * Scénario :
 * 1. Inscrire un utilisateur PME de test via l'API
 * 2. Login UI
 * 3. Aller dans /chat
 * 4. Envoyer un message qui force `ask_qcu`
 * 5. Vérifier que la bottom sheet F39 s'ouvre (data-testid="chat-bottom-sheet")
 *    avec le rôle dialog et que la bulle assistant ne contient PAS d'input
 *    interactif (P10).
 * 6. Sélectionner une option et soumettre
 * 7. Vérifier que le tour suivant s'enchaîne correctement
 */

import { test, expect } from '@playwright/test'

import { loginViaUI, registerLoginCsrf } from './helpers/auth'

const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8010'

test.describe('F55 US2 — Bottom sheet ASK flow', () => {
  test('ask_qcu opens bottom sheet (P10), bubble stays display-only', async ({
    page,
    request,
  }) => {
    // Necessary backend skill (ask_qcu trigger) is not seeded in dev. Keep
    // quarantined until a deterministic forme-juridique skill ships, OR until
    // we can assert via SSE intercept rather than UI bottom sheet rendering.
    test.fixme(
      true,
      'Requires backend skill seeding for ask_qcu trigger ; see /skills/ task',
    )

    const { email, password } = await registerLoginCsrf(request, { apiBase: API_BASE })
    await loginViaUI(page, email, password)

    await page.goto('/chat')

    // Envoyer un message qui force ask_qcu (configuration backend nécessaire
    // côté seeds — fallback : intercepter SSE)
    await page.fill('[data-testid="chat-input"]', 'Quelle est ma forme juridique ?')
    await page.click('[data-testid="chat-send"]')

    // Vérifier ouverture bottom sheet
    const sheet = page.locator('[data-testid="chat-bottom-sheet"]')
    await expect(sheet).toBeVisible({ timeout: 10_000 })
    await expect(sheet).toHaveAttribute('role', 'dialog')

    // Vérifier que la bulle assistant ne contient PAS d'input interactif (P10)
    const lastBubble = page.locator('[data-testid^="message-bubble-assistant"]').last()
    await expect(lastBubble.locator('input[type="radio"], input[type="checkbox"]'))
      .toHaveCount(0)

    // Sélectionner une option et soumettre
    const firstOption = sheet.locator('input[type="radio"]').first()
    await firstOption.check()
    await sheet.locator('[data-testid="bottom-sheet-submit"]').click()

    // Vérifier que la sheet se ferme
    await expect(sheet).toBeHidden({ timeout: 5_000 })

    // Vérifier qu'une nouvelle bulle assistant apparaît (tour suivant)
    await expect(page.locator('[data-testid^="message-bubble-assistant"]'))
      .toHaveCount(2, { timeout: 10_000 })
  })

  test('repondre librement button switches to free text', async ({
    page,
    request,
  }) => {
    // Same skill seeding gap as previous test ; ask_qcu trigger isn't seeded.
    test.fixme(
      true,
      'Requires backend skill seeding for ask_qcu trigger ; see /skills/ task',
    )

    const { email, password } = await registerLoginCsrf(request, { apiBase: API_BASE })
    await loginViaUI(page, email, password)

    await page.goto('/chat')

    await page.fill('[data-testid="chat-input"]', 'Donne-moi une question fermée')
    await page.click('[data-testid="chat-send"]')

    const sheet = page.locator('[data-testid="chat-bottom-sheet"]')
    await expect(sheet).toBeVisible({ timeout: 10_000 })

    // Bouton "Répondre librement" doit exister (P10 garantie)
    const freeBtn = sheet.locator('[data-testid="bottom-sheet-freetext"]')
    await expect(freeBtn).toBeVisible()
    await freeBtn.click()

    await expect(sheet).toBeHidden({ timeout: 5_000 })
    // L'input principal doit avoir le focus pour répondre librement
    await expect(page.locator('[data-testid="chat-input"]')).toBeFocused({
      timeout: 3_000,
    })
  })
})
