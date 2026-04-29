---
description: "Tasks F02 — Authentification & Rôles PME/Admin (RLS)"
---

# Tasks: Authentification & Rôles PME/Admin (Row-Level Security)

**Input**: Design documents from `/specs/002-auth-roles-rls/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth.openapi.yaml, quickstart.md

**Tests**: Tests INCLUS (TDD obligatoire — règle commune projet, couverture cible 80 %, suite RLS dédiée).

**Organization**: Tâches groupées par user story pour permettre une livraison incrémentale et indépendante.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, pas de dépendance non terminée)
- **[Story]**: US1…US7 = mapping spec.md
- Chemins absolus depuis la racine du repo

## Path Conventions (Web app)

- Backend Python : `backend/app/...`, tests : `backend/tests/...`
- Frontend Nuxt 4 : `frontend/app/...`, tests : `frontend/tests/...` (et `frontend/app/tests/` pour unit colocalisés selon convention F01)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ajouter les dépendances et la configuration nécessaires à F02.

- [X] T001 Ajouter dépendances backend dans `backend/pyproject.toml` (et `requirements.txt` si présent) : `passlib[bcrypt]`, `python-jose[cryptography]`, `slowapi`, `email-validator`, `aiosmtplib` ; régénérer le lock et `pip install -e .[dev]`.
- [ ] T002 [P] Ajouter dépendances frontend dans `frontend/package.json` : `@pinia/nuxt`, `pinia`, `nuxt-security` ; `pnpm install`.
- [X] T003 [P] Créer le fichier `backend/.env.example` (ou mettre à jour celui existant) avec : `DATABASE_URL`, `MIGRATOR_DATABASE_URL`, `JWT_SECRET`, `CSRF_SECRET`, `COOKIE_DOMAIN`, `COOKIE_SECURE`, `EMAIL_BACKEND`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `RESET_PASSWORD_BASE_URL`.
- [X] T004 [P] Mettre à jour `docker-compose.yml` ou script d'init Postgres pour créer les rôles `app_user` et `migrator` à la première création de la base (script `init-roles.sql`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migration RLS, helpers de session, middleware auth — prérequis indispensables pour TOUTES les user stories.

⚠️ CRITICAL: Aucune US ne peut commencer avant la fin de cette phase.

- [X] T005 Créer la migration Alembic `backend/alembic/versions/0002_auth_rls.py` : (a) `CREATE TYPE account_user_role AS ENUM('pme','admin')`, (b) `ALTER TABLE account_users ADD COLUMN role account_user_role NOT NULL DEFAULT 'pme'`, `ADD COLUMN last_login_at timestamptz`, `ALTER COLUMN account_id DROP NOT NULL`, `ADD CONSTRAINT chk_admin_account CHECK ((role='pme' AND account_id IS NOT NULL) OR (role='admin' AND account_id IS NULL))`, (c) `CREATE TABLE refresh_tokens` (cf. data-model.md), (d) `CREATE TABLE password_reset_tokens` (cf. data-model.md).
- [X] T006 Étendre la migration `0002_auth_rls.py` pour : (a) parcourir toutes les tables avec colonne `account_id NOT NULL` du schéma `public`, (b) `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`, (c) `CREATE POLICY tenant_isolation` (USING + WITH CHECK) selon research.md D-005.
- [X] T007 Étendre la migration pour activer RLS sur `refresh_tokens` et `password_reset_tokens` avec policy par `current_setting('app.current_user_id')`.
- [X] T008 [P] Créer `backend/app/core/security.py` : helpers `hash_password(plain) -> str`, `verify_password(plain, hash) -> bool` (bcrypt cost 12), `create_access_token(payload, ttl) -> str`, `decode_access_token(token) -> dict`, `generate_csrf_token() -> str`, `verify_csrf_token(submitted, cookie_value) -> bool`, `generate_opaque_token(n_bytes=32) -> str`, `sha256_hex(token) -> str`.
- [X] T009 [P] Créer `backend/app/core/rate_limit.py` : configuration `slowapi.Limiter` avec backend mémoire, key par IP (X-Forwarded-For aware), exposer `limiter` et le décorateur.
- [X] T010 Créer `backend/app/core/session.py` : helper async `set_db_session_context(conn, *, user_id, account_id, is_admin)` qui exécute `SET LOCAL app.current_user_id`, `SET LOCAL app.current_account_id`, `SET LOCAL app.is_admin` dans la transaction courante.
- [X] T011 Modifier `backend/app/db.py` pour exposer deux engines : `engine_app` (utilisateur `app_user`, RLS appliquée, utilisé par l'API) et `engine_migrator` (utilisateur `migrator`, BYPASS RLS, utilisé par Alembic uniquement). Adapter `get_session()` pour utiliser `engine_app`.
- [X] T012 [P] Créer les modèles SQLAlchemy : `backend/app/models/account_user.py` (mise à jour avec `role`, `last_login_at`), `backend/app/models/refresh_token.py` (nouveau), `backend/app/models/password_reset_token.py` (nouveau). Inscription dans `backend/app/models/__init__.py`.
- [X] T013 Créer `backend/app/middleware/auth_session.py` : ASGI middleware qui (a) lit le cookie `mefali_at`, décode le JWT, charge l'utilisateur, attache à `request.state.user` ; (b) sur méthode non-GET, vérifie `X-CSRF-Token` vs cookie `mefali_csrf` ; (c) ouvre une transaction et appelle `set_db_session_context()`. En cas d'absence de JWT, ne lève pas (les dépendances `get_current_user` géreront 401).
- [X] T014 [P] Créer `backend/app/auth/dependencies.py` : `get_current_user(request) -> AccountUser` (401 si absent), `get_current_admin(user)` (403 si non admin), `get_current_pme(user)` (403 si admin pour endpoints PME-only).
- [X] T015 Enregistrer le middleware et les dépendances dans `backend/app/main.py` ; ajouter le `Limiter` à l'app FastAPI ; définir le handler 429 générique sans fuite.
- [X] T016 [P] Créer `backend/app/services/email_sender.py` : interface `EmailSender` + `ConsoleEmailSender` (dev/test, log) + `SMTPEmailSender` (prod via aiosmtplib). Sélection via `EMAIL_BACKEND` env.
- [X] T017 [P] Créer `backend/app/services/audit.py` (helper léger réutilisant la table `audit_log_entries` de F01) : `record_event(event_type, actor_user_id, actor_account_id, payload, source_of_change)`.

**Checkpoint**: Les fondations sont prêtes. Les US peuvent démarrer en parallèle dans la mesure de leurs dépendances.

---

## Phase 3: User Story 1 — Inscription PME (Priority: P1) 🎯 MVP

**Goal**: Une PME peut créer un compte (Account + AccountUser PME), recevoir cookies de session, consulter `/me`.

**Independent Test**: POST /auth/register avec email/password valides → 201 + cookies positionnés ; GET /me retourne le profil.

### Tests pour US1 (TDD)

- [X] T018 [P] [US1] Test unitaire politique de mot de passe dans `backend/tests/unit/test_password_policy.py` (longueur, maj, min, chiffre).
- [X] T019 [P] [US1] Test unitaire `hash_password`/`verify_password` dans `backend/tests/unit/test_security.py`.
- [X] T020 [P] [US1] Test contract `/auth/register` validant le schéma OpenAPI dans `backend/tests/integration/test_auth_register.py` : 201 sur cas nominal, 409 email dupliqué, 422 mot de passe faible.
- [X] T021 [P] [US1] Test integration `/me` après register dans `backend/tests/integration/test_me.py` : 200 + payload sans `password_hash`.

### Implementation US1

- [X] T022 [US1] Créer `backend/app/auth/schemas.py` : `RegisterIn`, `LoginIn`, `ForgotIn`, `ResetIn`, `MeOut`, `NeutralAck`, `Error`, `ValidationError` (pydantic v2, validation policy mot de passe via validator custom).
- [X] T023 [US1] Créer `backend/app/auth/service.py::register_pme(db, email, password) -> (AccountUser, refresh_token_clear)` : crée Account + AccountUser role=pme, hash le mot de passe, émet access JWT + refresh token (stocké hashé), audit `auth.register`.
- [X] T024 [US1] Créer `backend/app/auth/router.py::POST /auth/register` : validation, appel service, set cookies (access, refresh, csrf), retourne `MeOut`. Décoré `@limiter.limit("10/hour")`.
- [X] T025 [P] [US1] Créer `backend/app/users/router.py::GET /me` + `backend/app/users/service.py::get_me(user) -> MeOut` (dépend de `get_current_user`).
- [X] T026 [US1] Enregistrer les routers `auth` et `users` dans `backend/app/main.py`.

### Frontend US1

- [X] T027 [P] [US1] Créer `frontend/app/stores/auth.ts` (Pinia) : state `user` `MeOut | null`, actions `fetchMe()`, `setUser()`, `clear()`.
- [X] T028 [P] [US1] Créer `frontend/app/composables/useAuth.ts` : `register({email,password})`, `getMe()`. Gestion erreurs 409/422.
- [X] T029 [P] [US1] Créer `frontend/app/composables/useCsrf.ts` : lit le cookie `mefali_csrf`, expose `withCsrf()` qui ajoute l'en-tête `X-CSRF-Token`.
- [ ] T030 [US1] Créer `frontend/app/pages/register.vue` : formulaire email/password, soumission via `useAuth().register()`, redirection vers `/` en succès, affichage erreurs.
- [ ] T031 [US1] Test E2E Playwright `frontend/tests/e2e/register.spec.ts` : remplir formulaire valide → vérifier redirection + appel /me OK.

**Checkpoint**: Une PME peut s'inscrire et consulter son profil.

---

## Phase 4: User Story 2 — Connexion email + mot de passe (Priority: P1)

**Goal**: Utilisateur enregistré (PME ou Admin) se connecte ; réponses indistinguables pour email inconnu vs mauvais mdp.

**Independent Test**: POST /auth/login → 200 + cookies ; mauvais mdp → 401 ; email inconnu → 401 strictement identique.

### Tests US2

- [X] T032 [P] [US2] Test integration `/auth/login` dans `backend/tests/integration/test_auth_login.py` : succès, mauvais mdp = email inconnu (mêmes statut/corps/headers), audit log écrit, `last_login_at` mis à jour.
- [X] T033 [P] [US2] Test rate limiting `/auth/login` dans `backend/tests/integration/test_rate_limit.py` : 6e tentative/min/IP → 429 sans révéler l'email.

### Implementation US2

- [X] T034 [US2] Étendre `backend/app/auth/service.py` avec `login(db, email, password) -> (user, refresh_token_clear)` : vérifie hash, met à jour `last_login_at`, émet tokens, audit `auth.login.success` ou `auth.login.failure`. Réponse uniforme via exception dédiée.
- [X] T035 [US2] Étendre `backend/app/auth/router.py::POST /auth/login` : `@limiter.limit("5/minute")`, set cookies, retourne `MeOut`. 401 strictement identique pour les deux cas d'échec.
- [X] T036 [US2] Étendre `backend/app/auth/router.py::POST /auth/logout` : révoque le refresh courant, efface les 3 cookies, audit `auth.logout`.

### Frontend US2

- [ ] T037 [P] [US2] Étendre `frontend/app/composables/useAuth.ts` avec `login({email,password})` et `logout()`.
- [ ] T038 [US2] Créer `frontend/app/pages/login.vue` : formulaire, gestion `?next=` pour redirection post-login.
- [ ] T039 [P] [US2] Créer `frontend/app/middleware/auth.global.ts` : si pas d'utilisateur en store, appelle `/me` ; si 401, redirige `/login?next=<path>` (sauf pages publiques).
- [ ] T040 [US2] Test E2E Playwright `frontend/tests/e2e/login.spec.ts` : login OK → redirection ; mauvais mdp → message générique.

**Checkpoint**: Connexion fonctionnelle, indistinguabilité des erreurs validée, rate-limit en place.

---

## Phase 5: User Story 3 — Isolation stricte multi-tenant (Priority: P1)

**Goal**: RLS active. Toute tentative cross-Account renvoie 404 ou 0 ligne, y compris bypass simulé.

**Independent Test**: Créer 2 PME, peupler chacune, lancer la suite `tests/security/test_rls_isolation.py` → 100 % vert.

### Tests US3 (suite RLS dédiée — ≥ 5 cas)

- [X] T041 [US3] Créer `backend/tests/security/__init__.py` et `backend/tests/security/conftest.py` : fixture `two_pme` créant 2 Accounts + AccountUsers + 1 entreprise factice par Account (utilise `engine_migrator` pour le seed).
- [X] T042 [US3] Créer `backend/tests/security/test_rls_isolation.py` avec ≥ 7 tests : (1) SELECT cross-account → 0 ligne, (2) LIST → uniquement own, (3) UPDATE cross-account → 0 ligne affectée, (4) DELETE cross-account → 0 ligne affectée, (5) requête sans `SET LOCAL` → 0 ligne, (6) INSERT avec mismatch `account_id` → erreur RLS, (7) Admin avec `app.is_admin=true` voit tout.

### Implementation US3

- [X] T043 [US3] Vérifier (et corriger si besoin) que la migration `0002_auth_rls.py` applique bien la policy sur TOUTES les tables `account_id NOT NULL` (audit automatisé : script `backend/app/scripts/audit_rls.py` qui liste les tables sans policy → CI fail).
- [X] T044 [US3] Confirmer que `backend/app/middleware/auth_session.py` positionne systématiquement `app.current_account_id` et `app.current_user_id` pour tout endpoint authentifié, et `app.is_admin=true` si rôle admin.
- [X] T045 [US3] Convertir les 404 « not found » de tous les endpoints métier déjà existants pour qu'ils ne distinguent pas « inexistant » de « non visible » (revue + ajustement éventuel de F01 où nécessaire).

**Checkpoint**: La suite RLS est verte ; aucune route ne fuite cross-tenant.

---

## Phase 6: User Story 4 — Rôle Admin & back-office (Priority: P1)

**Goal**: Admin créé via seed, peut accéder /admin/_rls_check ; PME → 403 ; Admin ne crée pas de données métier PME.

**Independent Test**: `python -m app.scripts.seed_admin --email a@m.io --password ...` → succès ; login admin → /admin/_rls_check 200 ; login PME → /admin/_rls_check 403.

### Tests US4

- [X] T046 [P] [US4] Test integration `backend/tests/integration/test_admin_endpoints.py` : admin → 200 sur /admin/_rls_check ; PME → 403 ; non authentifié → 401.
- [X] T047 [P] [US4] Test integration script seed admin dans `backend/tests/integration/test_seed_admin.py` : exécute la commande via `python -m`, vérifie création + audit log + idempotence.

### Implementation US4

- [X] T048 [US4] Créer `backend/app/scripts/seed_admin.py` : argparse `--email`, `--password` ; valide policy ; crée AccountUser role=admin, account_id=NULL ; audit `admin.created` source=`admin` ; idempotence (refus si email existe).
- [X] T049 [US4] Créer `backend/app/admin/router.py::GET /admin/_rls_check` (dep `get_current_admin`) : pour chaque table avec colonne `account_id`, exécute `SELECT count(*)` sans set `app.current_account_id` (via une connexion `app_user` séparée sans middleware), vérifie 0 lignes ; retourne le rapport JSON conforme au contract.
- [X] T050 [US4] Enregistrer le router admin dans `backend/app/main.py`.

### Frontend US4

- [X] T051 [P] [US4] Créer `frontend/app/middleware/admin.ts` : si `auth.user?.role !== 'admin'`, retourne `abortNavigation(404)` (cohérent FR-015).
- [ ] T052 [US4] Test E2E `frontend/tests/e2e/admin-access.spec.ts` : login PME tentant d'accéder /admin → 404 ; login admin → 200.

**Checkpoint**: Cloisonnement Admin/PME validé bout en bout.

---

## Phase 7: User Story 5 — Refresh token rotatif (Priority: P2)

**Goal**: Renouvellement automatique du JWT via refresh ; détection de réutilisation = révocation cascade.

**Independent Test**: login → /auth/refresh OK → nouveau refresh ; rejouer l'ancien → toute la chaîne révoquée.

### Tests US5

- [X] T053 [P] [US5] Test integration `backend/tests/integration/test_auth_refresh_rotation.py` : (a) refresh OK rotation, (b) ancien rejoué → 401 + chaîne révoquée + audit `auth.refresh.reuse_detected`, (c) refresh expiré → 401.

### Implementation US5

- [X] T054 [US5] Étendre `backend/app/auth/service.py` avec `rotate_refresh(db, refresh_token_clear) -> (user, new_refresh_clear)` : marque `used_at`, crée nouveau avec `parent_id`, audit ; sur réutilisation (`used_at IS NOT NULL`) parcourt la chaîne et révoque tout, lève exception.
- [X] T055 [US5] Étendre `backend/app/auth/router.py::POST /auth/refresh` : `@limiter.limit("30/minute")`, exige X-CSRF-Token, set new cookies, retourne `MeOut`.
- [X] T056 [P] [US5] Étendre `frontend/app/composables/useAuth.ts` : intercepteur `ofetch` qui sur 401 sur endpoint protégé, tente `/auth/refresh` une fois puis rejoue, sinon redirige `/login`.

**Checkpoint**: Sessions longues confortables sans compromis sécurité.

---

## Phase 8: User Story 6 — Réinitialisation mot de passe par email (Priority: P2)

**Goal**: Forgot/Reset password complets, neutres, à usage unique, TTL 30 min.

**Independent Test**: forgot existing → email envoyé (console en test) ; reset OK → login avec nouveau mdp ; tous refresh révoqués.

### Tests US6

- [X] T057 [P] [US6] Test integration `backend/tests/integration/test_auth_forgot_reset.py` : email connu → 202 neutre + token créé en DB + audit `auth.password_reset.requested` ; email inconnu → réponse strictement identique ; reset valide → 204 + login OK avec nouveau mdp + tous refresh tokens révoqués ; reset expiré → 400 ; reset déjà consommé → 400.

### Implementation US6

- [X] T058 [US6] Étendre `backend/app/auth/service.py` avec `request_password_reset(db, email)` (toujours retourne neutre) et `consume_password_reset(db, token, new_password)`.
- [X] T059 [US6] Étendre `backend/app/auth/router.py::POST /auth/forgot-password` (`@limiter.limit("5/minute")`) et `POST /auth/reset-password`.
- [X] T060 [US6] Vérifier que `consume_password_reset` révoque tous les refresh tokens actifs et émet audit `auth.password_reset.consumed`.

### Frontend US6

- [X] T061 [P] [US6] Étendre `useAuth.ts` avec `forgotPassword(email)` et `resetPassword(token, newPassword)`.
- [ ] T062 [US6] Créer `frontend/app/pages/forgot-password.vue` (formulaire email + message neutre).
- [ ] T063 [US6] Créer `frontend/app/pages/reset-password.vue` (lit `?token=`, formulaire nouveau mdp, soumission + redirection /login).

**Checkpoint**: Récupération de compte fonctionnelle sans fuite d'existence.

---

## Phase 9: User Story 7 — Plusieurs utilisateurs par Account (Priority: P3)

**Goal**: Plusieurs AccountUsers d'un même Account ont des droits identiques.

**Independent Test**: Créer un second AccountUser dans le même Account (via outil interne ou direct DB en dev) ; vérifier qu'il accède aux mêmes ressources.

### Tests US7

- [X] T064 [P] [US7] Test integration `backend/tests/integration/test_multi_user_account.py` : 2 utilisateurs même Account → mêmes droits sur entreprise factice.

### Implementation US7

- [X] T065 [US7] Confirmer que toute logique d'autorisation s'appuie EXCLUSIVEMENT sur `account_id` (pas sur `user_id`) pour les ressources partagées de l'Account ; corriger si une ressource a été indexée par `user_id` à tort.
- [X] T066 [US7] (Optionnel MVP) Ajouter un endpoint d'admin PME `POST /accounts/me/users` pour ajouter un collaborateur — DIFFÉRÉ post-MVP, garder simplement une note dans tasks et un test d'isolation 2-utilisateurs même Account.

**Checkpoint**: Multi-utilisateurs intra-Account validé fonctionnellement (ajout via DB en MVP).

---

## Phase 10: Polish & Cross-Cutting

- [X] T067 [P] Audit des routes FastAPI : script `backend/app/scripts/audit_routes.py` qui liste toutes les routes et confirme la présence de `Depends(get_current_user)` (sauf whitelist `/auth/*`, `/health`) — exécuté en CI ; SC-003.
- [X] T068 [P] Scan des logs : script `backend/app/scripts/audit_logs.py` qui parse les logs récents et grep les motifs interdits (`password=`, `Bearer ey`, `mefali_at=`, `mefali_rt=`) ; CI fail si match ; SC-006.
- [X] T069 [P] Configurer `nuxt-security` dans `frontend/nuxt.config.ts` : headers HSTS, CSP minimal, X-Frame-Options DENY, cookies par défaut httpOnly+Secure+SameSite=Strict.
- [X] T070 [P] Mettre à jour `frontend/app/composables/useAuth.ts` pour utiliser `useFetch`/`$fetch` côté SSR avec credentials `'include'` et propagation correcte des cookies serveur → client.
- [X] T071 Mesure de couverture backend : `pytest --cov=app --cov-report=term-missing --cov-fail-under=80` ; corriger les lacunes.
- [ ] T072 Mesure de couverture frontend : `pnpm test --coverage` ; cible 80 %.
- [ ] T073 [P] Documentation : mettre à jour `backend/README.md` avec section « Auth & RLS » pointant vers `specs/002-auth-roles-rls/quickstart.md`.
- [ ] T074 Exécuter manuellement le quickstart `specs/002-auth-roles-rls/quickstart.md` et cocher tous les SC-001..SC-009.

---

## Dependencies

- **Phase 1 (Setup)** → **Phase 2 (Foundational)** → toutes les User Stories.
- **US3 (RLS)** dépend strictement de Phase 2 et conditionne la qualité de toutes les autres US — exécuter en parallèle de US1/US2 mais **ne pas merger** sans US3 verte.
- **US1, US2, US4** sont indépendantes une fois Phase 2 et US3 terminées.
- **US5, US6** dépendent de US1+US2 (login/refresh existants).
- **US7** dépend de US3 (RLS) et US2 (login).
- **Phase 10 (Polish)** après l'ensemble des US P1+P2.

## Parallel execution opportunities

- Phase 1 : T002, T003, T004 en parallèle après T001.
- Phase 2 : T008, T009, T012, T014, T016, T017 en parallèle (fichiers différents).
- US1 tests : T018, T019, T020, T021 en parallèle.
- US1 frontend : T027, T028, T029 en parallèle.
- US3 + US4 implémentation : T043 (audit RLS) et T046–T052 indépendants.
- Phase 10 : T067, T068, T069, T070, T073 en parallèle.

## Independent test criteria (récap)

- **US1** : POST /auth/register valide → 201 + cookies + GET /me 200 sans password_hash.
- **US2** : POST /auth/login OK → 200 ; mauvais mdp ≡ email inconnu (réponse identique octet-pour-octet) ; rate-limit 5/min.
- **US3** : `pytest backend/tests/security` → ≥ 7 tests verts.
- **US4** : seed_admin OK ; admin → /admin/_rls_check 200 ; PME → 403 ; non auth → 401.
- **US5** : refresh OK rotation ; rejeu ancien → cascade revoke + 401.
- **US6** : forgot neutre ; reset OK → 204 + login nouveau mdp + tous refresh révoqués.
- **US7** : 2 users même Account → mêmes droits.

## Suggested MVP scope

MVP livrable = Phase 1 + Phase 2 + US1 + US2 + US3 + US4. Soit :
- Inscription PME, connexion, isolation RLS bouclée, rôle admin opérationnel.
- US5 (refresh rotatif) et US6 (reset password) livrables sur l'incrément suivant.

## Format validation

Toutes les tâches respectent : `- [ ] [TaskID] [P?] [Story?] description avec chemin`. Chaque US a tests + implémentation + (si applicable) frontend + checkpoint.
