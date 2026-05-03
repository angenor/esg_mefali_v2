# Phase 0 — Research: Onboarding Tour & Auth UX Polish (F42)

**Date**: 2026-05-03
**Branch**: `042-onboarding-auth-polish`

Aucun marqueur `NEEDS CLARIFICATION` n'est resté dans le plan ; toutes les questions techniques ouvertes sont résolues ici par décisions documentées.

---

## R1 — Persistance des préférences d'onboarding : table dédiée vs colonnes sur `account_user`

**Decision** : Table dédiée `user_preferences` (1-1 avec `account_user`).

**Rationale** :
- Isole les préférences évolutives (tour, futurs flags : `theme`, `notifications_email_enabled`, etc.) sans muter le schéma d'authentification critique (`account_user`).
- Permet une politique RLS dédiée et un index discriminant sur `account_id` cohérent avec P2 sans alourdir les requêtes auth chaudes.
- Ajout/évolution de préférences futures = ALTER sur une petite table peu chargée plutôt que sur la table d'auth.
- Audit log plus net : `entity='user_preferences'` au lieu d'écrire sur `account_user`.

**Alternatives considered** :
- *Colonnes ajoutées sur `account_user`* : moins de tables à maintenir, mais alourdit la table critique d'auth, mélange préoccupations métier (préférences UX) et identité, et complique l'évolution.
- *Table générique key-value `user_settings`* : flexibilité maximale mais validation impossible côté SQL (typer `onboarding_state` en enum SQL devient lourd) ; rejeté pour le MVP — on pourra l'introduire plus tard si les préférences se multiplient.

**Implications** :
- Migration Alembic `0042_user_preferences` crée la table + index `(account_id)` + politique RLS standard.
- Le service garantit l'**upsert** : `GET /me/preferences` crée la ligne par défaut (`onboarding_state='pending'`) si absente.

---

## R2 — Modélisation de l'état du tour : enum SQL vs string libre

**Decision** : Enum PostgreSQL `onboarding_state` `('pending', 'completed', 'skipped', 'dismissed')` + colonne `onboarding_state_updated_at TIMESTAMPTZ`.

**Rationale** :
- Conforme à la clarification Q2 (état typé granulaire pour analytics futurs).
- Enum natif Postgres garantit l'intégrité (refus côté DB d'une valeur hors liste).
- Pydantic `Literal['pending','completed','skipped','dismissed']` côté API valide en entrée.

**Alternatives considered** :
- *VARCHAR + CHECK constraint* : équivalent fonctionnellement, mais l'enum offre une meilleure ergonomie côté ORM et un signal explicite dans le schéma.
- *Booléens séparés (`completed_at`, `skipped_at`, `dismissed_at`)* : plus verbeux et permet des combinaisons absurdes ("complété ET désactivé").

**Implications** :
- Migration crée le type enum avant la table.
- Évolution future : `ALTER TYPE onboarding_state ADD VALUE 'in_progress'` reste possible si on veut suivre la progression.

---

## R3 — Force du mot de passe : zxcvbn-ts (front) vs zxcvbn-python (back) vs les deux

**Decision** : `zxcvbn-ts` côté **frontend** uniquement pour le MVP (validation + feedback live), avec validation **structurelle** côté backend (longueur ≥ 8, présence majuscule/chiffre/symbole — règles déjà appliquées en F02). Le score zxcvbn est **strictement informatif et UX** : le bouton est désactivé tant que le score < 3, mais le backend ne re-vérifie pas le score zxcvbn.

**Rationale** :
- L'expérience temps réel (barre, critères, label FR) requiert du JS dans tous les cas → installer une seule lib (`@zxcvbn-ts/core` + `@zxcvbn-ts/language-common` + `@zxcvbn-ts/language-fr`).
- Re-vérifier zxcvbn côté backend doublerait le coût (~10–30 ms par requête) sans apporter d'autres garanties qu'un attaquant motivé contournerait de toute façon avec un mot de passe haut score mais réutilisé.
- La protection réelle reste : longueur, hashage Argon2 (déjà), rate limiting (déjà via SlowAPI), break detection éventuelle (post-MVP via HIBP).

