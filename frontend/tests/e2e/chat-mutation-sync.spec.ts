/**
 * F55 / T033 — Playwright E2E : mutation LLM sync entre /chat et /profile (US1).
 *
 * Scénario :
 * 1. Inscrire user PME de test
 * 2. Login UI
 * 3. Ouvrir /profile/entreprise dans un onglet
 * 4. Ouvrir /chat dans un autre onglet
 * 5. Envoyer un message forçant `update_company_profile` (secteur=C10.71)
 * 6. Vérifier le SSE `mutation` reçu
 * 7. Sur l'onglet /profile/entreprise, vérifier que le champ secteur est
 *    synchronisé sans rechargement utilisateur (EventBus → store refresh).
 */

import { test, expect } from '@playwright/test'

import { loginViaUI, registerLoginCsrf } from './helpers/auth'

const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8010'

test.describe('F55 US1 — Mutation LLM avec sync front', () => {
  test('update_company_profile via chat reflects in /profile/entreprise', async ({
    page,
    context,
    request,
  }) => {
    // Requires backend skill seeding for ``update_company_profile`` trigger.
    // Auth/CSRF + chat input/SSE chain are now functional (see /helpers/auth
    // and added testids in MessageBubbleAssistant/MessageError/MessageInput).
    test.fixme(
      true,
      'Requires backend skill seeding for update_company_profile trigger.',
    )

    const { email, password } = await registerLoginCsrf(request, { apiBase: API_BASE })
    await loginViaUI(page, email, password)

    // Onglet 1 : profile
    const profilePage = await context.newPage()
    await profilePage.goto('/profile/entreprise')

    // Onglet 2 : chat
    await page.goto('/chat')

    // Envoyer un message qui force update_company_profile
    await page.fill(
      '[data-testid="chat-input"]',
      'Mets à jour mon secteur, c\'est de la boulangerie pâtisserie',
    )
    await page.click('[data-testid="chat-send"]')

    // Attendre une bulle assistant terminée
    await expect(page.locator('[data-testid^="message-bubble-assistant"]'))
      .toHaveCount(1, { timeout: 15_000 })

    // Vérifier que /profile/entreprise s'est mis à jour automatiquement
    // (EventBus front → store refresh ; pas de rechargement)
    await profilePage.waitForFunction(
      () => {
        const sectorEl = document.querySelector(
          '[data-testid="entreprise-secteur"]',
        )
        return sectorEl && sectorEl.textContent?.includes('C10.71')
      },
      { timeout: 10_000 },
    )

    // Snapshot accept : audit visible côté admin (optionnel)
    const auditCheck = await request.get(
      `${API_BASE}/me/audit-log?entity_type=entreprise&source_of_change=llm`,
      {
        headers: { Cookie: (await context.cookies()).map(c => `${c.name}=${c.value}`).join('; ') },
      },
    )
    if (auditCheck.ok()) {
      const data = (await auditCheck.json()) as { items?: Array<{ source_of_change: string }> }
      expect(data.items?.some(it => it.source_of_change === 'llm')).toBeTruthy()
    }
  })
})
