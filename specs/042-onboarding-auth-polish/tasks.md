# Tasks: Onboarding Tour & Auth UX Polish (F42)

**Branch**: `042-onboarding-auth-polish`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Data model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/](./contracts/) · **Quickstart**: [quickstart.md](./quickstart.md)

> Tasks numérotées T001…Tnnn ; `[P]` = parallélisable (fichier distinct, aucune dépendance sur une tâche en cours) ; `[USx]` = appartient à la User Story x.
> **Tests OPTIONNELS** : la spec ne demande pas TDD, mais la règle commune `~/.claude/rules/common/testing.md` exige 80 % de couverture. Les tâches de test sont incluses **dans chaque user story** pour garantir l'indépendance et le coverage.

---

## Phase 1 — Setup (infrastructure partagée)

- [X] T00- [ ] T001_ Ajouter les dépendances frontend `@zxcvbn-ts/core`, `@zxcvbn-ts/language-common`, `@zxcvbn-ts/language-fr` dans `frontend/package.json` puis `pnpm install`
- [X] T00- [ ] T002_ [P] Créer le dossier `frontend/app/locales/` et le fichier squelette `frontend/app/locales/fr.ts` avec `export default { } as const`
- [X] T00- [ ] T003_ [P] Créer le dossier `frontend/app/components/auth/`, `frontend/app/components/onboarding/`, `frontend/app/components/common/`, `frontend/app/components/home/` (placeholders `.gitkeep` si vides)
- [X] T00- [ ] T004_ [P] Ajouter les illustrations optimisées `frontend/app/assets/images/auth-illustration.webp` et `auth-illustration.avif` (≤ 60 KB chacune, 800×800), placeholder validé par le design
- [X] T00- [ ] T005_ [P] Créer `frontend/app/assets/css/tour.css` avec overrides driver.js (variables couleurs, padding, et règle `@media (prefers-reduced-motion: reduce)` qui force `transition: none`)
- [X] T00- [ ] T006_ Vérifier dans `backend/.env.example` la présence de `PASSWORD_RESET_TTL_MINUTES=60` ; l'ajouter sinon
- [X] T00- [ ] T007_ [P] Vérifier que `backend/app/config.py` expose `PASSWORD_RESET_TTL_MINUTES: int = 60` via `Settings`, l'ajouter sinon

---

## Phase 2 — Foundational (préalables bloquants pour toutes les user stories)

**But** : poser les fondations data + i18n + composables transverses utilisés par les 6 stories.

- [X] T00- [ ] T008_ Créer le modèle SQLAlchemy `backend/app/models/user_preferences.py` (table `user_preferences` selon `data-model.md` §1)
- [X] T00- [ ] T009_ Importer le nouveau modèle dans `backend/app/models/__init__.py`
- [X] T010 Créer la migration Alembic `backend/alembic/versions/0042_user_preferences.py` qui (a) crée le type enum `onboarding_state`, (b) crée la table `user_preferences` + index `idx_user_preferences_account_id`, (c) active RLS + policy `user_preferences_tenant_isolation`, (d) ajoute la colonne `account_user.tokens_invalidated_at TIMESTAMPTZ NULL` **uniquement si absente** (utiliser `inspector.has_column`)
- [X] T011 Appliquer la migration localement : `cd backend && source .venv/bin/activate && alembic upgrade head`. Vérifier `\d user_preferences` et `\dT onboarding_state` dans psql
- [X] T012 [P] Créer le composable `frontend/app/composables/useT.ts` selon le contrat `contracts/frontend-components.md` (typage `keyof typeof frLocale`, substitution `{param}`)
- [X] T013 [P] Créer le store Pinia `frontend/app/stores/userPreferences.ts` avec `state`, `updatedAt`, `loaded`, `load()`, `set()` selon `contracts/me-preferences-api.md`
- [X] T014 [US1, US2, US3, US4, US5, US6] Vérifier que la route `auth.vue` layout existe sous `frontend/app/layouts/auth.vue` ; la créer si absente avec `<slot />` simple ; le polish split-screen est traité en US2 (T031)
- [X] T015 [P] Créer le composable `frontend/app/composables/usePasswordStrength.ts` selon contrat (zxcvbn-ts + critères + `isAcceptable = score >= 3 && meetsBaseCriteria`)
- [X] T016 [P] Créer le test unitaire `frontend/app/composables/__tests__/usePasswordStrength.test.ts` couvrant : mot de passe vide → score 0 not acceptable ; `abc` → score 0 not acceptable ; `Mefali2026!Vert` → score 4 acceptable ; mot de passe avec critères OK mais score 2 (dictionnaire) → not acceptable

