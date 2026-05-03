# Feature Specification: Dashboard PME UI

**Feature Branch**: `044-dashboard-pme-ui`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F44 — Dashboard PME UI (UI de F32). Page d'accueil PME post-login : vue 360° lisible en 5 secondes (scoring ESG, empreinte carbone, score crédit, candidatures, rapports/attestations, plan d'action), bouton chat IA, export données, état vide intelligent. Grille de cartes sobres, max 6 cartes principales above-the-fold."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vue 360° en 5 secondes (Priority: P1)

Une dirigeante de PME se connecte le matin. En arrivant sur sa page d'accueil, elle doit comprendre en 5 secondes où en est son entreprise sur les trois piliers verts (scoring ESG, empreinte carbone, score crédit), combien de candidatures sont en cours, et ce qu'elle doit faire en priorité aujourd'hui. Un bandeau d'accueil affiche son nom commercial, la date du dernier diagnostic, et un bouton proéminent pour discuter avec l'IA.

**Why this priority**: C'est la fonction-cœur du tableau de bord et la première impression post-login. Sans cette vue d'ensemble, la PME perd confiance dans la plateforme et les autres fonctionnalités (scoring, candidatures, plan d'action) restent peu utilisées car non découvertes.

**Independent Test**: Connecter un compte PME possédant déjà des données (scoring, carbone, crédit, ≥1 candidature, ≥1 rapport, ≥1 étape de plan d'action), ouvrir la page d'accueil, et vérifier qu'un visiteur naïf peut citer en moins de 5 secondes : score global ESG, total annuel d'émissions, statut crédit, nombre de candidatures en cours.

**Acceptance Scenarios**:

1. **Given** une PME avec données complètes, **When** elle ouvre sa page d'accueil après login, **Then** six cartes principales (scores ESG, empreinte carbone, score crédit, candidatures, rapports & attestations, plan d'action) sont visibles sans défilement sur écran de bureau standard.
2. **Given** la même PME, **When** elle clique sur la carte "Scores ESG", **Then** elle est redirigée vers la page détail du scoring sans rechargement perçu (transition fluide).
3. **Given** la PME, **When** elle clique sur le bouton "Discuter avec l'IA" du bandeau, **Then** l'interface de chat conversationnel s'ouvre prête à recevoir une question.
4. **Given** la PME, **When** la page se charge, **Then** chaque carte affiche d'abord un état de chargement visuel (squelette) puis se remplit, sans afficher d'écran blanc à aucun moment.

---

### User Story 2 — Agir sur le plan d'action depuis la carte (Priority: P1)

Depuis la page d'accueil, l'utilisatrice voit les trois prochaines étapes prioritaires de son plan d'action. Elle peut cocher une étape comme terminée directement depuis la carte, sans naviguer ailleurs.

**Why this priority**: Le plan d'action est le moteur de progression de la PME. Permettre la complétion sans changer de page maximise la fréquence de mise à jour et donne un sentiment d'avancement immédiat.

**Independent Test**: Avec une PME possédant ≥3 étapes de plan d'action en attente, ouvrir le tableau de bord, cocher la première étape, vérifier qu'elle disparaît de la liste, qu'une nouvelle étape apparaît à sa place, et qu'un rechargement de la page confirme la persistance du changement.

**Acceptance Scenarios**:

1. **Given** une PME avec 5 étapes en attente, **When** elle coche la première sur le tableau de bord, **Then** l'étape est marquée terminée côté serveur et la carte affiche immédiatement la 4ᵉ étape à la place.
2. **Given** la même PME, **When** elle clique sur le titre de la carte "Plan d'action", **Then** elle accède à la page détaillée du plan d'action.

---

### User Story 3 — État vide intelligent pour primo-utilisateur (Priority: P1)

Une PME nouvellement inscrite n'a encore lancé aucun diagnostic. Au lieu d'afficher des "0" ou des cartes vides anxiogènes, chaque carte présente un message d'invitation et une action claire pour démarrer la première activité correspondante.

**Why this priority**: Les premières minutes déterminent l'adoption. Un dashboard vide décourage ; un dashboard guidant vers la première action convertit le visiteur en utilisateur actif.

**Independent Test**: Créer un compte PME sans aucune donnée, ouvrir le tableau de bord, vérifier qu'aucune carte n'affiche "0" sec ou "—", et que chaque carte propose un appel à l'action (par ex. "Lancez votre premier diagnostic ESG") cliquable menant à la fonctionnalité concernée.

**Acceptance Scenarios**:

1. **Given** une PME sans scoring antérieur, **When** elle ouvre le tableau de bord, **Then** la carte "Scores ESG" affiche un message d'invitation et un bouton "Lancer mon premier diagnostic" au lieu d'un score nul.
2. **Given** une PME sans candidature, **When** elle ouvre le tableau de bord, **Then** la carte "Candidatures" propose une action "Découvrir les financements" plutôt que "0 candidature".

---

### User Story 4 — Exporter ses données personnelles (Priority: P1)

Conformément aux droits RGPD/UEMOA, l'utilisatrice peut, depuis le tableau de bord, télécharger en un clic l'intégralité de ses données structurées dans un fichier portable.

**Why this priority**: Obligation légale (UEMOA 20/2010, RGPD article 20 — portabilité). Le tableau de bord est l'emplacement le plus naturel et visible pour cette commande, ce qui réduit le risque de plainte et le nombre de demandes manuelles au support.

**Independent Test**: Cliquer sur le bouton d'export en haut à droite du tableau de bord, vérifier qu'un fichier nommé `esg-mefali-export-AAAA-MM-JJ.json` est téléchargé et contient bien les données du compte connecté (et seulement ce compte).

**Acceptance Scenarios**:

1. **Given** une PME connectée, **When** elle clique sur "Exporter mes données", **Then** un fichier d'export structuré est téléchargé dans son navigateur en moins de 5 secondes pour un compte de taille standard.
2. **Given** la même PME, **When** elle ouvre le fichier exporté, **Then** elle y retrouve ses informations entreprise, projets, scorings, candidatures, étapes de plan d'action, et aucune donnée d'un autre compte.

---

### User Story 5 — Carte attestations vérifiables (Priority: P1)

Sur la carte "Rapports & attestations", l'utilisatrice voit ses dernières attestations actives avec leur QR code en miniature ; elle peut accéder à la version complète vérifiable publiquement.

**Why this priority**: Les attestations sont la sortie monétisable de la plateforme (preuve crédible vis-à-vis de bailleurs) ; les rendre visibles depuis l'accueil augmente leur usage et la perception de valeur.

**Independent Test**: Avec une PME possédant ≥2 attestations actives, vérifier que la carte affiche les 2 dernières avec QR mini, et que cliquer sur l'une d'elles ouvre la page de vérification publique correspondante.

**Acceptance Scenarios**:

1. **Given** une PME avec 3 attestations actives, **When** elle ouvre le tableau de bord, **Then** la carte "Rapports & attestations" liste les 3 derniers rapports PDF et les 2 attestations les plus récentes avec QR miniature.
2. **Given** la même PME, **When** elle clique sur une attestation, **Then** la page de vérification publique de cette attestation s'ouvre.

---

### User Story 6 — Affichage source pour chaque donnée ESG (Priority: P2)

À côté de chaque chiffre ESG affiché (score global, sous-scores, émissions), un indicateur cliquable permet de voir la source documentaire ayant servi au calcul.

**Why this priority**: Principe constitutionnel non-négociable de traçabilité (P1 Sourcing). En P2 car les utilisateurs PME pressés voient d'abord les chiffres ; les bailleurs et auditeurs ouvriront les sources, mais après le premier coup d'œil.

**Independent Test**: Sur une carte affichant un score ESG, vérifier la présence d'un badge cliquable "(source)" qui ouvre une vue listant les documents ayant alimenté ce calcul.

**Acceptance Scenarios**:

1. **Given** une PME avec scoring calculé à partir de 4 documents, **When** elle clique sur le badge source de la carte ESG, **Then** la liste des 4 documents apparaît avec leur titre et leur date.

---

### User Story 7 — Suggestions d'intermédiaires sur carte (Priority: P2)

Une carte secondaire affiche une mini-carte géographique avec quelques pins représentant des fonds ou banques recommandés selon le profil de la PME, cliquable vers la page de matching.

**Why this priority**: Engagement et découverte des opportunités, pas critique au premier load. Activée lorsque la PME a un profil et au moins un projet.

**Independent Test**: Avec une PME ayant un profil complet et un projet, vérifier la présence d'une carte affichant une carte géographique avec ≥3 pins et un lien vers la page de matching détaillée.

**Acceptance Scenarios**:

1. **Given** une PME avec profil complet et 1 projet déclaré, **When** elle ouvre le tableau de bord, **Then** la carte "Intermédiaires recommandés" affiche une carte géographique avec au moins 3 pins.

---

### User Story 8 — Rafraîchissement automatique des chiffres (Priority: P2)

Pendant que la PME garde le tableau de bord ouvert, les indicateurs se rafraîchissent automatiquement quand des calculs en arrière-plan se terminent (par exemple un nouveau scoring lancé depuis le chat).

**Why this priority**: Améliore l'expérience temps réel mais n'est pas indispensable au MVP — un rechargement manuel suffit en première approche.

**Independent Test**: Garder le tableau de bord ouvert dans un onglet, déclencher un nouveau calcul de scoring depuis un autre onglet, et vérifier que la carte ESG du premier onglet se met à jour seule en moins de 90 secondes.

**Acceptance Scenarios**:

1. **Given** une PME avec le tableau de bord ouvert, **When** un nouveau scoring se termine côté serveur, **Then** la carte ESG affiche la nouvelle valeur sans action manuelle de l'utilisatrice en moins de 90 secondes.

---

### Edge Cases

- **Compte vierge total** : aucune donnée, aucun projet, aucun document → toutes les cartes en mode "vide intelligent" avec CTA, jamais de "0" ou "—" sec.
- **Compte partiellement rempli** : par ex. scoring fait mais pas d'empreinte carbone → la carte concernée propose un CTA spécifique sans masquer les autres données existantes.
- **Données très volumineuses** (PME mature avec 50+ candidatures, 20+ rapports) : les cartes affichent uniquement les éléments les plus récents (3 candidatures, 3 rapports, 2 attestations) avec lien "voir tout".
- **Réseau lent ou intermittent** : chaque carte échoue indépendamment sans casser le reste du tableau de bord ; un message de réessai apparaît sur la carte concernée.
- **Action utilisateur perdue** : cocher une étape du plan d'action puis perdre la connexion → afficher un message d'erreur clair et permettre de réessayer sans avoir à recharger toute la page.
- **Affichage mobile** : les six cartes s'empilent verticalement, scroll fluide, aucune carte ne déborde horizontalement.
- **Compte multi-projets** : si la PME a plusieurs projets, les cartes agrègent (somme, dernière mise à jour) plutôt que d'en privilégier un implicitement.
- **Attestation expirée** : ne pas l'afficher dans la carte "actives" ; ne pas afficher d'attestation révoquée du tout.
- **Export demandé deux fois rapidement** : empêcher le double-clic de générer deux téléchargements ; bouton temporairement désactivé.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT afficher, après login PME, une page d'accueil unique présentant six cartes principales : scores ESG, empreinte carbone, score crédit, candidatures, rapports & attestations, plan d'action.
- **FR-002** : Le système DOIT afficher en haut de la page un bandeau d'accueil contenant la salutation, la raison sociale de la PME, la date du dernier diagnostic ESG, et un bouton proéminent menant à l'interface de chat conversationnel.
- **FR-003** : Chaque carte principale DOIT être cliquable et conduire à la page détaillée correspondante de la fonctionnalité.
- **FR-004** : La carte "Scores ESG" DOIT afficher le score global, une représentation visuelle compacte des trois axes E/S/G, et la date de la dernière mise à jour.
- **FR-005** : La carte "Empreinte carbone" DOIT afficher le total annuel d'émissions exprimé en tonnes équivalent CO₂ et une visualisation compacte de la tendance sur les quatre derniers trimestres.
- **FR-006** : La carte "Score crédit" DOIT afficher la valeur du score sur une échelle de 0 à 100 et un badge indiquant l'éligibilité aux principaux dispositifs de financement vert.
- **FR-007** : La carte "Candidatures" DOIT afficher des compteurs par statut (en cours, soumises, acceptées, refusées) et la liste des trois candidatures les plus récentes.
- **FR-008** : La carte "Rapports & attestations" DOIT afficher les trois derniers rapports PDF générés et les deux attestations actives les plus récentes avec QR code en miniature.
- **FR-009** : La carte "Plan d'action" DOIT afficher les trois prochaines étapes prioritaires et permettre de marquer une étape comme terminée directement depuis la carte.
- **FR-010** : Lorsqu'une étape est cochée depuis la carte, le système DOIT enregistrer la complétion côté serveur et rafraîchir la carte avec la prochaine étape en attente.
- **FR-011** : Le système DOIT afficher un état de chargement visuel (squelette) pour chaque carte pendant la récupération des données, sans jamais afficher d'écran blanc.
- **FR-012** : Pour toute carte dont les données sous-jacentes sont absentes, le système DOIT afficher un message d'invitation contextualisé et un appel à l'action menant à la fonctionnalité correspondante, jamais une valeur "0" ou "—" sec.
- **FR-013** : Le système DOIT proposer en haut à droite de la page un bouton "Exporter mes données" qui déclenche le téléchargement d'un fichier portable nommé selon le format `esg-mefali-export-AAAA-MM-JJ.<extension>` contenant uniquement les données du compte connecté.
- **FR-014** : Le système DOIT, en présence d'attestations actives, afficher leur QR miniature et conduire vers la page de vérification publique correspondante au clic.
- **FR-015** : Le système DOIT afficher, pour chaque chiffre ESG (scores, sous-scores, émissions), un indicateur cliquable permettant de consulter la liste des sources documentaires ayant servi au calcul.
- **FR-016** : Le système DOIT proposer une carte secondaire "Intermédiaires recommandés" affichant une carte géographique avec quelques pins lorsque la PME possède un profil complet et au moins un projet.
- **FR-017** : Le système DOIT, lorsqu'un calcul d'arrière-plan se termine, mettre à jour la carte concernée du tableau de bord ouvert sans intervention de l'utilisateur, dans un délai inférieur à 90 secondes.
- **FR-018** : Le système DOIT proposer, depuis le tableau de bord, un accès secondaire à l'historique des exports PDF déjà générés.
- **FR-019** : Le système DOIT garantir le cloisonnement des données : aucune carte ne DOIT afficher d'information appartenant à un autre compte que celui de l'utilisateur connecté.
- **FR-020** : En cas d'échec de chargement d'une carte, le système DOIT afficher un message d'erreur clair sur cette carte avec un bouton de réessai, sans casser l'affichage des autres cartes.
- **FR-021** : Le système DOIT empêcher le déclenchement simultané de deux exports par double-clic sur le bouton d'export.
- **FR-022** : Le tableau de bord DOIT être disponible dans la langue par défaut française pour tous les libellés, messages et invitations.

### Key Entities *(include if feature involves data)*

- **Tableau de bord (synthèse)** : agrégation lecture seule des données du compte connecté, comportant les indicateurs résumés de chaque domaine (scoring ESG, carbone, crédit, candidatures, rapports, attestations, plan d'action) et la date de dernière mise à jour pour chacun.
- **Carte de tableau de bord** : unité visuelle représentant un domaine ; chaque carte connaît son état (chargement, vide, rempli, en erreur), son contenu (chiffres, listes courtes, mini-visualisations) et sa destination de navigation détaillée.
- **Étape de plan d'action (vue carte)** : sous-ensemble cliquable des étapes prioritaires affichées sur le tableau de bord, avec libellé, priorité et état de complétion modifiable directement.
- **Attestation (vue carte)** : représentation compacte d'une attestation active, comportant identifiant public, date d'émission, QR miniature et lien vers la page de vérification publique.
- **Rapport (vue carte)** : représentation compacte d'un rapport PDF généré comportant titre, date, et lien de téléchargement.
- **Export de données** : fichier portable contenant l'ensemble des données du compte connecté, nommé selon une convention horodatée stable, généré à la demande.
- **Recommandation d'intermédiaire (vue carte)** : représentation compacte d'un fonds ou d'une banque recommandé pour la PME, comportant identifiant, type, position géographique approximative et lien vers la page de matching détaillée.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur écran de bureau standard, les six cartes principales du tableau de bord sont entièrement visibles sans défilement et lisibles dans leur état final en moins de 1,5 seconde après ouverture de la page pour 95 % des sessions.
- **SC-002** : Une utilisatrice naïve placée devant un tableau de bord pré-rempli peut citer correctement, en moins de 5 secondes, les quatre indicateurs principaux (score ESG global, total annuel d'émissions carbone, statut crédit, nombre de candidatures en cours) dans 90 % des tests utilisateurs.
- **SC-003** : Le taux de clics depuis le tableau de bord vers une page détaillée (scoring, carbone, plan d'action, candidatures, rapports) dépasse 60 % des sessions PME hebdomadaires.
- **SC-004** : Les PME nouvellement inscrites lancent leur premier diagnostic ESG dans les 7 jours suivant leur inscription dans 50 % des cas, en utilisant le CTA d'invitation présent sur la carte "Scores ESG" en mode vide.
- **SC-005** : Le délai entre le clic sur "Exporter mes données" et le début du téléchargement effectif est inférieur à 5 secondes pour 95 % des comptes de taille standard.
- **SC-006** : Le délai entre la complétion d'une étape de plan d'action depuis la carte et la confirmation visuelle (étape suivante affichée) est inférieur à 1 seconde dans 95 % des cas.
- **SC-007** : Aucune session utilisateur ne rapporte un affichage de "0" ou "—" sec à la place d'un appel à l'action sur les cartes des comptes vierges (vérifié sur 100 % des nouveaux comptes pendant la première semaine de mise en service).
- **SC-008** : Sur appareil mobile standard, le tableau de bord se charge et reste fluide (défilement perçu sans saccade) dans 95 % des sessions.
- **SC-009** : Le taux de fuite (sessions terminées dans les 10 secondes suivant l'ouverture du tableau de bord) reste inférieur à 10 % parmi les PME ayant déjà des données.
- **SC-010** : Lorsqu'une carte échoue à charger, l'utilisatrice peut continuer à interagir avec les cinq autres cartes dans 100 % des cas observés.

## Assumptions

- Les sources de données (scoring ESG, empreinte carbone, score crédit, candidatures, rapports, attestations, plan d'action) sont déjà disponibles via les fonctionnalités correspondantes ; le tableau de bord est purement consommateur, sans logique métier propre.
- La page d'accueil post-login est unique et identique pour toutes les PME ; la personnalisation par utilisateur (drag-reorder, masquage de cartes, widgets custom) est hors-scope MVP.
- Le rôle utilisateur ciblé est exclusivement la PME ; la vue administrateur dispose d'un tableau de bord séparé hors-scope de cette fonctionnalité.
- L'écran de bureau de référence pour la règle "six cartes above-the-fold" est une résolution standard 1366×768 ou supérieure ; en deçà, l'empilement et le défilement sont acceptés.
- Le bouton de chat IA depuis le bandeau renvoie vers une interface de chat existante ; aucune nouvelle expérience conversationnelle n'est créée par cette fonctionnalité.
- Les attestations ont une page publique de vérification déjà disponible ; le tableau de bord se contente de faire le lien.
- Les exports de données respectent les exigences de portabilité applicables (RGPD, UEMOA 20/2010) déjà couvertes par la fonctionnalité d'export back-end.
- L'ordre des cartes est fixe pour le MVP ; les retours utilisateurs ultérieurs pourront orienter une éventuelle personnalisation.
- Les cartes commentaires d'équipe et la vue multi-utilisateur sont hors-scope MVP.
- La carte "Intermédiaires recommandés" repose sur la fonctionnalité de matching existante ; à défaut de profil et de projet, elle est masquée plutôt qu'affichée vide.

## Dependencies

- Fonctionnalité **F32** (back-end dashboard) : endpoints de synthèse et d'export.
- Fonctionnalité **F36** (design tokens) et **F37** (UI primitives) : pour la cohérence visuelle des cartes.
- Fonctionnalité **F38** (app shell & navigation) : pour la navigation depuis et vers le tableau de bord.
- Fonctionnalité **F40** (bibliothèque de visualisation) : pour les mini-graphiques et la mini-carte géographique.
- Fonctionnalités cibles cliquables : **F47** scoring, **F48** carbone, **F49** crédit, **F46** plan d'action, **F51** rapports, **F52** attestations, **F53** matching.
- Fonctionnalité **F41** (couche conversationnelle) : pour le bouton "Discuter avec l'IA" du bandeau et, en option, pour le rafraîchissement temps réel.

## Out of Scope (MVP)

- Drag-and-drop pour réordonner les cartes.
- Widgets personnalisables ou cartes ajoutées par l'utilisateur.
- Carte commentaires d'équipe / collaboration multi-utilisateur.
- Vue administrateur dans le périmètre `/admin`.
- Personnalisation par utilisateur de la sélection des cartes affichées.
- Notifications push depuis le tableau de bord (gérées ailleurs).
