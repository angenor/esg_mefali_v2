# Feature Specification: Onboarding Tour & Auth UX Polish

**Feature Branch**: `042-onboarding-auth-polish`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F42 — Polish des pages auth (login, register, forgot/reset password) et mise en place d'un onboarding multi-étapes qui amène la PME jusqu'à son premier chat fonctionnel."

## Clarifications

### Session 2026-05-03

- Q: Durée de la session "Rester connecté" ? → A: 30 jours (standard B2B, équilibre confort/sécurité)
- Q: Modèle d'état du tour d'onboarding ? → A: État typé `pending` / `completed` / `skipped` / `dismissed` + timestamp de dernière action
- Q: Score minimum requis pour le mot de passe ? → A: Critères de base (≥8 chars, majuscule, chiffre, symbole) ET score de robustesse ≥ 3/4 (rejet des dictionnaires courants)
- Q: Comportement après réinitialisation réussie du mot de passe ? → A: Redirection vers `/login` avec message de succès ; toutes les sessions existantes du compte sont invalidées
- Q: Durée de validité du lien de réinitialisation ? → A: 60 minutes, à usage unique (token invalidé dès première utilisation)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Inscription multi-étapes guidée (Priority: P1)

Une PME ouest-africaine arrive sur la page d'inscription, parcourt un wizard 3 étapes (identifiants, identité entreprise, consentements légaux) avec validation en direct, et atterrit sur un onboarding visuel qui lui présente l'application avant son premier chat.

**Why this priority**: Première impression critique — si la PME ne ressent pas la qualité dans les 2 premières minutes, elle décroche. C'est le tunnel d'entrée principal du produit.

**Independent Test**: Une PME inscrite peut créer son compte de bout en bout (3 étapes), recevoir confirmation, voir le tour guidé, et atterrir sur un état initial cohérent — sans dépendre du reste du produit (chat, profil, dashboard restent stubbables).

**Acceptance Scenarios**:

1. **Given** une PME sur la page d'inscription, **When** elle complète les 3 étapes (email + mot de passe valide, raison sociale + secteur, acceptation CGU/RGPD), **Then** son compte est créé et elle est redirigée vers la page de bienvenue post-inscription.
2. **Given** une PME au step 2 du wizard, **When** elle clique "Précédent", **Then** elle revient au step 1 avec ses données préservées et la barre de progression mise à jour.
3. **Given** un mot de passe faible saisi au step 1, **When** la PME tape, **Then** la barre de force se met à jour en direct avec critères visibles (longueur, majuscule, chiffre, symbole) et le bouton "Suivant" reste désactivé tant que les critères P1 ne sont pas atteints.
4. **Given** une inscription complète réussie, **When** la PME se connecte pour la première fois, **Then** un tour guidé 6 étapes (sidebar, profil, chat, bibliothèque, plan d'action, paramètres) démarre automatiquement avec options "Passer" et "Ne plus afficher".
5. **Given** une PME ayant terminé ou passé le tour, **When** elle revient sur l'application au login suivant, **Then** le tour ne redémarre pas automatiquement.

---

### User Story 2 — Connexion soignée et récupération de mot de passe (Priority: P1)

Une PME revient sur la plateforme et se connecte via une page split-screen sobre. En cas d'oubli, elle peut demander un lien de réinitialisation et le suivre jusqu'à reprise d'accès, avec messages d'erreur clairs en français à chaque étape.

**Why this priority**: Le retour quotidien des PME passe par le login. Un échec ou une friction ici (mot de passe oublié, message obscur) est la première cause d'abandon après l'inscription.

**Independent Test**: Le flow login → mot de passe oublié → email de reset → nouveau mot de passe → reconnexion fonctionne end-to-end et est testable indépendamment du reste du produit.

**Acceptance Scenarios**:

1. **Given** une PME avec compte existant, **When** elle saisit identifiants valides et coche "Rester connecté", **Then** elle est redirigée vers sa destination demandée (deep link respecté) et reste connectée au-delà de la session courante.
2. **Given** une PME ayant oublié son mot de passe, **When** elle saisit son email sur la page "mot de passe oublié", **Then** un message générique de confirmation s'affiche (sans révéler si l'email existe) et un bouton "Renvoyer dans 60 s" est verrouillé pendant le délai.
3. **Given** un lien de réinitialisation reçu par email, **When** la PME suit le lien et soumet un nouveau mot de passe respectant les critères, **Then** son mot de passe est mis à jour, ses sessions existantes sont invalidées, et elle est redirigée vers la page de connexion avec un message de succès afin de se reconnecter avec le nouveau mot de passe.
4. **Given** une saisie d'identifiants incorrecte, **When** la PME soumet, **Then** un message en français explicite (jamais "Erreur 500", jamais de divulgation d'existence du compte) s'affiche en zone d'erreur accessible.
5. **Given** un champ mot de passe, **When** la PME clique sur l'icône œil, **Then** la valeur devient visible en clair et l'icône change d'état.

