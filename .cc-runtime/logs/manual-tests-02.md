# Manual tests — Feature 02 (Auth & RLS)

Format : `- [ ] T0XX — desc — comment vérifier`

## Frontend (UI réelle, navigateur)

- [ ] T031 — Test E2E Playwright /register — Backend up + frontend `pnpm dev` + Playwright config + spec à écrire dans `frontend/tests/e2e/register.spec.ts` (skipped car Playwright non installé en F02 ; couvert par tests backend integration de /auth/register).
- [ ] T040 — Test E2E Playwright /login — Idem ; vérifier login OK → redirection vers `/`, mauvais mdp → message générique.
- [~] T052 — Test E2E /admin-access — Après fix SSR + seed admin (admin@example.com) : PME loggée → /admin retourne 500 (`obj.hasOwnProperty is not a function`) au lieu de 404 ; admin loggé → même erreur 500. Cause : aucune page Vue `/admin/*.vue` n'existe (deferred dans F02/F06/F08), seul le middleware `admin.ts` est livré mais il n'est pas global et n'est référencé par aucune page. Ni le 404 strict (spec) ni la page admin OK ne sont observables tant que la page admin frontend n'est pas livrée. ⚠️ 2026-04-30.
- [x] T030 — Page register UX — http://localhost:3001/register → formulaire visible, soumission OK redirige vers `/`, erreur 409 "Cet email est déjà utilisé." affichée. ✅ 2026-04-30 agent-browser.
- [x] T038 — Page login UX — http://localhost:3001/login → soumission valide redirige vers `/`, mauvais mdp affiche "Identifiants invalides." ✅ 2026-04-30 agent-browser.
- [x] T062 — Page forgot-password UX — Soumission affiche "Si cette adresse correspond à un compte, vous recevrez un email…" (message neutre). ✅ 2026-04-30 agent-browser.
- [x] T063 — Page reset-password UX — Sans token → "Lien invalide." ; avec token invalide → "Lien invalide ou expiré. Demandez un nouvel email." ✅ 2026-04-30 agent-browser. Token valide non testé (pas d'envoi SMTP en dev).

## Frontend deps install

- [ ] T002 — `pnpm install` dans frontend pour installer `nuxt-security` (ajouté dans package.json) — vérifier que `pnpm dev` démarre sans erreur.

## Email réel (SMTP)

- [ ] T016 — Email reset password via SMTP — Configurer `EMAIL_BACKEND=smtp` + SMTP_* dans `.env`, soumettre `/auth/forgot-password` avec un email connu, vérifier que l'email est reçu (boîte mail réelle).

## Quickstart manuel

- [ ] T074 — Exécuter `specs/002-auth-roles-rls/quickstart.md` end-to-end et cocher SC-001..SC-009 (smoke tests métier).

## Performance

- [ ] T002 (perf) — Mesurer P95 /auth/login < 300 ms et P95 /me < 100 ms via outil HTTP load-test (k6 / hey / wrk) — non fait en F02 implementation, à valider lors du staging.

## Frontend coverage

- [ ] T072 — Mesure couverture frontend `pnpm test --coverage` — Pas de tests Vitest écrits pour les composables F02 ; à compléter (tâche déférée, non bloquante MVP).

## Frontend lint

- [ ] T002 (lint) — `cd frontend && pnpm lint` après `pnpm install` ; nuxt-security ajouté pourrait nécessiter mise à jour des configs.
