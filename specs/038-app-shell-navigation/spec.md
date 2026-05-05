# Feature Specification: App Shell, Layout & Navigation

**Feature Branch**: `038-app-shell-navigation`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F38 — App Shell, Layout & Navigation : squelette commun à toutes les pages PME (layout principal, sidebar, top-bar, routing protégé, gestion auth, breadcrumbs, états globaux), layouts séparés pour pages publiques et pages d'authentification. Style épuré inspiré de Linear."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Squelette PME authentifié (Priority: P1)

Une PME connectée arrive sur n'importe quelle page applicative (tableau de bord, profil, projets, scoring…) et retrouve la même charpente : barre latérale gauche (logo + navigation principale), barre supérieure sobre (raison sociale, cloche de notifications, menu avatar), zone de contenu centrale fluide. La navigation entre rubriques se fait sans rechargement, avec une mini-barre de progression discrète pendant les transitions.

**Why this priority**: Sans cette charpente partagée, aucune page PME n'est utilisable de bout en bout. Toutes les fonctionnalités MVP (chat, profil, scoring, projets, candidatures, dashboard) en dépendent visuellement et fonctionnellement.

**Independent Test**: Connecter un compte PME stub, naviguer entre cinq rubriques différentes (Tableau de bord, Profil, Projets, Scoring, Paramètres), vérifier que sidebar, top-bar et breadcrumbs s'affichent de manière cohérente et que les transitions sont fluides (< 100 ms perçus).

**Acceptance Scenarios**:

1. **Given** une PME authentifiée sur `/dashboard`, **When** elle clique sur "Profil entreprise" dans la sidebar, **Then** la zone de contenu se met à jour sans rechargement complet, le breadcrumb devient "Accueil / Profil entreprise" et l'élément actif de la sidebar reflète la nouvelle rubrique.
2. **Given** une PME sur n'importe quelle page authentifiée, **When** elle ouvre le menu avatar et clique sur "Déconnexion", **Then** sa session est invalidée côté serveur, les cookies de session sont effacés et elle est redirigée vers `/login`.
3. **Given** une PME avec 3 notifications non lues, **When** elle ouvre la cloche de notifications, **Then** un popover affiche les 5 dernières notifications non lues avec un lien vers `/notifications`, et le badge compteur reflète le bon total.

---

### User Story 2 — Pages publiques et pages d'authentification distinctes (Priority: P1)