---

### User Story 3 — Empty state landing intelligent (Priority: P1)

Après la première connexion (ou tant que le profil entreprise est très incomplet), la PME atterrit sur une page d'accueil qui l'invite explicitement à compléter son profil en 5 minutes via un CTA central, accompagné de 3 mini-cartes pédagogiques expliquant ce que la plateforme va débloquer.

**Why this priority**: Sans cette orientation, une PME nouvellement inscrite ne sait pas par où commencer. C'est le pont entre l'onboarding visuel (US1) et la première utilisation utile (chat).

**Independent Test**: Pour un compte de profil < 50 % de complétion, la landing affiche le CTA "Compléter mon profil" et les 3 cartes ; pour un compte ≥ 50 %, elle affiche le tableau de bord normal — testable avec deux comptes fixtures.

**Acceptance Scenarios**:

1. **Given** une PME au tout premier login (profil 0 %), **When** elle clôt le tour guidé, **Then** la page d'accueil affiche un CTA visible "Compléter mon profil en 5 minutes" et 3 cartes pédagogiques.
2. **Given** une PME dont le profil est complété à au moins 50 %, **When** elle se connecte, **Then** elle voit le dashboard standard et non l'empty state.
3. **Given** une PME sur l'empty state, **When** elle clique le CTA, **Then** elle est redirigée vers le formulaire de profil entreprise.

---

### User Story 4 — Vérification d'email non bloquante (Priority: P2)

Une PME nouvellement inscrite peut continuer à utiliser le produit même si elle n'a pas encore vérifié son email, tout en étant rappelée discrètement de le faire via un bandeau persistant non bloquant qui disparaît dès que la vérification est faite.

**Why this priority**: Bloquer l'usage avant vérification email tuerait l'élan post-inscription ; en revanche, un rappel passif maintient la pression sans frustrer.

**Independent Test**: Un compte non vérifié voit le bandeau et peut cliquer "Renvoyer" ; après vérification, le bandeau disparaît à la session suivante.

**Acceptance Scenarios**:

1. **Given** une PME inscrite mais email non vérifié, **When** elle navigue dans l'application, **Then** un bandeau en haut de page propose "Vérifier mon email" et "Renvoyer le lien" sans bloquer aucune fonctionnalité.
2. **Given** un bandeau de vérification visible, **When** la PME clique "Renvoyer", **Then** un nouveau lien est envoyé et un compteur anti-spam s'enclenche (60 s minimum entre deux envois).
3. **Given** un email vérifié, **When** la PME recharge la page, **Then** le bandeau a disparu.

---

### User Story 5 — Page d'accueil publique de confiance (Priority: P1)

Un visiteur (PME prospect, partenaire, journaliste) arrive sur l'URL racine et comprend en moins de 30 secondes ce que fait la plateforme, pour qui, et ce qu'il peut en attendre, avec un appel à l'action clair vers l'inscription.

**Why this priority**: La page publique est la porte d'entrée du funnel d'acquisition. Sans pitch clair et témoignage crédible, la conversion s'effondre.

**Independent Test**: La page racine est visitable sans compte, présente le pitch + 3 bénéfices + 1 témoignage + CTA inscription, et passe les tests d'accessibilité.

**Acceptance Scenarios**:

1. **Given** un visiteur non authentifié, **When** il arrive sur l'URL racine, **Then** il voit un pitch clair, 3 bénéfices structurés, un témoignage anonymisé crédible, et un CTA proéminent "Créer un compte".
2. **Given** une PME déjà connectée, **When** elle arrive sur l'URL racine, **Then** elle est redirigée vers son espace authentifié (empty state ou dashboard selon profil).

---

### User Story 6 — Animations subtiles et respect des préférences (Priority: P1)

Toutes les transitions des pages auth et de l'onboarding sont fluides (fade-in + slide-up courts) sans alourdir l'expérience, et sont automatiquement neutralisées pour les utilisateurs ayant activé "réduire les animations" au niveau système.

**Why this priority**: Les micro-animations véhiculent la qualité perçue. Mais elles doivent respecter `prefers-reduced-motion` pour ne pas exclure les utilisateurs sensibles.