**Checkpoint** : Foundational complet → toutes les user stories peuvent commencer en parallèle.

---

## Phase 3 — User Story 1 (P1) : Inscription multi-étapes guidée

**But** (US1 du spec) : wizard 3 étapes (identifiants, entreprise, consentements) + déclenchement automatique du tour 6 étapes après premier login + persistance de l'état du tour.
**Independent test** : créer un compte de bout en bout, atterrir sur welcome, voir le tour démarrer, l'état persiste entre logins.

### Backend

- [X] T017 [P] [US1] Créer `backend/app/users/schemas.py` (ou y ajouter) `UserPreferencesOut` et `UserPreferencesPatch` selon `contracts/me-preferences-api.md` (Pydantic v2, `model_config = {"extra": "forbid"}`, `Literal[...]`)
- [X] T018 [US1] Étendre `backend/app/users/service.py` : `get_or_create_preferences(db, user)` (upsert idempotent qui retourne la ligne, créée par défaut `pending` si absente) et `update_preferences(db, user, patch)` (vérifie la transition, écrit l'`audit_log` via `app/audit/`, met à jour `onboarding_state_updated_at`)
- [X] T019 [US1] Étendre `backend/app/users/router.py` : ajouter `GET /me/preferences` et `PATCH /me/preferences` qui appellent le service ci-dessus, dépendances auth + `get_db`. Status 401 sans session, 200 sinon. `PATCH` avec valeur identique = no-op (pas d'audit, status 200)
- [X] T020 [US1] Vérifier que `backend/app/main.py` monte bien le router `users` (s'il n'est pas déjà monté). Pas de modification si déjà fait
- [X] T021 [P] [US1] Créer `backend/tests/users/test_preferences.py` couvrant : GET sans session → 401 ; GET 1ère fois crée la ligne pending ; GET 2ème fois pas de duplication ; PATCH `completed` → 200 + audit ; PATCH valeur invalide → 422 ; PATCH champ inconnu → 422 (`extra=forbid`) ; RLS : user A ne voit pas les prefs de user B (tenant isolation → 404 cross-tenant)

### Frontend — wizard register

- [X] T022 [P] [US1] Créer `frontend/app/components/auth/PasswordStrengthMeter.vue` (props `password`, emit `change`, barre 4 segments, label FR via `useT`, aria-live)
- [X] T023 [P] [US1] Créer `frontend/app/components/auth/PasswordVisibilityToggle.vue` (v-model `visible`, button avec aria-pressed)
- [X] T024 [P] [US1] Créer `frontend/app/components/auth/RegisterProgressBar.vue` (props `step`, `total`, label "Étape {step} sur {total}")
- [X] T025 [P] [US1] Créer `frontend/app/components/auth/RegisterStepIdentifiants.vue` : email + password + confirm, intègre `PasswordStrengthMeter` et `PasswordVisibilityToggle`, émet `next(stepData)` quand validation locale passe
- [X] T026 [P] [US1] Créer `frontend/app/components/auth/RegisterStepEntreprise.vue` : raison sociale + combobox secteur consommant `GET /catalog/secteurs?q=` (F08, public), émet `next` / `previous`
- [X] T027 [P] [US1] Créer `frontend/app/components/auth/RegisterStepConsentements.vue` : checkboxes CGU + RGPD avec liens vers les textes publiés (F05), émet `next` / `previous`. Bouton final libellé `Créer mon compte` désactivé tant que les 2 cases ne sont pas cochées
- [X] T028 [US1] Refondre `frontend/app/pages/register.vue` en orchestrateur du wizard : state local `currentStep` (1|2|3), `draft` (en mémoire), transitions gsap 200 ms (neutralisées si `useReducedMotion`), au step 3 final → `POST /auth/register` agrégé + redirect `/onboarding/welcome`. Toutes les chaînes via `useT`
- [X] T029 [P] [US1] Ajouter dans `frontend/app/locales/fr.ts` toutes les clés `auth.register.*` utilisées par les composants ci-dessus

### Frontend — page welcome + tour guidé

- [X] T030 [US1] Créer `frontend/app/composables/useOnboardingTour.ts` selon `contracts/frontend-components.md` : `startIfPending`, `start`, `skip`, `dismissForever`, `complete` ; détection mobile < 768 px (fallback fullscreen) ; respecter `useReducedMotion` (`animate: false`) ; sélecteurs `[data-tour="..."]` ; appels `userPreferencesStore.set(...)` à chaque transition
- [X] T031 [P] [US1] Créer `frontend/app/components/onboarding/FullscreenTourStep.vue` (modal plein écran utilisé en fallback mobile : titre, description, boutons "Suivant"/"Passer"/"Ne plus afficher")
- [X] T032 [P] [US1] Créer `frontend/app/components/onboarding/OnboardingTourTrigger.vue` (bouton dans le menu Aide qui appelle `useOnboardingTour().start()`)
- [X] T033 [US1] Créer `frontend/app/pages/onboarding/welcome.vue` : message de bienvenue, bouton `Démarrer le tour` qui appelle `start()`, bouton secondaire `Passer pour l'instant`. À la fin du tour ou après skip/dismiss, redirection `/dashboard`
- [X] T034 [P] [US1] Ajouter dans `frontend/app/locales/fr.ts` les clés `onboarding.tour.*` et `onboarding.welcome.*`
- [X] T035 [US1] Ajouter les attributs `data-tour="sidebar"`, `data-tour="profil"`, `data-tour="chat"`, `data-tour="bibliotheque"`, `data-tour="plan-action"`, `data-tour="parametres"` dans le shell d'application (F38) — éditer `frontend/app/components/AppShell.vue` (ou layout équivalent)
- [X] T036 [US1] Modifier `frontend/app/composables/useAuth.ts` pour appeler `userPreferencesStore.load()` après `login()` réussi (afin que `startIfPending()` puisse statuer immédiatement à l'arrivée sur `/dashboard`)
- [X] T037 [US1] Sur `/dashboard` (ou layout authentifié principal), invoquer `useOnboardingTour().startIfPending()` au mounted (uniquement après chargement des préférences ; le composable doit être idempotent)
- [X] T038 [P] [US1] Créer le test unitaire `frontend/app/composables/__tests__/useOnboardingTour.test.ts` : vérifier que `startIfPending` appelle/n'appelle pas driver.js selon état, que `skip` met `state=skipped`, que `dismissForever` met `state=dismissed`, que `complete` met `state=completed`, que `restart` n'altère pas l'état initial
- [X] T039 [P] [US1] Créer l'E2E `frontend/tests/e2e/auth-register-wizard.spec.ts` : remplir wizard 3 steps, vérifier redirection `/onboarding/welcome`, password faible bloque le step 1, navigation arrière préserve les données
- [X] T040 [P] [US1] Créer l'E2E `frontend/tests/e2e/onboarding-tour.spec.ts` : démarrer le tour, cliquer "Passer" → state skipped via API, recharger et vérifier que le tour ne redémarre pas auto, relancer manuellement via `OnboardingTourTrigger`, terminer → state completed

**Checkpoint US1** : un nouveau compte est créable de bout en bout, atterrit sur welcome, voit le tour. État persisté en base. Indépendamment testable.

---

## Phase 4 — User Story 2 (P1) : Connexion soignée et récupération de mot de passe

**But** (US2) : login split-screen avec "Rester connecté" + deep link, parcours forgot/reset complet, anti-énumération, cooldown, invalidation des sessions, TTL token 60 min, redirection post-reset.
**Independent test** : flow login → forgot → email → reset → reconnexion fonctionne sans accroc, sessions précédentes invalidées.

### Backend

- [X] T041 [US2] Vérifier dans `backend/app/auth/service.py` que l'émission d'un `password_reset_token` utilise `settings.PASSWORD_RESET_TTL_MINUTES` ; ajuster sinon (la valeur stockée dans `expires_at = issued_at + timedelta(minutes=...)`)
- [X] T042 [US2] Vérifier dans `backend/app/auth/service.py::reset_password` que la consommation du token (positionne `consumed_at`) refuse `expires_at <= now()` et `consumed_at IS NOT NULL` avec une erreur générique FR. Ajuster si besoin
- [X] T043 [US2] Modifier `backend/app/auth/service.py::reset_password` pour positionner `account_user.tokens_invalidated_at = now()` dans la même transaction que la mise à jour du hash mot de passe
- [X] T044 [US2] Modifier le middleware `backend/app/middleware/auth_session.py` (ou le module `backend/app/core/security.py`) pour rejeter tout JWT dont `iat < tokens_invalidated_at` du user concerné (lecture en cache courte si possible, sinon lookup DB par requête authentifiée)
- [X] T045 [US2] Vérifier `backend/app/auth/router.py::forgot_password` : retourne **toujours** `200 NeutralAck` quel que soit l'existence du compte. Ajouter au besoin un délai constant minimal (ex. `await asyncio.sleep(0.1)`) pour réduire le canal latéral temps. Vérifier que SlowAPI rate limit est en place (ex. `@limiter.limit("3/minute")`)
- [X] T046 [US2] Vérifier `backend/app/auth/router.py::reset_password` : la réponse de succès est un simple `{"ok": true}` (pas de tokens) — le frontend redirige vers `/login` avec message ; en cas d'échec : 400 + message FR explicite mais générique
- [X] T047 [P] [US2] Créer `backend/tests/auth/test_password_reset_invalidation.py` : (a) login → reset password réussi → utilisation du cookie session précédent → 401, (b) deux logins simultanés sur 2 navigateurs → un reset → les 2 cookies sont invalidés
- [X] T048 [P] [US2] Créer/étendre `backend/tests/auth/test_password_reset_ttl.py` (avec `freezegun`) : token utilisé après 61 min → 400 ; token consommé puis ré-utilisé → 400 ; token valide → 200 + `tokens_invalidated_at` mis à jour
- [X] T049 [P] [US2] Créer/étendre `backend/tests/auth/test_forgot_password_neutral.py` : email existant et email inexistant → mêmes status, body, et tolérance temporelle ± 50 ms

### Frontend

- [X] T050 [P] [US2] Créer `frontend/app/components/auth/ResendCooldownButton.vue` (props `email`, `onSend`, `cooldownSeconds=60`, lit/écrit `localStorage[`resend-cooldown:${email}`]`, label dynamique "Renvoyer dans {n} s")
- [X] T051 [US2] Refondre `frontend/app/layouts/auth.vue` : grid 2-cols ≥ 1024 px (illustration | contenu), 1-col compactée 768–1023, 1-col pleine largeur < 768 (illustration cachée). `<link rel="preload" as="image">` pour avif/webp dans `<head>` via `useHead`
- [X] T052 [US2] Refondre `frontend/app/pages/login.vue` : split-screen via layout `auth`, intégrer `PasswordVisibilityToggle`, checkbox "Rester connecté" qui appelle `useAuth().login({ ..., rememberMe: true })`, lien "Mot de passe oublié", message d'erreur générique FR via `useT('auth.login.error')`. Respecter `route.query.redirect` (deep link). Toutes les chaînes via `useT`
- [X] T053 [US2] Modifier `frontend/app/composables/useAuth.ts` : `login(payload, { rememberMe })` ; le frontend ne décide pas du TTL cookie (côté backend selon flag à transmettre dans le body `LoginIn.remember_me: bool`). Ajouter le champ `remember_me` dans `backend/app/auth/schemas.py::LoginIn` et dans `auth/service.py` pour conditionner le `Max-Age` du cookie refresh (30 j si vrai, sinon session courte)
- [X] T054 [US2] Refondre `frontend/app/pages/forgot-password.vue` : un seul champ email, message de confirmation toujours générique via `useT('auth.forgot.confirmation')`, intègre `ResendCooldownButton` après premier envoi, layout auth
- [X] T055 [US2] Refondre `frontend/app/pages/reset-password.vue` : champ password + confirmation, `PasswordStrengthMeter`, sur succès → redirect `/login?reset=ok` ; le login affiche un toast de succès via `useT('auth.reset.success')`. Gestion token expiré/invalide → page d'erreur dédiée avec CTA "Redemander un lien"
- [X] T056 [P] [US2] Ajouter dans `frontend/app/locales/fr.ts` toutes les clés `auth.login.*`, `auth.forgot.*`, `auth.reset.*`, `auth.password.*`
- [X] T057 [P] [US2] Créer l'E2E `frontend/tests/e2e/auth-login.spec.ts` (étendre l'existant) : login OK + deep link respecté, login KO message générique, "Rester connecté" → cookie 30 j (vérifier `Max-Age` via Playwright), pwd toggle fonctionne
- [X] T058 [P] [US2] Créer l'E2E `frontend/tests/e2e/auth-reset-password.spec.ts` : forgot avec email OK et KO → même message, ResendCooldownButton verrouille 60 s, reset avec token valide → redirect `/login` + message succès, reset avec token invalide → page d'erreur, ancien cookie session ne fonctionne plus

**Checkpoint US2** : tout le flow auth est polish, sécurisé et testé. Indépendamment testable.

---

## Phase 5 — User Story 3 (P1) : Empty state landing intelligent

**But** (US3) : afficher empty state si profil < 50 %, dashboard sinon.
**Independent test** : 2 fixtures (compte profil 0 % et compte profil ≥ 50 %) → comportements distincts.

- [X] T059 [US3] Vérifier l'existence de l'endpoint `GET /me/entreprise/completion` dans `backend/app/entreprise/router.py` ; sinon, l'ajouter en consommant `entreprise/completeness.py` et retourner `{ "completion_pct": <0-100> }`
- [X] T060 [P] [US3] Créer/étendre `frontend/app/stores/entreprise.ts` (ou store existant F11) avec `completion_pct` lazy-loaded ; ajouter `loadCompletion()` qui appelle `GET /me/entreprise/completion`
- [X] T061 [P] [US3] Créer `frontend/app/components/onboarding/EmptyStateCard.vue` (props `icon`, `title`, `description`, `linkTo?`)
- [X] T062 [US3] Créer `frontend/app/components/onboarding/EmptyStateLanding.vue` : hero, CTA "Compléter mon profil en 5 minutes" → `router.push('/profil')`, 3 `<EmptyStateCard>`, toutes chaînes via `useT('empty.*')`
- [X] T063 [US3] Modifier `frontend/app/pages/dashboard.vue` : au mounted, charger `completion_pct` ; si `< 50` afficher `<EmptyStateLanding>`, sinon le contenu dashboard standard. Si l'endpoint répond 404, fallback empty state (fail-safe)
- [X] T064 [P] [US3] Ajouter dans `frontend/app/locales/fr.ts` les clés `empty.*`
- [X] T065 [P] [US3] Créer l'E2E `frontend/tests/e2e/empty-state-landing.spec.ts` : seed compte profil vide → voir empty state ; seed compte profil 60 % → voir dashboard ; clic CTA → URL `/profil`

**Checkpoint US3** : empty state opérationnel.

---

## Phase 6 — User Story 4 (P2) : Vérification d'email non bloquante

**But** (US4) : bandeau persistant non bloquant si email non vérifié + cooldown sur "Renvoyer".
**Independent test** : compte non vérifié voit bandeau ; clic "Renvoyer" déclenche cooldown 60 s ; après vérification, bandeau disparaît à la session suivante.

- [X] T066 [US4] Vérifier l'existence d'un endpoint `POST /auth/email/resend` ; sinon l'ajouter dans `backend/app/auth/router.py` (rate-limited, neutre, écrit l'envoi dans logs)
- [X] T067 [US4] Vérifier que `MeOut` (auth schemas) expose `email_verified_at` ; sinon l'ajouter
- [X] T068 [P] [US4] Créer `frontend/app/components/common/EmailVerificationBanner.vue` : visible si `useAuth().user.value?.email_verified_at == null`, intègre `ResendCooldownButton` qui appelle `POST /auth/email/resend`, bouton "X" pour replier (état session uniquement, ex. ref locale)
- [X] T069 [US4] Monter `<EmailVerificationBanner>` dans le layout authentifié principal (`frontend/app/layouts/default.vue` ou App Shell F38) au-dessus du contenu
- [X] T070 [P] [US4] Ajouter dans `frontend/app/locales/fr.ts` les clés `auth.email_verification.*`
- [X] T071 [P] [US4] Créer l'E2E `frontend/tests/e2e/email-verification-banner.spec.ts` : compte non vérifié voit bandeau ; clic Renvoyer → cooldown verrouille 60 s ; simuler vérification (DB direct via Playwright fixture) → recharger → bandeau disparu

**Checkpoint US4** : bandeau opérationnel, sans bloquer aucune fonctionnalité.

---

## Phase 7 — User Story 5 (P1) : Page d'accueil publique de confiance

**But** (US5) : `/` non authentifié = pitch + 3 bénéfices + témoignage + CTA register ; redirection si déjà connecté.
**Independent test** : visiter `/` non connecté → contenu attendu ; connecté → redirection.

- [X] T072 [P] [US5] Créer `frontend/app/components/home/PublicHero.vue` (titre, sous-titre, CTA `Créer un compte` → `/register`, illustration ou KPI)
- [X] T073 [P] [US5] Créer `frontend/app/components/home/PublicBenefitsGrid.vue` (3 cartes bénéfices avec icône + titre + description courte)
- [X] T074 [P] [US5] Créer `frontend/app/components/home/PublicTestimonial.vue` (citation anonymisée + secteur + région)
- [X] T075 [US5] Refondre `frontend/app/pages/index.vue` : si user authentifié, redirection `/dashboard` (middleware) ; sinon afficher Hero + Benefits + Testimonial + footer light. `definePageMeta({ public: true })`. Toutes chaînes via `useT('public.*')`
- [X] T076 [P] [US5] Ajouter dans `frontend/app/locales/fr.ts` les clés `public.*`
- [X] T077 [P] [US5] Test E2E `frontend/tests/e2e/public-home.spec.ts` : non authentifié → pitch visible, CTA navigue vers `/register` ; authentifié → redirection `/dashboard`

**Checkpoint US5** : page publique livrée.

---

## Phase 8 — User Story 6 (P1) : Animations subtiles + `prefers-reduced-motion`

**But** (US6) : transitions courtes par défaut, neutralisées avec `prefers-reduced-motion: reduce`.
**Independent test** : avec et sans la préférence système, observer les pages auth + onboarding.

- [X] T078 [US6] Vérifier `frontend/app/composables/useReducedMotion.ts` (existant) — confirmer qu'il retourne un `Ref<boolean>` réactif aux changements de la media query
- [X] T079 [US6] Auditer `frontend/app/pages/login.vue`, `register.vue`, `forgot-password.vue`, `reset-password.vue`, `onboarding/welcome.vue`, `index.vue` : toutes les animations gsap doivent passer par `useReducedMotion` (skip ou `duration: 0`) ; les CSS transitions sont neutralisées par `tour.css` global pour la classe driver.js (T005) — étendre la règle si nécessaire à `frontend/app/assets/css/main.css` pour les conteneurs auth
- [X] T080 [P] [US6] Test E2E `frontend/tests/e2e/reduced-motion.spec.ts` : forcer `prefers-reduced-motion: reduce` (Playwright `colorScheme`/`reducedMotion`), parcourir wizard register, lancer le tour ; assert qu'aucun élément n'a `transition-duration > 0` mesurée

**Checkpoint US6** : conformité accessibilité animations.

---

## Phase 9 — Polish & cross-cutting

- [X] T081 [P] Audit grep i18n : `grep -rEn '(Login|Sign[ -]?up|Welcome to)' frontend/app/pages frontend/app/components | grep -v locales/fr.ts` doit ne rien retourner. Corriger sinon
- [~] T082 [P] Lighthouse a11y manuel ou CI sur `/login` et `/register` → vérifier score ≥ 95 (SC-004) ; ajuster aria-labels manquants
- [~] T083 [P] Lighthouse perf manuel sur `/login` → vérifier LCP < 1,2 s (SC-005) ; ajuster preload, taille des illustrations sinon
- [~] T084 [P] Vérifier que `make lint` passe (ruff backend + eslint frontend)
- [X] T085 [P] Vérifier que `make test` passe et que la couverture backend reste ≥ 80 % (`pytest --cov`)
- [~] T086 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F42 comme `done` (si applicable au workflow du dépôt)
- [~] T087 Suivre le `quickstart.md` de bout en bout manuellement (toutes les étapes 1 à 7) sur un environnement local propre — checklist signée

---

## Dépendances entre phases & user stories

```text
Phase 1 (Setup)     ─┐
                     ├─► Phase 2 (Foundational) ─► Phase 3 (US1)
                     │                          ├─► Phase 4 (US2)
                     │                          ├─► Phase 5 (US3)
                     │                          ├─► Phase 6 (US4)
                     │                          ├─► Phase 7 (US5)
                     │                          └─► Phase 8 (US6)
                     │                                   │
                     └───────────────────────────────────┴─► Phase 9 (Polish)
```

- Phase 2 (Foundational) DOIT être terminée avant toute user story.
- US1, US2, US3, US4, US5, US6 sont **indépendantes** entre elles (peuvent se développer en parallèle par 6 développeurs distincts une fois Phase 2 terminée).
- US6 (`prefers-reduced-motion`) **audite** les pages produites par US1, US2, US5 ; elle peut commencer en parallèle mais ne se "termine" qu'après les pages auditées.
- US4 (vérification email) dépend de la présence du bandeau dans le layout authentifié (App Shell F38) — pas de dépendance sur les autres US sauf le store auth.
- Polish (Phase 9) en dernier.

---

## Opportunités de parallélisation

### Au sein de la Phase 2 (Foundational)

T012, T013, T015, T016 peuvent tourner en parallèle (4 fichiers distincts). T008→T010→T011 reste séquentiel (modèle → migration → apply).

### Au sein de la Phase 3 (US1)

- Backend : T017 ‖ T018→T019→T020 (T021 en parallèle dès T019 terminé)
- Frontend composants : T022 ‖ T023 ‖ T024 ‖ T025 ‖ T026 ‖ T027 ‖ T029 (tous fichiers distincts) ; T028 dépend de T022→T027
- Tour : T030 → T031 ‖ T032 ; T033 dépend de T030
- Tests : T038 ‖ T039 ‖ T040 dès que les fichiers correspondants existent

### Au sein de la Phase 4 (US2)

- Backend : T041→T042→T043→T044 séquentiel (même fichier `auth/service.py` ou middleware) ; T045, T046 indépendants ; T047 ‖ T048 ‖ T049
- Frontend : T050 ‖ T056 ; T051→T052→T054→T055 (layout puis pages) ; T053 indépendant côté composable mais touche backend (séquentiel avec T046)
- Tests : T057 ‖ T058

### Phases 5 → 8

Chaque story est essentiellement parallèle aux autres. Toutes les tâches `[P]` au sein d'une même story sont parallélisables.

### Phase 9

T081–T085 entièrement parallèles.

---

## Stratégie de livraison MVP

**MVP minimal (User Story 1 seule)** : Phase 1 + Phase 2 + Phase 3 → on peut déjà démontrer un wizard register fonctionnel + tour guidé persistant. Le reste (login polish, forgot/reset, empty state, vérif email, page publique) reste fonctionnellement opérationnel via les pages existantes non-polies (déjà livrées en F02).

**Incrément 2** : ajouter Phase 4 (US2) — login + reset polishés et durcis (sécurité réelle).

**Incrément 3** : ajouter Phase 5 (US3) + Phase 7 (US5) — orientation utilisateur + page publique de conversion.

**Incrément 4** : ajouter Phase 6 (US4) + Phase 8 (US6) + Phase 9 — quality gates + polish accessibilité.

---

## Récapitulatif

- **Total tâches** : 87
- **Phase 1 Setup** : 7 (T001–T007)
- **Phase 2 Foundational** : 9 (T008–T016)
- **Phase 3 US1** : 24 (T017–T040)
- **Phase 4 US2** : 18 (T041–T058)
- **Phase 5 US3** : 7 (T059–T065)
- **Phase 6 US4** : 6 (T066–T071)
- **Phase 7 US5** : 6 (T072–T077)
- **Phase 8 US6** : 3 (T078–T080)
- **Phase 9 Polish** : 7 (T081–T087)
- **Tâches `[P]`** : ~45 (parallélisables une fois leurs dépendances satisfaites)
