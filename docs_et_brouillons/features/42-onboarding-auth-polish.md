# F42 — Onboarding Tour & Auth UX Polish

**Phase** : C — Onboarding & profil
**Modules brainstorm** : 0.1 onboarding + amélioration F02 frontend
**Dépendances** : F36, F37, F38, F02 (auth backend), F11 (profil entreprise — pour redirect post-signup)
**Estimation** : 2 jours

## Contexte et objectif

Polish des pages auth existantes (`login`, `register`, `forgot-password`, `reset-password`) **avec** un onboarding multi-étapes qui amène la PME jusqu'à son premier chat fonctionnel. Première impression critique : si la PME ne ressent pas la qualité dans les 2 premières minutes, elle décroche.

Style : pages auth split-screen sobres, illustration ou citation chiffrée, formulaire à droite avec validation live, erreurs en français, gestion explicite des échecs.

## User Stories

- **US1 Login polish (P1)** — split-screen, password visibility toggle, "rester connecté", lien "mot de passe oublié", redirection deep link.
- **US2 Register multi-étapes (P1)** — wizard 3 étapes : (1) email + mot de passe, (2) raison sociale + secteur (autocomplete F08), (3) acceptation CGU + RGPD (F05). Progress bar, retour, validation zod live.
- **US3 Password strength meter (P1)** — barre + critères (8+ chars, majuscule, chiffre, symbole), tooltip explicatif. zxcvbn lib pour score.
- **US4 Forgot / reset password (P1)** — formulaire minimaliste + état d'attente, "Renvoyer dans 60 s" anti-spam.
- **US5 Email verification (P2)** — bandeau top non bloquant + bouton "Renvoyer", auto-disparaît une fois vérifié.
- **US6 Onboarding tour (P1)** — driver.js 6 étapes après 1er login : sidebar, profil, chat, bibliothèque, plan d'action, paramètres. Skip + "Ne plus afficher".
- **US7 Empty state landing (P1)** — `/` post-login si profil vide → CTA "Compléter mon profil en 5 minutes" + 3 mini-cartes pédagogiques. Si profil ≥ 50 % → dashboard F45.
- **US8 Erreurs auth claires (P1)** — messages français explicites. Jamais "Erreur 500".
- **US9 Brand voice page (P1)** — homepage publique sobre : pitch, 3 bénéfices, témoignage anonymisé, CTA `/register`.
- **US10 Animation entrée (P1)** — fade-in + slide-up subtil 300 ms (gsap), `prefers-reduced-motion` neutralise.

## Exigences fonctionnelles

- **FR-001** : Polish `pages/{login,register,forgot-password,reset-password,index}.vue` (existants).
- **FR-002** : Nouveau `pages/onboarding/welcome.vue` (post-register).
- **FR-003** : Composable `useOnboardingTour()` orchestre driver.js, persist `onboarding_completed_at` via `PATCH /me/preferences`.
- **FR-004** : Wizard register utilise `<UiFormField>` F37, transitions 200 ms gsap.
- **FR-005** : Password strength via zxcvbn, barre 4 segments colorés.
- **FR-006** : Backend `GET/PATCH /me/preferences` (clé `onboarding_completed_at`).
- **FR-007** : Empty state landing lit `useEntrepriseStore().completion_pct`.

## Exigences non-fonctionnelles

- **NFR-001** : Login LCP < 1.2 s (CDN cache fonts, illustration WebP).
- **NFR-002** : a11y : formulaires labellisés, erreurs `aria-live="polite"`.
- **NFR-003** : Mobile : illustration cachée < 768 px, formulaire full-width.
- **NFR-004** : Strings dans `i18n/fr.json`.

## Success Criteria

- **SC-001** : Register 3 étapes complétées < 90 s sur 5 PME testées.
- **SC-002** : Tour complet sans bug, skip fonctionnel.
- **SC-003** : Reset password flow end-to-end sans bug.
- **SC-004** : Lighthouse a11y ≥ 95 sur `/login` et `/register`.

## Hors-scope MVP

- OAuth Google/LinkedIn → P2.
- Email verification obligatoire → P2.
- Quiz onboarding "niveau ESG ?" → post-MVP.
- Animations Lottie → post-MVP.

## Risques et points de vigilance

- CGU/RGPD validés par DPO avant prod (F05).
- Driver.js mobile : popovers mal placés possible.
- Wizard abandonné : sauver brouillon localStorage (post-MVP).
- Email déjà utilisé : message générique anti-user-enumeration.
