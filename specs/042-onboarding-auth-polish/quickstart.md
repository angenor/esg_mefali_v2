# Quickstart — F42 Onboarding & Auth UX Polish

Ce document explique comment tester localement la feature de bout en bout.

## Pré-requis

- Backend, frontend et Postgres opérationnels selon `CLAUDE.md` (3 terminaux).
- Migration `0042_user_preferences` appliquée : `cd backend && source .venv/bin/activate && alembic upgrade head`.
- Variables d'environnement requises côté backend :
  - `JWT_SECRET` — déjà existant
  - `PASSWORD_RESET_TTL_MINUTES=60` — à ajouter dans `.env` si non présent (défaut 60).
- Frontend : `cd frontend && pnpm install` pour récupérer `@zxcvbn-ts/core`, `@zxcvbn-ts/language-common`, `@zxcvbn-ts/language-fr` (ajoutés par cette feature).

## Étapes manuelles

### 1. Page publique → inscription

1. Ouvrir `http://localhost:3001/` en navigation privée (utilisateur non authentifié).
2. Vérifier : pitch + 3 bénéfices + témoignage + CTA `Créer un compte`.
3. Lighthouse a11y sur cette page → score ≥ 95.

### 2. Wizard register 3 étapes

1. Cliquer `Créer un compte`.
2. Step 1 — saisir un email valide, taper un mot de passe faible (`abc`) : barre rouge, bouton désactivé. Taper `Mefali2026!Vert` : barre verte (score 4), bouton activé. Cliquer `Suivant`.
3. Step 2 — taper "boula" dans le champ secteur : autocomplete F08 → choisir "Boulangerie". Saisir une raison sociale. Cliquer `Suivant`.
4. Step 3 — cocher CGU et RGPD, cliquer `Précédent` puis revenir : les données saisies sont préservées. Cliquer `Créer mon compte`.
5. Vérifier : redirection sur `/onboarding/welcome`.

### 3. Tour guidé

1. Sur `/onboarding/welcome`, cliquer `Démarrer le tour`. driver.js démarre sur la sidebar.
2. Cliquer `Passer` : `onboarding_state = skipped` (vérifier via `curl http://localhost:8010/me/preferences -b cookies.txt`).
3. Recharger la page : le tour ne redémarre pas automatiquement.
4. Aller dans le menu Aide → cliquer `Relancer le tour` (composant `OnboardingTourTrigger`). Le tour redémarre.
5. Aller jusqu'à la dernière étape, cliquer `Terminer` : `onboarding_state = completed`.
6. Tester avec `prefers-reduced-motion: reduce` activé (DevTools → Rendering → Emulate CSS media feature) : aucune animation au-delà d'un fondu instantané.

### 4. Empty state landing

1. Avec un compte au profil < 50 % : `/dashboard` → empty state visible (CTA + 3 cartes).
2. Compléter le profil entreprise jusqu'à dépasser 50 % de complétion.
3. Recharger `/dashboard` → tableau de bord standard, plus l'empty state.

### 5. Login + Rester connecté + deep link

1. Se déconnecter.
2. Aller directement sur `http://localhost:3001/profil` : redirection vers `/login?redirect=/profil`.
3. Saisir identifiants valides, cocher `Rester connecté`, cliquer `Se connecter`.
4. Vérifier : retour sur `/profil` (deep link respecté). Cookie `refresh_token` a `Max-Age` ≈ 30 jours (DevTools → Application → Cookies).
5. Tester sans cocher : `Max-Age` du cookie session courte (~ 1 h), expiration à fermeture du navigateur.

### 6. Mot de passe oublié → reset → reconnexion

1. `/forgot-password`, saisir un email **inexistant** : message générique. Saisir un email **existant** : même message générique, même délai.
2. Vérifier dans la base que `password_reset_tokens` contient une ligne avec `expires_at - issued_at == 60 min`.
3. Cliquer le bouton `Renvoyer` : il affiche `Renvoyer dans 60 s` et est désactivé. Recharger la page : le compteur reprend depuis localStorage.
4. Récupérer le lien (depuis logs backend ou table) et l'ouvrir : `/reset-password?token=...`.
5. Saisir un nouveau mot de passe (score ≥ 3, critères OK). Cliquer `Enregistrer`.
6. Vérifier : redirection vers `/login` avec message de succès. Toute session précédente est expirée — l'ouverture d'un autre onglet déjà connecté tombe en 401 à la prochaine requête.
7. Re-tenter d'utiliser le même token de reset : 400.
8. Émettre un autre token, attendre > 60 min (ou tricher avec freezegun en test) : 400.

### 7. Bandeau de vérification email

1. Avec un compte non vérifié : bandeau visible sur toutes les pages.
2. Cliquer `Renvoyer` : compteur 60 s.
3. Vérifier l'email manuellement (cliquer le lien) → recharger : bandeau disparu.

## Vérifications automatisées

```bash
# Backend tests
cd backend && source .venv/bin/activate
pytest tests/users/test_preferences.py -v
pytest tests/auth/test_password_reset_invalidation.py -v

# Coverage
pytest --cov=app.users --cov=app.auth --cov-report=term-missing

# Frontend tests
cd frontend
pnpm vitest run app/composables/__tests__/usePasswordStrength.test.ts
pnpm vitest run app/composables/__tests__/useOnboardingTour.test.ts

# E2E (Playwright)
pnpm playwright test tests/e2e/auth-register-wizard.spec.ts
pnpm playwright test tests/e2e/auth-reset-password.spec.ts
pnpm playwright test tests/e2e/onboarding-tour.spec.ts
pnpm playwright test tests/e2e/empty-state-landing.spec.ts
```

## Audit i18n FR (manuel ou CI)

```bash
# Heuristique : aucune chaîne anglaise hard-codée hors locales/fr.ts
grep -rEn '(Login|Sign[ -]?up|Password|Submit|Cancel|Welcome to)' frontend/app/pages frontend/app/components | grep -v locales/fr.ts
# devrait ne rien retourner.
```

## Critères de succès (rappel SC)

- SC-001 — wizard < 90 s sur 4/5 PME en test utilisateur.
- SC-002 — tour 100 % sans bug bloquant.
- SC-003 — reset 100 % sans régression.
- SC-004 — Lighthouse a11y ≥ 95 sur `/login` et `/register`.
- SC-005 — LCP `/login` < 1,2 s.
- SC-006 — 100 % messages d'erreur en français, anti-énumération respectée.
- SC-007 — aucune chaîne anglaise dans les pages de la feature.
- SC-008 — `prefers-reduced-motion: reduce` neutralise les animations.