**Alternatives considered** :
- *zxcvbn-python en backend en plus* : sécurité défense-en-profondeur mais coût/bénéfice médiocre pour MVP — réintroductible plus tard sans casse.
- *Front-only sans lib (heuristique maison)* : insuffisant — les patterns de dictionnaires courants (mots de passe ouest-africains : "bonjour123", noms de villes) ne sont pas détectés par règles simples.

**Implications** :
- Bundle frontend + ~120 KB compressé (acceptable pour pages auth qui ne sont chargées qu'une fois en début de session — code-split possible via `defineAsyncComponent` sur `PasswordStrengthMeter`).
- Backend continue d'appliquer la validation structurelle déjà en place ; ajouter un test pour vérifier qu'un mot de passe trop simple **passe** côté backend (puisque la garde-fou principale est front) et que la validation structurelle est bien le minimum exigé.

---

## R4 — Durée de validité du token reset password : 60 min, à usage unique

**Decision** : Aligner le TTL à 60 minutes (clarification Q5) et garantir que `consumed_at` est positionné dès la première consommation réussie ; tout token `consumed_at IS NOT NULL` ou `expires_at <= now()` est rejeté.

**Rationale** :
- Le modèle `password_reset_tokens` (`backend/app/models/password_reset_token.py`) a déjà les champs `issued_at`, `expires_at`, `consumed_at`. Vérifier dans `auth/service.py` la valeur de TTL utilisée à l'émission ; si elle diffère de 60 min, l'ajuster (config via `settings.PASSWORD_RESET_TTL_MINUTES = 60`).
- Le caractère à usage unique est non négociable (clarification + bonne pratique OWASP ASVS V3.7).

**Alternatives considered** :
- 15 min : trop strict pour les utilisateurs dont la livraison email est lente (clients IMAP en zone à connectivité variable).
- 24 h : exposition trop longue si email intercepté.

**Implications** :
- Pas de migration DB requise (champs déjà présents).
- Test backend : émettre un token, attendre > TTL via `freezegun`, tenter consommation → 400 + message FR explicite.
- Test backend : consommer, retenter le même token → 400.

---

## R5 — Invalidation des sessions actives sur reset réussi

**Decision** : Implémenter une **rotation forcée** du `session_version` côté `account_user` ; tout JWT/refresh dont la version ne correspond pas est rejeté à la prochaine validation. À défaut de mécanisme dédié dans F02, fallback : suppression de tous les refresh tokens persistés du user (si la table existe) ; sinon documenter explicitement la limite.

**Rationale** :
- Clarification Q4 : « toutes les sessions existantes du compte sont invalidées ».
- Le `REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30` (30 jours, cookies HttpOnly+Secure+SameSite=strict) signifie qu'un attaquant ayant volé un cookie pourrait l'utiliser jusqu'à 30 jours sans cette invalidation.

**Alternatives considered** :
- Ne rien faire (auto-login non, mais sessions parallèles tolérées) : viole la clarification et l'OWASP ASVS.
- Liste de révocation Redis : surdimensionné pour MVP, ajoute une dépendance.

**Implications** :
- Vérifier si `account_user` possède déjà un champ `session_version` ou `tokens_invalidated_at`. Si non, **ajouter** dans la migration `0042` la colonne `tokens_invalidated_at TIMESTAMPTZ NULL` et faire en sorte que la validation de session compare `iat >= tokens_invalidated_at`.
- Modifier `auth.service.reset_password` pour positionner `tokens_invalidated_at = now()` dans la même transaction.
- Test : login → reset password réussi → utilisation du cookie de session précédent → 401.

---

## R6 — Anti-énumération sur `/auth/forgot-password`

**Decision** : `/auth/forgot-password` retourne **toujours** `200 { "ok": true }` (ou un `204`) avec le **même délai** quelle que soit l'existence du compte, et le même message générique côté frontend. Pas de différenciation par status code, par message, par durée ni par header.

**Rationale** :
- Clarification + FR-006 + OWASP ASVS V3.2.4.
- Le délai constant nécessite éventuellement un `time.sleep(random_jitter)` ou un envoi en tâche de fond (déjà le cas si l'envoi mail est asynchrone).

**Alternatives considered** :
- Réponse différenciée pour debug en dev : non — ouvre la porte à des erreurs en prod si flags mal configurés.

**Implications** :
- Vérifier l'implémentation actuelle `auth/router.py::forgot_password` : si elle renvoie déjà un `NeutralAck`, OK. Sinon, l'aligner. Tester en CI : appel avec email existant vs inexistant → réponse identique en status, body, et délai (tolérance ± 50 ms).
- Frontend : afficher un message générique « Si cette adresse est valide, vous recevrez un lien dans quelques minutes. » (chaîne FR dans `locales/fr.ts`).

---

## R7 — Cooldown anti-spam 60 s sur "Renvoyer" (forgot + email verification)

**Decision** : Cooldown **client** géré par un composant `ResendCooldownButton.vue` (compteur 60 s avec `localStorage`-key par adresse email pour persister entre rechargements de page) **et** rate limit **serveur** déjà en place (SlowAPI `@limiter.limit("3/minute")` ou équivalent — à vérifier sur `forgot_password` et l'endpoint vérification email).

**Rationale** :
- Le cooldown client est UX-friendly (compteur visible).
- Le rate limit serveur est la garantie réelle (un attaquant peut désactiver le client).
- Conforme à FR-007.

**Alternatives considered** :
- Cooldown serveur lié au `email` : nécessite un store partagé (Redis) ou une table dédiée → overkill MVP. La protection IP (SlowAPI) suffit.

**Implications** :
- `ResendCooldownButton.vue` lit/écrit `localStorage[`resend-cooldown:${email}`]` avec timestamp d'expiration.
- Tester côté backend que 5 appels rapides sont rate-limited (existant déjà probablement, à confirmer).

---

## R8 — Tour guidé : driver.js, mobile, et `prefers-reduced-motion`

**Decision** :
- Utiliser `driver.js` (déjà installé) avec configuration : `allowClose: true`, `showProgress: true`, traductions FR via la clé `popoverClass` + textes injectés.
- Sur mobile (< 768 px), si `driver.js` détecte qu'un popover sortirait de la viewport, fallback vers un **affichage modal plein écran** ; détection via media query + `window.innerWidth` au démarrage du tour.
- Si `prefers-reduced-motion: reduce`, désactiver les transitions de `driver.js` (`stagePadding: 0`, `animate: false` à passer au constructeur).
- Stocker l'état uniquement après action utilisateur explicite : terminer la dernière étape → `completed`, bouton "Passer" → `skipped`, bouton "Ne plus afficher" → `dismissed`. Fermeture par clic à l'extérieur ou ESC = `skipped` (pas `dismissed` — l'utilisateur n'a pas choisi explicitement de masquer pour toujours).

**Rationale** :
- driver.js déjà au package.json — pas de nouvelle dépendance.
- Cohérent avec `useReducedMotion` existant.
- La distinction skip/dismiss permet d'envisager un futur "rappel doux" sur les `skipped` sans rappeler les `dismissed`.

**Alternatives considered** :
- shepherd.js, intro.js : équivalents mais ajout de dépendance.
- Tour custom (overlay maison) : trop d'effort pour l'apport.

**Implications** :
- `useOnboardingTour.ts` expose `start()`, `restart()`, `dismissForever()`. À chaque transition d'état utilisateur, appel `PATCH /me/preferences` avec le nouvel `onboarding_state`.
- 6 étapes ciblant des sélecteurs DOM stables (préfixés `data-tour="..."`) à ajouter dans le shell d'application (F38) : `data-tour="sidebar"`, `data-tour="profil"`, `data-tour="chat"`, `data-tour="bibliotheque"`, `data-tour="plan-action"`, `data-tour="parametres"`.
- Tests Playwright : naviguer vers welcome → driver.js démarre → cliquer "Passer" → vérifier `state = skipped` ; relancer manuellement → driver.js redémarre.

---

## R9 — i18n FR : nuxt-i18n vs fichier statique TS

**Decision** : Fichier TypeScript `frontend/app/locales/fr.ts` exportant un objet `default` typé, consommé par un composable `useT(key: string, params?: Record<string, string|number>): string`. Pas de `nuxt-i18n` pour le MVP.

**Rationale** :
- L'application est **mono-langue FR** au MVP (constitution + FR-019). `nuxt-i18n` ajoute ~80 KB et des concepts (locale routing, lazy loading) inutiles pour une seule langue.
- Un fichier TS typé offre l'autocomplétion et la détection de chaînes manquantes au build (TypeScript échoue si une clé inexistante est utilisée avec un type `keyof typeof FR`).
- Migration vers `nuxt-i18n` reste triviale plus tard (juste remplacer `useT` par `useI18n().t`).

**Alternatives considered** :
- `nuxt-i18n` complet : surdimensionné, ralentit le démarrage.
- `vue-i18n` standalone : équivalent mais ajoute une dépendance.

**Implications** :
- Toutes les chaînes FR de la feature centralisées dans un fichier unique.
- Test : un script lint vérifie qu'aucune chaîne JSX/template ne contient une lettre française non standard hors de balises `i18n`/`useT` (heuristique simple via grep).

---

## R10 — Pourcentage de complétion du profil entreprise

**Decision** : Lecture via un endpoint dédié `GET /me/entreprise/completion` (à confirmer dans F11) qui renvoie `{ completion_pct: number (0-100) }`. Le seuil empty-state vs dashboard est **50 %** (FR-012, FR-013).

**Rationale** :
- F11 expose déjà `entreprise/completeness.py` ; on consomme via une route HTTP existante ou à exposer (à vérifier dans `entreprise/router.py` — sinon ajouter une mini-route).
- 50 % a été retenu dans le brouillon source comme seuil pédagogique : couvre le profil "minimum viable pour matcher" (raison sociale, secteur, taille, contact) sans exiger les indicateurs ESG complets.

**Alternatives considered** :
- Frontend recalcule la complétion à partir des champs : duplication de logique métier → rejeté (le calcul vit dans F11).

**Implications** :
- Dépendance soft sur F11 : si l'endpoint n'existe pas encore, prévoir une PR sur F11 pour l'exposer ou un fallback côté frontend (toujours afficher empty-state si l'endpoint répond 404 — fail-safe).

---

## R11 — Performance LCP < 1,2 s sur `/login`

**Decision** :
- Illustration en `webp` + fallback `avif`, ≤ 60 KB chacune, dimensions 800×800.
- `<link rel="preload" as="image" type="image/avif" href="...">` dans le `<head>`.
- Police système ou self-hosted (déjà en place) avec `font-display: swap`.
- Pas de bundle JS bloquant — la page de login utilise un layout léger sans charger driver.js, charts, ni mermaid (vérifier qu'aucun import global ne tire ces dépendances).

**Rationale** :
- LCP < 1,2 s est exigeant ; la feuille de route est éprouvée (preload + format moderne + critical CSS inline).

**Alternatives considered** :
- Lottie / animations riches : exclus par "Hors-scope MVP".

**Implications** :
- Ajouter un test Lighthouse-CI ou un check manuel documenté dans `quickstart.md`.

---

## R12 — Sectors autocomplete au step 2 du wizard

**Decision** : Endpoint `GET /catalog/secteurs?q=` (F08) — utilisation d'un combobox accessible (`<UiCombobox>` de F37 si dispo, sinon `headlessui` ou implémentation maison ARIA).

**Rationale** : Réutilisation de la dépendance F08 déjà publiée.

**Implications** : Vérifier que F08 expose un endpoint public ou nécessitant un compte pré-créé ; au step 2 l'utilisateur n'est pas encore authentifié → l'endpoint doit accepter des appels non authentifiés OU le wizard doit créer le compte au step 1 et continuer authentifié dès le step 2. **Décision** : créer le compte à la fin du step 3 (atomique) — le frontend conserve les saisies en mémoire (sans `localStorage`, conforme "Hors-scope MVP : sauvegarde inter-session"). L'endpoint `/catalog/secteurs` doit donc être **public** (lecture seule du référentiel — pas de PII). À confirmer en début d'implémentation.

---

## R13 — Tests E2E : Playwright

**Decision** : Étendre les specs existantes sous `frontend/tests/e2e/` avec 4 nouveaux fichiers (login, register-wizard, reset-password, onboarding-tour, empty-state-landing). Pas de framework supplémentaire.

**Rationale** : Conforme aux conventions (F38).

---

## Synthèse

Aucune zone d'incertitude résiduelle. Toutes les décisions sont implémentables avec les dépendances déjà au dépôt (driver.js, gsap) ou un seul ajout frontend (`@zxcvbn-ts/*`). Pas de nouveau service backend, une seule nouvelle table, un seul nouvel endpoint.