**Independent Test**: Avec `prefers-reduced-motion: reduce`, aucune animation supérieure à un fade simple n'est jouée ; sans cette préférence, les transitions sont visibles et limitées en durée.

**Acceptance Scenarios**:

1. **Given** un utilisateur sans préférence de réduction de mouvement, **When** il navigue entre les étapes du wizard d'inscription, **Then** la transition affiche un fade-in + slide-up court (≈ 300 ms).
2. **Given** un utilisateur avec `prefers-reduced-motion: reduce`, **When** il navigue dans les mêmes pages, **Then** aucune animation autre qu'un fondu instantané n'est jouée.

---

### Edge Cases

- **Email déjà utilisé à l'inscription** : message générique anti-énumération (ex. "Si cette adresse est valide, vous recevrez une confirmation"), pas de différenciation visible entre email inconnu et email déjà inscrit.
- **CGU/RGPD non acceptés** : bouton de finalisation au step 3 reste désactivé ; texte explicatif sous la case.
- **Token de reset password expiré (au-delà de 60 min) ou déjà utilisé** : page dédiée explique l'expiration ou l'invalidation et propose de redemander un nouveau lien.
- **Tour guidé sur écran mobile** : popovers doivent rester lisibles ; si placement impossible, fallback texte plein écran avec navigation explicite.
- **Saisie wizard interrompue** : à la prochaine ouverture, l'étape déjà validée précédemment est reprise (in-memory pendant la session ; sauvegarde inter-session hors scope MVP).
- **Illustration de la page split-screen sur mobile (< 768 px)** : illustration cachée, formulaire en pleine largeur.
- **Strings totalement en français** : aucune chaîne anglaise visible dans les pages auth/onboarding ; toutes les chaînes proviennent du fichier de traductions FR.
- **Un utilisateur ayant choisi "Ne plus afficher" au tour** : le tour ne doit jamais redémarrer automatiquement ; un point d'entrée manuel doit toutefois rester accessible (ex. menu d'aide).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT proposer une page de connexion en disposition split-screen (illustration ou élément visuel à gauche, formulaire à droite) avec basculement de visibilité du mot de passe et option "Rester connecté" qui prolonge la session de l'utilisateur jusqu'à 30 jours d'inactivité (par défaut session courte navigateur).
- **FR-002** : Le système DOIT proposer un wizard d'inscription en 3 étapes : (1) email + mot de passe, (2) raison sociale + secteur d'activité (saisie facilitée par autocomplétion sur le référentiel des secteurs), (3) acceptation explicite des CGU et de la politique de confidentialité.
- **FR-003** : Le wizard d'inscription DOIT afficher une barre de progression visible et permettre la navigation arrière sans perte des données déjà saisies dans la session.
- **FR-004** : La saisie du mot de passe DOIT afficher en temps réel une mesure de force visuelle (barre 4 segments) et la liste des critères requis (longueur ≥ 8, majuscule, chiffre, caractère spécial), avec un score de robustesse global. La validation pour avancer dans le wizard ou enregistrer un nouveau mot de passe DOIT exiger à la fois le respect de tous les critères de base ET un score de robustesse d'au moins 3 sur 4 (rejet des mots de passe figurant dans des dictionnaires de mots de passe courants ou suivant des motifs triviaux). Tant que ce seuil n'est pas atteint, le bouton "Suivant" / "Enregistrer" reste désactivé avec un message explicatif.
- **FR-005** : Le système DOIT proposer un parcours "mot de passe oublié → email de réinitialisation → définition d'un nouveau mot de passe → reconnexion" complet et exclusivement en français. Une fois le nouveau mot de passe enregistré avec succès, l'utilisateur DOIT être redirigé vers la page de connexion avec un message de succès explicite, et toutes les sessions actives existantes du compte (y compris d'éventuels appareils tiers) DOIVENT être invalidées — l'utilisateur n'est jamais auto-connecté à la suite d'un reset.
- **FR-006** : La demande de réinitialisation DOIT renvoyer un message générique unique, qu'un compte existe ou non avec cette adresse, pour empêcher l'énumération d'utilisateurs.
- **FR-007** : Le bouton "Renvoyer le lien" (mot de passe oublié et vérification email) DOIT être verrouillé pendant un délai d'au moins 60 secondes après chaque envoi.
- **FR-008** : Le système DOIT afficher tous les messages d'erreur d'authentification en français explicite, sans exposer de codes techniques ni de détails permettant de distinguer les causes (ex. compte inexistant vs mot de passe incorrect doivent partager un message générique).
- **FR-009** : Après création du compte, le système DOIT proposer un tour guidé contextuel en 6 étapes pointant les zones clés de l'interface (sidebar, profil, chat, bibliothèque, plan d'action, paramètres) avec boutons "Passer", "Suivant" et "Ne plus afficher".
- **FR-010** : Le système DOIT mémoriser de façon durable, par utilisateur, l'état du tour parmi quatre valeurs explicites — `pending` (jamais ouvert), `completed` (parcouru jusqu'à la dernière étape), `skipped` (option "Passer" utilisée), `dismissed` (option "Ne plus afficher" utilisée) — accompagné du timestamp de la dernière action. Le tour ne DOIT plus se redéclencher automatiquement dès lors que l'état est différent de `pending`.
- **FR-011** : L'utilisateur DOIT pouvoir relancer manuellement le tour à tout moment depuis un point d'entrée stable (par exemple un menu "Aide").
- **FR-012** : Pour un compte dont le profil entreprise est complété à moins de 50 %, la page d'accueil authentifiée DOIT afficher un état d'accueil "vide" avec un CTA principal "Compléter mon profil en 5 minutes" et 3 mini-cartes pédagogiques expliquant ce que la plateforme va débloquer.
- **FR-013** : Pour un compte dont le profil entreprise est complété à au moins 50 %, la page d'accueil authentifiée DOIT afficher le tableau de bord standard.
- **FR-014** : Tant que l'email d'un utilisateur n'a pas été vérifié, un bandeau persistant non bloquant DOIT être affiché en haut de l'application, avec une action "Renvoyer le lien" et un compteur anti-spam.
- **FR-015** : Une fois l'email vérifié, le bandeau DOIT disparaître automatiquement (au plus tard à la prochaine session) sans intervention manuelle.
- **FR-016** : La page d'accueil publique (URL racine, non authentifiée) DOIT présenter un pitch produit, 3 bénéfices structurés, un témoignage anonymisé crédible, et un CTA proéminent vers la création de compte.
- **FR-017** : Une PME déjà authentifiée arrivant sur l'URL racine DOIT être redirigée automatiquement vers son espace authentifié.
- **FR-018** : Toutes les transitions et animations introduites DOIVENT respecter la préférence système `prefers-reduced-motion: reduce` et se neutraliser dans ce cas.
- **FR-019** : Toutes les chaînes visibles des pages d'authentification, du wizard, de l'onboarding et du tour DOIVENT provenir du référentiel de traductions français de l'application — aucune chaîne en dur dans le code de présentation.
- **FR-020** : Tous les formulaires (login, wizard, mot de passe oublié, reset) DOIVENT être totalement utilisables au clavier, leurs champs DOIVENT être étiquetés correctement pour les lecteurs d'écran, et leurs zones d'erreur DOIVENT être annoncées de manière non intrusive (politesse "polite").
- **FR-021** : Sur écrans étroits (< 768 px), les pages d'authentification DOIVENT masquer l'illustration de la disposition split-screen et afficher le formulaire en pleine largeur.
- **FR-022** : Le système DOIT exposer au frontend un moyen de lire et d'écrire la préférence individuelle "tour d'onboarding terminé/désactivé", de manière persistante et liée au compte utilisateur.
- **FR-023** : Le système DOIT exposer au frontend un moyen de lire le pourcentage de complétion du profil entreprise pour piloter la décision "empty state vs dashboard".
- **FR-024** : Les CGU et la politique de confidentialité présentés au step 3 du wizard DOIVENT être validés par le DPO avant mise en production (porte de gating non technique avant déploiement).
- **FR-025** : La cible de l'authentification après login DOIT respecter un éventuel deep link entrant (ex. l'utilisateur cliquant un lien protégé est ramené à cette destination après connexion plutôt que sur la page d'accueil par défaut).

