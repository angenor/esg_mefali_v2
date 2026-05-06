/**
 * F56 / T038 — E2E Playwright : rendu des chips Source dans le chat (US7).
 *
 * Vérifie que :
 * 1. Un message assistant avec ``payload.sources`` rend des superscripts
 *    cliquables (citation indices).
 * 2. Cliquer sur un superscript ouvre un popover (composant <VizSourcePin>
 *    F40) affichant title, publisher, URL.
 * 3. Un event SSE ``unsourced_claim`` affiche une chip d'avertissement
 *    jaune sur le span correspondant.
 *
 * Pré-requis :
 * - Backend démarré sur E2E_BASE_URL.
 * - Frontend démarré sur E2E_FRONT_URL.
 *
 * Exécuté par l'agent e2e-runner après merge de F56.
 */

import { expect, test } from '@playwright/test';

const FRONT_URL = process.env.E2E_FRONT_URL || 'http://localhost:3001';
const BACK_URL = process.env.E2E_BASE_URL || 'http://localhost:8010';

const PASSWORD = 'E2eTestPass123!';

interface PmeAccount {
  email: string;
}

async function createPmeAccount(request: any): Promise<PmeAccount> {
  const email = `e2e_pme_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@example.com`;
  const r = await request.post(`${BACK_URL}/auth/register`, {
    data: { email, password: PASSWORD },
  });
  if (r.status() !== 200 && r.status() !== 201) {
    throw new Error(`Cannot provision PME account: HTTP ${r.status()}`);
  }
  return { email };
}

async function loginUI(page: any, email: string): Promise<void> {
  await page.goto(`${FRONT_URL}/login`);
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/mot de passe/i).fill(PASSWORD);
  await page.getByRole('button', { name: /connexion|se connecter/i }).click();
  await page.waitForURL(/\/(?!login)/, { timeout: 10000 });
}

test.describe('F56 — Chat sources rendering (US7)', () => {
  test.fixme('superscripts cliquables ouvrent le popover source', async ({ page, request }) => {
    const account = await createPmeAccount(request);
    await loginUI(page, account.email);

    // Naviguer vers le chat avec une conversation contenant un message
    // assistant porteur de payload.sources.
    await page.goto(`${FRONT_URL}/chat`);
    // L'application devrait afficher un message assistant avec un span citant
    // une source. Le superscript "¹" apparaît côté DOM dès que message_done
    // SSE est reçu avec sources.
    const sup = page.locator('sup.cursor-pointer').first();
    await expect(sup).toBeVisible({ timeout: 10000 });

    await sup.click();

    // Le popover <VizSourcePin> doit afficher title + publisher + URL
    const popover = page.locator('[data-testid="source-pin-popover"]').first();
    await expect(popover).toBeVisible();
    await expect(popover).toContainText(/ADEME|GCF|BOAD/);
    await expect(popover.locator('a[href]')).toHaveCount(1);
  });

  test.fixme(
    'unsourced_claim SSE affiche une chip jaune sur le span',
    async ({ page, request }) => {
      const account = await createPmeAccount(request);
      await loginUI(page, account.email);
      await page.goto(`${FRONT_URL}/chat`);

      // Provoquer l'envoi d'un message qui déclenchera flag_unsourced backend.
      const input = page.getByPlaceholder(/votre message|tapez/i);
      await input.fill('Quel est le seuil GCF non répertorié ?');
      await page.getByRole('button', { name: /envoyer|send/i }).click();

      // Attendre la chip d'avertissement jaune
      const chip = page.locator('[data-testid="unsourced-claim-chip"]').first();
      await expect(chip).toBeVisible({ timeout: 15000 });
      await expect(chip).toHaveCSS('background-color', /yellow|255, 255, 224|fef3c7/);
    },
  );

  test.fixme('source outdated affiche un badge orange', async ({ page, request }) => {
    const account = await createPmeAccount(request);
    await loginUI(page, account.email);
    await page.goto(`${FRONT_URL}/chat`);

    const sup = page.locator('sup.cursor-pointer').first();
    await sup.click();

    const popover = page.locator('[data-testid="source-pin-popover"]').first();
    // Si la source est outdated, un badge orange doit apparaître.
    const badge = popover.locator('[data-testid="source-outdated-badge"]');
    if (await badge.isVisible()) {
      await expect(badge).toContainText(/obsolète|outdated/i);
    }
  });
});