Les pages publiques (page de vérification d'attestation `/verify/{id}`, accueil marketing) s'affichent **sans sidebar ni top-bar applicative** : header minimal (logo) et footer mentions légales. Les pages d'authentification (`/login`, `/register`, `/forgot-password`, `/reset-password`) utilisent un layout split-screen (illustration/citation à gauche, formulaire à droite ; passage en pleine largeur sur mobile).

**Why this priority**: Indispensable pour permettre l'inscription, la connexion, la récupération de mot de passe, et la consultation publique des attestations vérifiables (P7 de la constitution). Aucun parcours d'entrée dans la plateforme n'est possible sans ces layouts dédiés.

**Independent Test**: Visiter `/login` et `/verify/{id-stub}` sans session, vérifier qu'aucun chrome PME (sidebar / top-bar applicative) ne s'affiche, et que le layout split-screen fonctionne sur écran ≥ 1024 px puis bascule en pleine largeur sur < 1024 px.

**Acceptance Scenarios**:

1. **Given** un visiteur non authentifié, **When** il accède à `/login`, **Then** il voit un layout split-screen sans sidebar PME, et le formulaire de connexion s'affiche à droite (ou en pleine largeur si la fenêtre fait moins de 1024 px).
2. **Given** un visiteur non authentifié, **When** il accède à `/verify/abc123`, **Then** la page s'affiche avec un header minimal, sans sidebar ni cloche de notifications, et avec un footer mentions légales.
3. **Given** une PME authentifiée, **When** elle accède à `/login`, **Then** elle est immédiatement redirigée vers `/dashboard`.

---

### User Story 3 — Navigation principale et palette de commandes (Priority: P1)

La sidebar liste les rubriques MVP : Tableau de bord, Profil entreprise, Projets, Plan d'action, Scoring ESG, Empreinte carbone, Score crédit, Candidatures, Rapports & attestations, Bibliothèque, Paramètres. Une palette de commandes globale (raccourci clavier dédié) permet de rechercher et d'atteindre rapidement n'importe quelle action ou page (MVP : actions/pages uniquement, pas de full-text).

**Why this priority**: Permet à la PME de circuler efficacement dans 11 rubriques sans surcharger l'écran ni dépendre uniquement du clic souris. La palette est un standard d'usage pour les utilisateurs réguliers.

**Independent Test**: Ouvrir la palette via le raccourci clavier, taper "scoring", appuyer sur Entrée, vérifier que la navigation amène sur `/scoring`. Vérifier qu'au moins 2 raccourcis (macOS et Windows/Linux) fonctionnent.

**Acceptance Scenarios**:

1. **Given** une PME sur `/dashboard`, **When** elle déclenche le raccourci d'ouverture de palette, **Then** la palette apparaît au centre de l'écran avec un champ de recherche focus.
2. **Given** la palette ouverte, **When** la PME tape "scoring" puis valide la première suggestion, **Then** la palette se ferme et la PME arrive sur `/scoring`.
3. **Given** un élément actif "Scoring ESG" dans la sidebar, **When** la PME y est effectivement, **Then** l'item porte un état visuel "actif" distinct des autres.

---

### User Story 4 — Responsive mobile avec drawer et bottom nav (Priority: P1)

Sur écrans étroits (< 1024 px), la sidebar bascule en drawer accessible via un bouton hamburger dans le header. Une barre de navigation inférieure simplifiée (4 icônes : Chat, Tableau de bord, Profil, Plus) reste visible en permanence sur mobile pour les actions les plus fréquentes.

**Why this priority**: Une part significative des PME ouest-africaines accède au web principalement sur smartphone. Sans expérience mobile soignée, l'adoption est compromise.

**Independent Test**: Redimensionner la fenêtre à moins de 1024 px de large, vérifier que la sidebar disparaît au profit d'un bouton hamburger, que la bottom-nav apparaît avec 4 cibles tactiles d'au moins 44×44 px, et que le drawer s'ouvre/ferme correctement.

**Acceptance Scenarios**:

1. **Given** une fenêtre redimensionnée à 360 × 640, **When** la PME charge `/dashboard`, **Then** la sidebar est masquée, le bouton hamburger est visible dans le header et la bottom-nav s'affiche avec 4 icônes.
2. **Given** la vue mobile, **When** la PME appuie sur le bouton hamburger, **Then** un drawer s'ouvre avec la navigation complète et un overlay sombre derrière.
3. **Given** la vue mobile, **When** la PME appuie sur l'icône "Plus" de la bottom-nav, **Then** un menu s'affiche listant les rubriques absentes des 4 raccourcis principaux.

---

### User Story 5 — Routes protégées et redirections (Priority: P1)

Toute tentative d'accès à une page applicative sans session valide redirige vers `/login`. Les comptes PME ne peuvent pas accéder aux pages réservées admin (et vice versa). Les pages explicitement publiques (login, register, forgot/reset password, verify) restent accessibles sans authentification.

**Why this priority**: Sécurité de base. Sans guards, des utilisateurs non authentifiés pourraient accéder à des pages PME (bug visuel + fuite d'information). Les comptes PME pourraient atterrir sur l'admin et vice versa, brisant la séparation de rôles (P7 constitution : seulement PME et Admin).

**Independent Test**: Tenter d'accéder à `/dashboard` sans cookie de session → redirection `/login` avec preservation de la destination. Tenter d'accéder à `/admin/*` avec un compte PME → blocage et redirection. Tenter d'accéder à une route PME avec un compte admin → blocage.

**Acceptance Scenarios**:

1. **Given** un visiteur sans cookie de session, **When** il tente `/dashboard`, **Then** il est redirigé vers `/login` et la destination initiale est mémorisée pour redirection post-connexion.
2. **Given** une PME authentifiée, **When** elle tente d'accéder à une URL `/admin/*`, **Then** l'accès est refusé et elle est redirigée vers `/dashboard`.
3. **Given** un admin authentifié, **When** il tente d'accéder à une URL PME-only (ex : `/scoring`), **Then** l'accès est refusé et il est redirigé vers la console admin.

---

### User Story 6 — États globaux (notifications temps réel, erreurs, hors-ligne) (Priority: P1)

Le shell affiche en temps réel : (a) une file d'attente de toasts pour les retours d'action, (b) une bannière discrète quand la connexion réseau est perdue, (c) une page de repli avec bouton "Recharger" en cas d'erreur non gérée, (d) la cloche de notifications synchronisée en temps réel via le flux d'événements serveur (avec fallback polling 60 s en cas d'indisponibilité).

**Why this priority**: Sans ces états globaux, la PME perd la confiance (échecs silencieux, état dépassé, app figée). Les notifications temps réel sont un attendu de produit moderne.

**Independent Test**: Déclencher une action backend qui pousse une notification, vérifier que le badge cloche s'incrémente sans recharger. Couper le réseau, vérifier l'apparition de la bannière hors-ligne. Forcer une exception dans une page, vérifier le repli avec bouton "Recharger".

**Acceptance Scenarios**:

1. **Given** une PME authentifiée sur `/dashboard`, **When** le serveur émet un événement de notification, **Then** le badge de la cloche reflète le nouveau compteur sans intervention de l'utilisateur en moins de 2 secondes.
2. **Given** une page applicative qui jette une exception non gérée, **When** l'erreur survient, **Then** la zone de contenu affiche un message de repli "Une erreur est survenue" avec un bouton "Recharger" qui rétablit la page.
3. **Given** une PME authentifiée, **When** la connexion réseau est perdue, **Then** une bannière discrète apparaît en haut de l'écran indiquant "Connexion perdue" et disparaît dès la reconnexion.

---

### User Story 7 — Breadcrumbs automatiques (Priority: P2)

Chaque page applicative annonce ses fils d'Ariane via une métadonnée de route. Le shell les rend automatiquement dans la top-bar au format "Accueil / Profil / Projets / Mon projet ABC", chaque segment cliquable (sauf le dernier).

**Why this priority**: Améliore le repérage et la navigation hiérarchique. Pas bloquant pour l'usage, mais important pour l'expérience.

**Independent Test**: Naviguer dans une page imbriquée (ex : un projet précis), vérifier que le breadcrumb correspond à la hiérarchie attendue et que chaque segment, sauf le dernier, est cliquable.

**Acceptance Scenarios**:

1. **Given** une PME sur la page d'un projet, **When** elle regarde le breadcrumb, **Then** elle voit "Accueil / Projets / [Nom du projet]" avec les deux premiers segments cliquables.
2. **Given** une PME sur le tableau de bord, **When** elle regarde le breadcrumb, **Then** elle voit uniquement "Accueil" (segment racine, non cliquable).

---

### User Story 8 — Sélecteur de langue dans le menu avatar (Priority: P2)

Le menu avatar propose un sélecteur de langue FR / EN. Au MVP, le français est actif et l'anglais est visible mais grisé/désactivé. Le placement réserve l'expérience d'internationalisation future sans complexifier le MVP.

**Why this priority**: Préparation visuelle pour i18n future ; pas bloquant pour le MVP en français.

**Independent Test**: Ouvrir le menu avatar, vérifier la présence d'un sélecteur "Langue" avec FR (actif) et EN (grisé / non cliquable), et qu'aucune action n'est possible sur EN.

**Acceptance Scenarios**:

1. **Given** une PME francophone, **When** elle ouvre le menu avatar, **Then** elle voit "Langue : FR" comme actif et "EN" en état désactivé.

---

### Edge Cases

- **Reload à froid d'une page profonde** (ex : `/projets/abc/scoring`) : la sidebar et l'état d'authentification doivent être cohérents après un rendu serveur initial, sans flash d'état non authentifié puis bascule.
- **Conflit de raccourci clavier de la palette** sur macOS (ex : combinaisons système réservées) : la palette doit accepter au moins une combinaison alternative pour ne pas être inaccessible.
- **Session expirée pendant la navigation** : un appel API qui retourne 401 doit déclencher la déconnexion propre (clear stores + redirect `/login`) plutôt qu'un état d'erreur générique.
- **Notification reçue alors que la cloche est déjà ouverte** : la liste se met à jour en place sans fermer le popover.
- **Navigation mobile en rotation portrait/paysage** : la bascule sidebar/drawer doit s'opérer au franchissement du seuil 1024 px sans casser l'état courant (drawer ouvert vs sidebar dépliée).
- **Reduce motion préféré par le système** : les animations de transition de route, d'ouverture/fermeture du drawer et de la palette doivent être atténuées ou supprimées.
- **Breadcrumb sans métadonnée déclarée** sur une page : un repli neutre (titre de la page courante seulement) doit s'afficher sans erreur.
- **Connexion lente** : la barre de progression de transition de route doit rester visible jusqu'au rendu effectif, sans donner l'impression d'une app figée.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer trois layouts distincts — `default` (PME authentifiée), `public` (accueil marketing + pages de vérification d'attestation), `auth` (connexion / inscription / récupération de mot de passe) — automatiquement appliqués selon la route demandée.
- **FR-002**: Le layout `default` DOIT comporter une sidebar gauche listant les 11 rubriques MVP (Tableau de bord, Profil entreprise, Projets, Plan d'action, Scoring ESG, Empreinte carbone, Score crédit, Candidatures, Rapports & attestations, Bibliothèque, Paramètres), une top-bar (raison sociale, breadcrumb, cloche de notifications, menu avatar) et une zone de contenu fluide.
- **FR-003**: La sidebar DOIT marquer visuellement la rubrique active correspondant à la route courante.
- **FR-004**: La sidebar DOIT afficher un badge de compteur sur les rubriques recevant des notifications non lues (au minimum sur la cloche globale).
- **FR-005**: Le layout `public` DOIT afficher un header minimal (logo) et un footer mentions légales, sans sidebar ni top-bar applicative ni cloche de notifications.
- **FR-006**: Le layout `auth` DOIT proposer une présentation split-screen sur écrans larges (≥ 1024 px) — illustration ou citation à gauche, formulaire à droite — et basculer en pleine largeur sous 1024 px.
- **FR-007**: Le système DOIT empêcher l'accès aux pages applicatives sans session valide en redirigeant vers `/login`, et préserver la destination initiale pour redirection post-connexion.
- **FR-008**: Le système DOIT séparer strictement les espaces PME et Admin : un compte PME ne peut pas accéder aux URLs `/admin/*`, et un compte admin ne peut pas accéder aux pages réservées PME.
- **FR-009**: Les pages explicitement publiques (login, register, forgot-password, reset-password, verify) DOIVENT être marquées comme telles dans leurs métadonnées de route et ignorées par le guard d'authentification.
- **FR-010**: Le menu avatar DOIT proposer au minimum : lien "Mon compte", lien "Paramètres", action "Déconnexion".
- **FR-011**: L'action "Déconnexion" DOIT invalider la session côté serveur, vider les états locaux d'authentification et de notifications, puis rediriger vers `/login`.
- **FR-012**: Le système DOIT exposer une palette de commandes globale ouverte par raccourci clavier, supportant au moins deux combinaisons (une macOS, une Windows/Linux) pour éviter les conflits.
- **FR-013**: La palette DOIT permettre, au MVP, la recherche et la navigation vers des actions ou pages prédéfinies (pas de recherche full-text de contenu).
- **FR-014**: Le système DOIT afficher un breadcrumb dans la top-bar dérivé d'une métadonnée déclarée par chaque route (`route.meta.breadcrumb`), avec un repli neutre quand la métadonnée est absente.
- **FR-015**: Sous 1024 px de largeur d'écran, la sidebar DOIT être remplacée par un drawer accessible via un bouton hamburger dans le header.
- **FR-016**: Sous 1024 px de largeur d'écran, le système DOIT afficher une barre de navigation inférieure simplifiée à 4 icônes : Chat, Tableau de bord, Profil, Plus.
- **FR-017**: Toute cible tactile mobile DOIT mesurer au moins 44 × 44 px.
- **FR-018**: Le système DOIT afficher une mini-barre de progression discrète (≈ 2 px, couleur de marque) en haut de l'écran pendant les transitions de route.
- **FR-019**: Le système DOIT exposer une file d'attente globale de toasts utilisable depuis n'importe quelle page pour notifier l'utilisateur.
- **FR-020**: Le système DOIT envelopper les pages applicatives d'un mécanisme de type ErrorBoundary qui, en cas d'exception non gérée, affiche un message de repli avec un bouton "Recharger" rétablissant la page.
- **FR-021**: Le système DOIT afficher une bannière discrète quand la connexion réseau est perdue et la masquer dès la reconnexion.
- **FR-022**: Le layout `default` DOIT s'abonner au flux d'événements serveur de l'utilisateur courant pour mettre à jour en temps réel le compteur et la liste des notifications, avec un fallback de polling à 60 s en cas d'échec d'abonnement.
- **FR-023**: La cloche de notifications DOIT afficher en popover les 5 dernières notifications non lues et un lien "Voir toutes" vers `/notifications`.
- **FR-024**: Le menu avatar DOIT exposer un sélecteur de langue FR / EN, FR actif et EN visible mais désactivé au MVP.
- **FR-025**: Toutes les animations du shell (transition de route, ouverture/fermeture du drawer, ouverture de la palette) DOIVENT respecter la préférence système `prefers-reduced-motion`.
- **FR-026**: La transition perçue entre deux pages PME (du clic sur un lien à l'apparition du nouveau contenu) DOIT rester sous 100 ms côté rendu client.
- **FR-027**: En cas d'appel d'API authentifié retournant un statut "non authentifié" (ex : session expirée), le système DOIT déclencher la procédure de déconnexion propre puis rediriger vers `/login`.
- **FR-028**: La sidebar DOIT conserver une largeur fixe (un état déplié, un état rail compact) sans contrôle utilisateur de redimensionnement libre au MVP.

### Key Entities *(include if feature involves data)*

- **Session utilisateur** : représente l'état d'authentification courant côté client (identifiant utilisateur, identifiant compte, rôle PME/Admin, raison sociale affichable). Source de vérité côté serveur via cookies de session.
- **Notification** : élément consultable depuis la cloche (titre, horodatage, état lu/non lu, lien profond optionnel). Liste tronquée aux 5 plus récentes non lues dans le popover.
- **Métadonnée de route** : déclaration attachée à chaque page définissant son layout (`default`/`public`/`auth`), ses guards (publique, PME-only, admin-only) et son fil d'Ariane (`breadcrumb`).
- **Action de palette** : entrée recherchable dans la palette de commandes (libellé, description courte, icône optionnelle, route ou action cible).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME authentifiée peut naviguer entre 5 rubriques distinctes en moins de 10 secondes au total, sans rechargement complet entre chaque page.
- **SC-002**: La transition de route perçue (clic → premier rendu de la nouvelle page) reste sous 100 ms dans 95 % des navigations sur connexion ≥ 4G.
- **SC-003**: 100 % des pages applicatives sont inaccessibles sans session valide (vérifié par tentative d'accès direct à au moins 5 routes protégées).
- **SC-004**: 100 % des pages publiques (login, register, forgot/reset password, verify) sont accessibles sans cookie de session.
- **SC-005**: Le passage en mode mobile (< 1024 px) déclenche systématiquement l'apparition du drawer + bottom-nav et la disparition de la sidebar large, vérifié sur trois résolutions cibles (360, 412, 768 px).
- **SC-006**: La palette de commandes ouvre en moins de 200 ms après l'appui clavier et résout une recherche d'action en moins de 100 ms.
- **SC-007**: Une nouvelle notification poussée par le serveur apparaît dans le badge de la cloche en moins de 2 secondes pour 95 % des cas.
- **SC-008**: La déconnexion supprime tous les cookies de session et tous les états locaux liés à l'utilisateur (vérifiable depuis les outils de développement du navigateur).
- **SC-009**: 100 % des cibles tactiles de la navigation mobile mesurent au moins 44 × 44 px (audit visuel + automatisé).
- **SC-010**: 0 régression visuelle sur le shell entre deux refactorings consécutifs (validé par capture d'écran de référence sur les 3 layouts).

## Assumptions

- L'authentification (cookies de session, endpoints `/auth/login`, `/auth/logout`) est fournie par F02 (Auth) et fonctionnelle.
- Les primitives UI (boutons, champs, modaux, toasts, popovers, command palette de base) sont disponibles via F37 et les tokens de design via F36.
- Le flux d'événements temps réel `/me/events` est fourni par F41 ; en cas d'indisponibilité ou de retard, le fallback polling 60 s reste fonctionnel.
- Le rendu côté serveur est utilisé pour les pages applicatives ; l'état d'authentification est déterminable dès le premier rendu (pas de "flash" client-only).
- Le MVP cible un seul compte par utilisateur (P7 constitution) ; aucun sélecteur multi-tenant n'est requis dans le shell.
- Les langues locales (Wolof, Bambara, …) sont post-MVP ; seul FR est pleinement actif, EN reste un placeholder visuel.
- La recherche de la palette se limite aux actions et pages prédéfinies au MVP ; la recherche full-text de contenu est différée.
- Les rubriques listées en sidebar peuvent encore évoluer marginalement selon l'avancement des features dépendantes (036, 037, 02), mais l'architecture du shell n'en dépend pas.
- Les pages réelles derrière les rubriques sont livrées par d'autres features ; le shell se contente, au MVP de F38, de pages stubs ou réelles selon disponibilité, sans bloquer son acceptation.