### Key Entities *(include if feature involves data)*

- **Préférences utilisateur (onboarding)** : associent à chaque utilisateur authentifié un état du tour d'onboarding (`pending` / `completed` / `skipped` / `dismissed`) et le timestamp de la dernière action. Persistantes côté serveur, lisibles et modifiables par le frontend.
- **Demande de réinitialisation de mot de passe** : artefact transitoire associé à un utilisateur, à durée de vie limitée à 60 minutes après émission, à usage unique (invalidé dès la première utilisation réussie ou à expiration), pour autoriser la définition d'un nouveau mot de passe.
- **Bandeau de vérification d'email** : signal calculé à partir de l'état du compte ; pas de persistance dédiée — découle de l'état de vérification déjà tenu côté backend.
- **Métrique de complétion du profil entreprise** : indicateur (0 à 100 %) calculé sur le profil existant (consommé en lecture seule par cette feature).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur 5 PME en test utilisateur, au moins 4 complètent les 3 étapes du wizard d'inscription en moins de 90 secondes sans aide externe.
- **SC-002** : 100 % des sessions de tour guidé se déroulent sans bug bloquant (étape ne s'affiche pas, popover hors écran, bouton inactif), et l'option "Passer" est fonctionnelle à toutes les étapes.
- **SC-003** : Le parcours "mot de passe oublié → email → reset → reconnexion" se déroule de bout en bout sans régression sur 100 % des comptes de test, et le délai anti-spam de renvoi est strictement respecté.
- **SC-004** : Les pages de connexion et d'inscription atteignent un score d'accessibilité automatisé d'au moins 95/100.
- **SC-005** : La page de connexion s'affiche entièrement en moins de 1,2 seconde sur connexion typique cible (mesure du contenu principal visible).
- **SC-006** : 100 % des messages d'erreur visibles dans les pages d'authentification sont rédigés en français, sans code technique ni indication permettant de distinguer "compte inexistant" de "mot de passe incorrect".
- **SC-007** : Aucune chaîne en anglais ou en dur n'est détectable dans les pages auth/onboarding par revue manuelle d'un échantillon de 10 chaînes par page.
- **SC-008** : Avec `prefers-reduced-motion: reduce`, aucune animation au-delà d'un fondu instantané n'est observée sur les pages auth et l'onboarding.

## Assumptions

- Le backend d'authentification (création de compte, login, reset password, vérification email) défini en F02 est disponible et fonctionnel ; cette feature ajoute un endpoint de préférences utilisateur et consomme les endpoints existants.
- Le module de profil entreprise (F11) expose un pourcentage de complétion lisible côté frontend.
- Le référentiel des secteurs d'activité (F08) est disponible pour alimenter l'autocomplétion à l'étape 2 du wizard.
- Les utilisateurs cibles disposent d'un navigateur moderne (deux dernières versions majeures des principaux navigateurs) ; pas de support IE ni de très vieux Android.
- Les CGU et la politique de confidentialité sont fournis par le DPO avant la mise en production ; cette feature en consomme la version publiée sans en débattre le contenu.
- Connectivité instable acceptée comme contexte courant : les formulaires doivent rester utilisables et les retours d'erreur réseau explicites.
- Les écrans de référence pour le design split-screen sont desktop ≥ 1024 px ; le breakpoint mobile à 768 px est cohérent avec le design system existant.

## Dependencies

- **F02 — Authentification & RLS** : endpoints d'inscription, connexion, déconnexion, reset password, vérification email.
- **F11 — Profil entreprise** : lecture du pourcentage de complétion pour piloter l'empty state.
- **F08 — Catalogue secteurs** : autocomplétion au step 2 du wizard.
- **F36 — Design system tokens**, **F37 — UI primitives**, **F38 — App shell & navigation** : composants de base, layout, navigation.
- **F05 — Données privées & consentements** : textes CGU/RGPD, traçabilité des consentements.

## Out of Scope (MVP)

- Connexion via fournisseurs tiers (Google, LinkedIn, etc.) — repoussée en priorité 2.
- Vérification d'email rendue obligatoire avant usage — repoussée en priorité 2.
- Quiz d'onboarding "niveau ESG" — post-MVP.
- Animations riches type Lottie — post-MVP.
- Sauvegarde inter-session du brouillon de wizard d'inscription (localStorage / serveur) — post-MVP.
- Langues locales (Wolof, Bambara, etc.) — post-MVP.
- Onboarding différencié par secteur d'activité — post-MVP.

## Risks & Vigilance

- **Validation juridique des CGU/RGPD** : tout retard du DPO bloque la mise en production ; à programmer en parallèle de la conception.
- **Tour guidé sur mobile** : risque de popovers mal positionnés ; prévoir un fallback texte plein écran et tester sur cibles réelles.
- **Anti-énumération d'utilisateurs** : tout message ou code de retour différenciant un compte existant d'un compte inconnu doit être audité avant mise en production.
- **Wizard interrompu** : sans sauvegarde inter-session, un utilisateur fermant son onglet doit recommencer ; à communiquer clairement ou à compenser par une UX qui rassure (perception de rapidité).
- **Performance d'affichage de la page de connexion** : l'illustration et la police ne doivent pas dégrader le temps d'affichage cible ; prévoir formats légers et préchargement.
