# Feature Specification: Notifications, Paramètres, Exports & Panneau d'extension

**Feature Branch**: `052-notifications-settings-extension`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "F52 — Notifications + Settings + Exports + Extension panneau (UI de F34/F05/F32)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Centre des notifications (Priority: P1)

L'utilisateur PME consulte une page dédiée listant toutes ses notifications (deadlines de candidatures, candidatures inactives, offres recommandées). Il filtre par statut (lues/non-lues), par type et par plage de dates, ouvre le détail dans un panneau latéral, et peut tout marquer comme lu en une action.

**Why this priority** : Sans visibilité centralisée, l'utilisateur rate les échéances critiques (J-30/J-7/J-1) de ses candidatures et perd l'opportunité de boucler son dossier. C'est le canal in-app principal pour rappels et offres recommandées.

**Independent Test** : L'utilisateur ouvre `/notifications`, voit la liste paginée de ses notifications, applique un filtre "non-lues", clique une ligne pour lire le détail, puis utilise "Tout marquer comme lu" — la cloche d'en-tête repasse à 0.

**Acceptance Scenarios** :

1. **Given** un utilisateur avec 12 notifications dont 5 non-lues, **When** il ouvre `/notifications`, **Then** il voit la liste paginée avec un badge "5 non-lues" et chaque ligne affiche type (badge), titre, extrait de message, date de création et date de lecture.
2. **Given** la liste affichée, **When** l'utilisateur active le filtre "non-lues" puis sélectionne le type "deadline_j_minus_7", **Then** la liste se met à jour pour ne montrer que les éléments correspondants.
3. **Given** une notification non lue, **When** l'utilisateur clique la ligne, **Then** un panneau latéral s'ouvre avec le contenu complet et l'action contextuelle (ex. "Reprendre la candidature"), et la notification passe en "lue".
4. **Given** plusieurs notifications non-lues, **When** l'utilisateur clique "Tout marquer comme lu", **Then** toutes passent en "lue", la cloche en en-tête repasse à 0, et l'action est annulable en cas d'erreur réseau.
5. **Given** un utilisateur sans aucune notification, **When** il ouvre `/notifications`, **Then** un état vide illustré s'affiche avec un message "Aucune notification".
6. **Given** la page ouverte, **When** une nouvelle notification est émise côté serveur, **Then** elle apparaît en haut de la liste sans rechargement et le compteur de la cloche s'incrémente.

---

### User Story 2 — Paramètres du compte (profil, préférences, sécurité, RGPD) (Priority: P1)

L'utilisateur accède à un espace de réglages organisé en sections : informations personnelles, préférences de notifications, consentements RGPD, sécurité (sessions actives), export de ses données, et zone dangereuse pour la suppression de compte.

**Why this priority** : Les obligations RGPD (consentements traçables, droit à l'effacement, portabilité des données) sont un prérequis légal non négociable pour exploiter la plateforme en UE/UEMOA. La gestion du profil et des préférences de canaux conditionne par ailleurs la qualité des notifications.

**Independent Test** : L'utilisateur ouvre `/parametres`, modifie son nom, active/désactive un canal de notification, retire un consentement, télécharge son archive de données et constate que toutes ces actions sont prises en compte.

**Acceptance Scenarios** :

1. **Given** un utilisateur connecté, **When** il modifie son nom, sa photo et sa langue puis valide, **Then** les changements sont enregistrés et reflétés immédiatement dans l'en-tête.
2. **Given** un utilisateur qui change son adresse e-mail, **When** il valide, **Then** la nouvelle adresse passe en statut "en attente de vérification", un e-mail de confirmation est envoyé, et l'ancienne reste active jusqu'à validation.
3. **Given** la section "Préférences de notifications", **When** l'utilisateur désactive le canal e-mail pour le type "deadline_j_minus_30", **Then** le toggle est sauvegardé et plus aucune notification de ce type ne lui est envoyée par e-mail (l'in-app reste si activé).
4. **Given** un consentement RGPD actif, **When** l'utilisateur clique "Retirer", confirme, **Then** le retrait est journalisé en audit, un e-mail de confirmation est envoyé et la liste reflète la nouvelle date.
5. **Given** la section "Sessions actives", **When** l'utilisateur révoque une session distante, **Then** cette session est invalidée et déconnectée à sa prochaine requête.
6. **Given** la section "Mes données", **When** l'utilisateur clique "Télécharger toutes mes données", **Then** une archive complète au format portable est générée et un lien de téléchargement temporaire lui est fourni.
7. **Given** la "Zone dangereuse", **When** l'utilisateur clique "Supprimer mon compte", saisit la raison sociale exacte de son entreprise et confirme, **Then** une suppression différée de 30 jours est planifiée, un e-mail de confirmation est envoyé, et un message indique la date d'effacement définitif et la possibilité d'annuler avant cette date.

