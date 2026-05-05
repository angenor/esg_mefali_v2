# E2E F52 — Notifications, Paramètres, Exports & Extension

Suite de tests Playwright pour la feature 052.

## Spec couverte

- SC-001 / SC-002 : `notifications-mark-all-read.spec.ts`
- SC-003 : `email-change-reverif.spec.ts`
- SC-005 : `account-deletion-30d.spec.ts`
- SC-006 / SC-009 : `exports-history.spec.ts`
- SC-007 / SC-008 : `extension-sidepanel.spec.ts`
- A11y / Lighthouse / cloisonnement : `a11y.spec.ts`,
  `extension-tenant-isolation.spec.ts`

## Configuration

Le `playwright.config.ts` racine charge automatiquement les tests sous
`tests/e2e/` ET `e2e/052/` (extension du `testMatch`).

```bash
pnpm playwright test e2e/052/notifications-mark-all-read.spec.ts
```
