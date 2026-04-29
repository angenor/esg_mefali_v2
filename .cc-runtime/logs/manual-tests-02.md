# Manual tests — Feature 02 (Auth & RLS)

Format : `- [ ] T0XX — desc — comment vérifier`

## Frontend (UI réelle, navigateur)

- [ ] T031 — Test E2E Playwright /register — Backend up + frontend `pnpm dev` + Playwright config + spec à écrire dans `frontend/tests/e2e/register.spec.ts` (skipped car Playwright non installé en F02 ; couvert par tests backend integration de /auth/register).
- [ ] T040 — Test E2E Playwright /login — Idem ; vérifier login OK → redirection vers `/`, mauvais mdp → message générique.
- [ ] T052 — Test E2E /admin-access — Vérifier login PME tentant /admin → 404 ; login admin → page admin OK.
- [ ] T030 — Page register UX — `pnpm dev` → http://localhost:3000/register → formulaire visible, soumission OK redirige vers `/`, erreur 409 affichée si email déjà utilisé.
- [ ] T038 — Page login UX — http://localhost:3000/login → soumission valide redirige vers `/` (ou vers `?next=...`), mauvais mdp affiche "Identifiants invalides".
- [ ] T062 — Page forgot-password UX — Soumission affiche message neutre que l'email existe ou non.
- [ ] T063 — Page reset-password UX — Avec `?token=…` valide, formulaire accepte un nouveau mdp, redirige vers `/login` au succès, affiche erreur si token expiré.

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