---

### User Story 3 — Historique et génération d'exports (Priority: P1)

L'utilisateur consulte l'historique des exports déjà générés (rapports PDF, archives JSON) et lance la génération d'un nouvel export à la demande.

**Why this priority** : La portabilité des données et la traçabilité des rapports produits sont indispensables pour partage avec banque/fonds et audit interne. Sans ce centre d'historique, les utilisateurs régénèrent inutilement des fichiers volumineux.

**Independent Test** : L'utilisateur ouvre `/dashboard/exports`, voit la liste des exports passés, lance un nouvel export, reçoit un lien temporaire dès qu'il est prêt et peut le télécharger.

**Acceptance Scenarios** :

1. **Given** un utilisateur avec 4 exports antérieurs, **When** il ouvre `/dashboard/exports`, **Then** il voit un tableau avec type (PDF/JSON), date, taille et un lien de téléchargement temporaire pour chaque ligne.
2. **Given** la page ouverte, **When** l'utilisateur clique "Nouvel export", choisit le type et le format, **Then** la génération démarre en arrière-plan, l'utilisateur peut quitter la page, et il est notifié dès que le lien de téléchargement est disponible.
3. **Given** un export terminé dont la taille dépasse 100 Mo, **When** il est prêt, **Then** une notification dédiée est envoyée par e-mail avec le lien (au lieu d'un téléchargement direct in-app).
4. **Given** un lien d'export expiré, **When** l'utilisateur clique dessus, **Then** un message clair indique que le lien est expiré et propose de regénérer.

---

### User Story 4 — Panneau latéral d'extension navigateur (Priority: P1)

Lorsque l'utilisateur navigue sur une plateforme financière listée (ex. site BOAD, banque partenaire), un panneau latéral coulissant à droite s'affiche avec ses candidatures actives, leur progression et un raccourci "Reprendre".

**Why this priority** : Le scénario phare est de retomber sur sa candidature au moment où la PME consulte la plateforme du financeur — sans cette présence contextuelle, le taux de complétion chute. C'est le différenciateur produit de l'extension.

**Independent Test** : L'utilisateur installe l'extension, ouvre une URL de plateforme listée (ex. site BOAD de test), et constate qu'un panneau latéral s'ouvre montrant ses 2 candidatures actives sur cette offre, avec progression et bouton "Reprendre".

**Acceptance Scenarios** :

1. **Given** une URL de plateforme listée et un utilisateur authentifié, **When** la page se charge, **Then** un panneau latéral d'environ 350–450 px de large s'affiche à droite, sticky au scroll, avec en-tête (logo + bouton fermer).
2. **Given** une URL non listée, **When** la page se charge, **Then** aucun panneau ne s'affiche.
3. **Given** le panneau ouvert, **When** l'utilisateur clique "Reprendre" sur une candidature active, **Then** un nouvel onglet s'ouvre directement sur la candidature en question dans la plateforme principale.
4. **Given** le panneau ouvert, **When** l'utilisateur clique "Fermer", **Then** le panneau se replie et reste fermé pour la session courante de l'onglet.
5. **Given** plusieurs onglets ouverts sur des sites différents, **When** un onglet affiche le panneau, **Then** aucune information d'un autre tenant ne fuite vers le site visité (cloisonnement strict).

---

### User Story 5 — Synchronisation extension ↔ application (Priority: P2)

L'utilisateur voit dans `/parametres` si son extension est connectée et la date du dernier ping, et peut forcer une synchronisation.

**Why this priority** : Utile pour diagnostiquer un panneau qui n'apparaît pas, mais non bloquant pour le MVP : une PME peut continuer à utiliser l'application sans extension.

**Independent Test** : L'utilisateur ouvre `/parametres`, voit le statut "Extension connectée — dernier ping il y a 12 min", clique "Synchroniser maintenant" et le statut se met à jour.

**Acceptance Scenarios** :

1. **Given** une extension installée et active, **When** l'utilisateur ouvre la section "Connecté", **Then** le statut "Extension détectée" et la date du dernier ping s'affichent.
2. **Given** le statut affiché, **When** l'utilisateur clique "Synchroniser maintenant", **Then** un nouveau ping est déclenché et la date affichée est rafraîchie.

---

### User Story 6 — Aide IA contextuelle et offres recommandées dans le panneau (Priority: P2)

Le panneau latéral propose un mini-chat IA pour aider l'utilisateur sur la plateforme visitée, et 3 cartes d'offres recommandées compatibles avec son projet.

**Why this priority** : Augmente la valeur perçue de l'extension mais reste un complément. Le panneau peut livrer son cœur de valeur (suivi candidatures) sans ces éléments.

**Independent Test** : Sur une plateforme listée, l'utilisateur fait défiler le panneau, voit 3 cartes d'offres compatibles, clique sur l'une d'elles et arrive sur la page de matching dans un nouvel onglet ; il pose une question dans le mini-chat et reçoit une réponse contextuelle.

**Acceptance Scenarios** :

1. **Given** un projet utilisateur défini, **When** le panneau s'ouvre sur une plateforme listée, **Then** 3 cartes d'offres compatibles sont affichées dans le panneau.
2. **Given** une carte d'offre, **When** l'utilisateur clique, **Then** un nouvel onglet s'ouvre sur la page de matching dédiée.
3. **Given** le mini-chat dans le panneau, **When** l'utilisateur saisit une question contextuelle, **Then** une réponse IA est retournée et toute saisie interactive nécessaire (formulaires, fichiers) est demandée dans une feuille inférieure dédiée, jamais dans la bulle de chat.

---

### User Story 7 — Notifications push de l'extension (Priority: P2)

L'extension émet une notification système lorsqu'une deadline de candidature est imminente (< 24 h) ; un clic sur la notification ouvre la candidature concernée.

**Why this priority** : Renforce l'engagement mais ajoute un canal supplémentaire pouvant générer du bruit ; les notifications in-app et e-mail couvrent déjà l'essentiel.

**Acceptance Scenarios** :

1. **Given** une candidature dont la deadline est dans moins de 24 h et l'utilisateur a accepté les notifications système, **When** l'extension est active, **Then** une notification système est émise.
2. **Given** la notification, **When** l'utilisateur clique dessus, **Then** la candidature concernée s'ouvre dans la plateforme.

---

### Edge Cases

- **Lien d'export expiré** : message clair et bouton "Regénérer" ; ne pas exposer l'ancien chemin.
- **Échec batch "Tout marquer comme lu"** : interface optimiste suivie d'un rollback visible si l'opération échoue côté serveur.
- **Suppression de compte tentée puis annulée** : possibilité d'annuler le compte à effacer pendant la fenêtre de 30 jours, avec confirmation.
- **Modification d'e-mail non confirmée** : la nouvelle adresse n'est utilisée qu'après vérification ; si la fenêtre de vérification expire, l'ancienne reste seule active.
- **Retrait d'un consentement nécessaire au service** : prévenir explicitement de l'impact (perte d'accès à certaines fonctions) avant de confirmer.
- **Export RGPD volumineux (> 100 Mo)** : ne pas saturer le navigateur ; livrer le lien par e-mail.
- **Panneau d'extension sur URL listée mais utilisateur non connecté** : afficher un état "Veuillez vous connecter" avec lien vers la plateforme, sans révéler aucune donnée.
- **Plusieurs onglets ouverts sur des plateformes différentes** : le panneau de l'onglet A ne doit jamais exposer les données du tenant de l'onglet B.
- **Notification non-lue concernant une candidature supprimée** : la ligne reste lisible et le clic indique que la candidature liée n'existe plus, sans erreur 500.
- **Collision avec le DOM du site visité** : l'injection du panneau ne doit pas casser la mise en page du site hôte ni intercepter ses raccourcis clavier.

## Requirements *(mandatory)*

### Functional Requirements

#### Centre des notifications

- **FR-001** : Le système DOIT proposer une page listant les notifications de l'utilisateur, paginée, avec colonnes type, titre, extrait, date de création, date de lecture.
- **FR-002** : Le système DOIT permettre de filtrer la liste par "non-lues uniquement", par type de notification et par plage de dates.
- **FR-003** : Le système DOIT permettre d'ouvrir le détail complet d'une notification dans un panneau latéral, incluant son contenu intégral et une action contextuelle pertinente.
- **FR-004** : Le système DOIT permettre de marquer une notification individuelle ou la totalité des non-lues comme "lues" en une action, avec mise à jour immédiate du compteur global (cloche).
- **FR-005** : Le système DOIT afficher un état vide illustré et explicite lorsqu'aucune notification n'existe.
- **FR-006** : Le système DOIT mettre à jour la liste en temps quasi-réel à l'arrivée de nouvelles notifications, sans rechargement manuel.

#### Paramètres — profil

- **FR-007** : Le système DOIT permettre à l'utilisateur de modifier son nom, sa photo et sa langue d'interface.
- **FR-008** : Le système DOIT exiger une nouvelle vérification lorsque l'utilisateur change son adresse e-mail, en conservant l'ancienne active jusqu'à validation.
- **FR-009** : Le système DOIT proposer un point d'entrée pour changer le mot de passe.

#### Paramètres — préférences de notifications

- **FR-010** : Le système DOIT permettre à l'utilisateur d'activer/désactiver indépendamment les canaux e-mail et in-app pour chaque type de notification (deadline J-30, J-7, J-1, candidature inactive, offre recommandée).
- **FR-011** : Le système DOIT respecter ces préférences pour tous les envois ultérieurs.

#### Paramètres — RGPD et sécurité

- **FR-012** : Le système DOIT lister les consentements RGPD actifs avec leur date d'octroi et permettre leur retrait avec confirmation.
- **FR-013** : Le système DOIT envoyer un e-mail de confirmation et journaliser en audit toute opération sensible (retrait de consentement, suppression de compte).
- **FR-014** : Le système DOIT exposer les liens vers la politique de confidentialité et les coordonnées du DPO.
- **FR-015** : Le système DOIT lister les sessions actives de l'utilisateur et permettre la révocation individuelle de chacune.
- **FR-016** : Le système DOIT permettre à l'utilisateur de télécharger l'intégralité de ses données dans un format portable et lisible par machine.
- **FR-017** : Le système DOIT proposer une procédure de suppression de compte exigeant la saisie exacte de la raison sociale de l'entreprise, planifiant l'effacement après un délai de 30 jours, avec possibilité d'annulation pendant ce délai et un e-mail de confirmation immédiat.

#### Historique des exports

- **FR-018** : Le système DOIT lister les exports passés (type, date, taille) avec un lien de téléchargement temporaire.
- **FR-019** : Le système DOIT permettre la génération à la demande d'un nouvel export en arrière-plan, en notifiant l'utilisateur dès que le lien est disponible.
- **FR-020** : Lorsqu'un export dépasse 100 Mo, le système DOIT livrer le lien par e-mail dédié plutôt que par téléchargement in-app direct.

#### Panneau d'extension navigateur

- **FR-021** : L'extension DOIT détecter les URLs listées au catalogue et n'afficher le panneau latéral que sur celles-ci.
- **FR-022** : Le panneau DOIT afficher la liste compacte des candidatures actives de l'utilisateur (deadline, pourcentage de complétion, action "Reprendre").
- **FR-023** : Le panneau DOIT permettre la fermeture par l'utilisateur, persistante pour la session de l'onglet.
- **FR-024** : Le panneau DOIT être responsive entre 350 et 450 px de largeur et rester sticky au scroll de la page hôte.
- **FR-025** : Le panneau DOIT proposer un mini-chat IA contextuel et 3 cartes d'offres compatibles avec le projet de l'utilisateur (P2).
- **FR-026** : L'extension DOIT pouvoir émettre une notification système lorsqu'une deadline est imminente (< 24 h), avec ouverture de la candidature au clic (P2).
- **FR-027** : Le système DOIT empêcher toute fuite de données entre tenants/comptes via les communications entre l'extension et la plateforme.

#### Synchronisation extension ↔ application

- **FR-028** : `/parametres` DOIT afficher l'état de connexion de l'extension (détectée/non détectée) et la date du dernier ping (P2).
- **FR-029** : Le système DOIT proposer une action "Synchroniser maintenant" qui rafraîchit l'état (P2).

### Key Entities *(include if feature involves data)*

- **Notification** : message destiné à l'utilisateur ; attributs : type/kind, titre, contenu, date de création, date de lecture, action contextuelle, lien vers l'entité associée (candidature, offre).
- **Préférence de notification** : couple (type, canal) avec un état activé/désactivé par utilisateur.
- **Consentement RGPD** : enregistrement d'un consentement (finalité, version du texte, date d'octroi, date de retrait éventuelle), traçable et auditable.
- **Session active** : session authentifiée de l'utilisateur (date, dispositif, localisation approximative, dernier accès) révocable individuellement.
- **Demande de suppression de compte** : enregistrement avec date demandée, date d'effacement planifiée (J+30), statut (en attente, annulée, exécutée).
- **Export** : artefact généré (type PDF/JSON, date, taille, lien temporaire, statut, expiration).
- **Cible d'extension (URL listée)** : motif d'URL au catalogue qui déclenche l'apparition du panneau.
- **Ping d'extension** : trace de la dernière communication réussie entre l'extension et la plateforme.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : 95 % des utilisateurs ouvrant `/notifications` voient leur liste affichée en moins d'1 seconde.
- **SC-002** : Marquer 10 notifications "lues" en lot met à jour l'ensemble et ramène le compteur de la cloche à 0 dans la même action.
- **SC-003** : 100 % des changements d'adresse e-mail déclenchent une vérification et l'ancienne adresse reste active jusqu'à confirmation.
- **SC-004** : 100 % des retraits de consentement RGPD et des demandes de suppression de compte génèrent une trace auditable et un e-mail de confirmation.
- **SC-005** : Une demande de suppression de compte s'exécute exactement 30 jours après la confirmation, sauf annulation préalable de l'utilisateur.
- **SC-006** : 100 % des exports volumineux (> 100 Mo) sont livrés par e-mail dédié, sans saturation de l'interface.
- **SC-007** : Sur une URL de plateforme listée de test (ex. BOAD), au moins 2 candidatures actives s'affichent dans le panneau d'extension en moins de 500 ms après chargement de la page.
- **SC-008** : Aucune fuite de données entre comptes ne peut être démontrée lors d'un test de cloisonnement multi-onglets/multi-comptes.
- **SC-009** : Le téléchargement d'archive personnelle complète est disponible en moins de 5 minutes pour un compte standard.
- **SC-010** : 90 % des utilisateurs trouvent et ajustent leurs préférences de notifications en moins de 60 secondes lors d'un test d'utilisabilité.

## Assumptions

- L'utilisateur est authentifié et appartient au rôle PME ; les écrans Admin du back-office sont hors scope.
- Les canaux de notification couverts au MVP sont l'e-mail et l'in-app ; SMS, WhatsApp, Slack et webhooks PME sont post-MVP.
- L'authentification à deux facteurs est mentionnée dans la section sécurité mais reportée en P2 (hors MVP).
- L'extension est livrée pour Chrome, Edge et Brave au MVP ; Firefox est post-MVP.
- Les notifications système natives de l'extension sont reportées en P2 pour limiter la sur-sollicitation des canaux.
- Le délai de grâce avant suppression définitive est fixé à 30 jours, conforme à une pratique RGPD défensive (annulable par l'utilisateur).
- Le seuil de 100 Mo pour bascule export → e-mail est un seuil produit, ajustable par configuration.
- Le panneau latéral d'extension occupe 350–450 px et n'altère pas le DOM du site hôte au-delà de l'injection du conteneur du panneau.
- La page `/notifications` repose sur un mécanisme push serveur déjà fourni par les fonctionnalités amont (centre de notifications backend) ; la couche temps réel est consommée mais pas re-spécifiée ici.
- Les textes RGPD (politique de confidentialité, mentions DPO) sont fournis et validés par l'équipe juridique avant mise en production.
- Toute saisie interactive (formulaires de modification, sélecteurs) au sein du mini-chat de l'extension passe par une feuille inférieure (bottom sheet), conformément à la règle UX du produit.
