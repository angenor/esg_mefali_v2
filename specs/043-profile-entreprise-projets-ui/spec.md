# Feature Specification: Profil Entreprise & Projets — UI

**Feature Branch**: `043-profile-entreprise-projets-ui`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F43 — Profile Entreprise & Projets UI (UI de F11 + F12-profile)"

## Clarifications

### Session 2026-05-03

- Q: Liste fermée des statuts projet ? → A: `brouillon`, `actif`, `en_candidature`, `finance`, `cloture`, `abandonne` (6 valeurs)
- Q: Tranches de couleur du badge score ESG (échelle 0–100) ? → A: Vert ≥ 75, Orange 50–74, Rouge < 50
- Q: Documents projet — formats et taille max ? → A: PDF, JPG, PNG, DOCX, XLSX — 25 Mo max par fichier
- Q: Options du dialogue de résolution de conflit chat ↔ utilisateur ? → A: 3 choix — Garder ma valeur, Garder la valeur du chat, Annuler
- Q: Granularité de la localisation projet ? → A: Pays (ISO2) + région/commune en texte libre + latitude/longitude optionnelles

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Consulter et compléter le profil entreprise (Priority: P1)

Une dirigeante de PME ouvre `/profil/entreprise` et voit son profil organisé en sections (Identité, Taille, Localisation, Gouvernance, Pratiques). Elle clique sur une section, modifie un champ, et le système enregistre automatiquement après une courte pause de saisie. Un indicateur de complétion en haut de page lui montre sa progression.

**Why this priority**: Le profil entreprise est la fondation de tout le parcours ESG : sans lui, ni le scoring (F23), ni le matching (F25), ni les dossiers (F26) ne fonctionnent. C'est le premier point de contact après l'onboarding.

**Independent Test**: Connecter un compte PME vierge → ouvrir `/profil/entreprise` → vérifier l'affichage des sections vides → renseigner la raison sociale → confirmer que la valeur est persistée (refresh page) et que la barre de complétion progresse.

**Acceptance Scenarios**:

1. **Given** une PME connectée sans profil rempli, **When** elle ouvre `/profil/entreprise`, **Then** les 5 sections (Identité, Taille, Localisation, Gouvernance, Pratiques) s'affichent en mode lecture avec un état vide explicite et un taux de complétion à 0 %.
2. **Given** une section ouverte en édition, **When** la dirigeante saisit la raison sociale et arrête de taper, **Then** la valeur est persistée silencieusement après 800 ms et un feedback discret « Enregistré il y a 2 s » apparaît.
3. **Given** un champ obligatoire renseigné, **When** la valeur est sauvegardée côté serveur, **Then** le pourcentage de complétion en haut de page est mis à jour automatiquement.
4. **Given** une saisie en cours, **When** la dirigeante recharge la page sans avoir attendu le toast de confirmation, **Then** la dernière valeur saisie après pause est présente (zéro perte de données).

---

### User Story 2 — Saisir des montants typés et zones géographiques fiables (Priority: P1)

La dirigeante doit pouvoir renseigner un chiffre d'affaires en XOF, EUR ou USD et déclarer ses pays d'opération via une liste ISO normalisée plutôt qu'en texte libre.

**Why this priority**: La précision financière (P5 monnaie typée) et la normalisation géographique sont des invariants constitutionnels : un montant float ou un pays en texte libre casserait le scoring, le matching et la conformité réglementaire (UEMOA).

**Independent Test**: Saisir « 50 000 000 » avec devise XOF → vérifier l'affichage formaté (50 000 000 FCFA) → changer pour EUR → vérifier la conversion live au taux fixe 655,957 → consulter la base : valeur stockée en décimal sans perte.

**Acceptance Scenarios**:

1. **Given** un champ de chiffre d'affaires, **When** la dirigeante saisit un montant et sélectionne XOF, **Then** la valeur est affichée et stockée comme décimal avec sa devise sans recourir à un nombre flottant.
2. **Given** un champ multi-pays d'opération, **When** la dirigeante ouvre le sélecteur, **Then** les pays d'Afrique de l'Ouest apparaissent en tête de liste, avec recherche par nom, et seuls des codes ISO 2 lettres sont acceptés.
3. **Given** une devise initialement en XOF, **When** la dirigeante bascule vers EUR, **Then** le montant équivalent est affiché en temps réel selon le taux fixe XOF↔EUR 655,957 (avec source citée), sans modifier la valeur originale stockée.

---

### User Story 3 — Gérer la liste des projets et créer un nouveau projet (Priority: P1)

La dirigeante ouvre `/profil/projets`, voit ses projets sous forme de cartes (nom, statut, secteur, date dernière maj, badge score ESG coloré). Elle clique sur « Nouveau projet » et est guidée par un assistant en 4 étapes pour créer son projet principal.

**Why this priority**: Le projet est l'objet central du financement vert. Sans projet créé, la PME ne peut accéder ni au matching d'offres, ni aux dossiers de candidature, ni au plan d'action.

**Independent Test**: Compte PME sans projet → ouvrir `/profil/projets` → vérifier l'état vide avec illustration et CTA → cliquer « Nouveau projet » → compléter les 4 étapes → vérifier l'apparition immédiate de la carte projet.

**Acceptance Scenarios**:

1. **Given** une PME sans projet, **When** elle ouvre `/profil/projets`, **Then** un état vide explicite s'affiche avec illustration et bouton « Créez votre premier projet ».
2. **Given** l'assistant de création projet ouvert, **When** la dirigeante remplit nom + description, secteur + type d'impact (E/S/G), localisation, budget + horizon, **Then** chaque étape valide les contraintes (champs requis, formats) avant de permettre l'étape suivante.
3. **Given** la création terminée, **When** la confirmation est envoyée, **Then** la liste de projets affiche immédiatement la nouvelle carte sans rechargement complet.
4. **Given** une carte projet, **When** la dirigeante clique dessus, **Then** elle accède à la page détail (Identité, Description, Localisation, Budget typé, Documents, Score ESG).

---

### User Story 4 — Cohabitation chat ↔ formulaire sans perte (Priority: P1)

Pendant que la dirigeante édite manuellement son profil, le chat IA peut aussi écrire dans les mêmes champs (via tools). Les deux flux doivent rester cohérents : modification manuelle → contexte LLM invalidé ; mutation chat → page rafraîchie en direct.

**Why this priority**: La synchronisation bidirectionnelle (P8) est un invariant constitutionnel. Une divergence chat/formulaire entraînerait un scoring sur des données fausses, donc une perte de confiance et un risque réglementaire.

**Independent Test**: Ouvrir `/profil/entreprise` dans un onglet → ouvrir le chat dans un autre onglet → demander au chat « mets le CA à 75 M XOF » → vérifier que la page profil reflète la valeur en moins de 2 s avec un flash discret « Mis à jour par le chat ».

**Acceptance Scenarios**:

1. **Given** une page profil ouverte, **When** le chat exécute une mutation sur un champ, **Then** la section concernée est rechargée et un feedback visuel discret « Mis à jour par le chat » apparaît.
2. **Given** une dirigeante en train de modifier un champ et le chat qui pousse une valeur concurrente, **When** les deux modifications portent sur le même champ, **Then** un dialogue de résolution propose une prévisualisation des deux versions et demande laquelle conserver.
3. **Given** une modification manuelle confirmée, **When** la dirigeante repose une question au chat, **Then** le chat utilise les valeurs à jour de la base (le contexte précédent a été invalidé).

---

### User Story 5 — Documents et suppression réversible des projets (Priority: P1)

La dirigeante peut joindre des documents (justificatifs, plan d'affaires) à un projet via un téléversement avec aperçu, et supprimer un projet de façon réversible (soft delete) avec confirmation.

**Why this priority**: Les documents alimentent le scoring et la génération de dossiers (F22, F26). La suppression réversible évite la perte accidentelle d'un projet en cours de candidature.

**Independent Test**: Ouvrir un projet → téléverser un PDF → vérifier l'aperçu miniature → supprimer le projet → confirmer la disparition de la liste active → vérifier que le projet reste récupérable pendant 30 jours.

**Acceptance Scenarios**:

1. **Given** la page détail d'un projet, **When** la dirigeante téléverse un document, **Then** un aperçu miniature apparaît dans la liste des documents projet.
2. **Given** un projet existant, **When** la dirigeante clique « Supprimer » et confirme dans la boîte de dialogue, **Then** le projet disparaît de la liste active mais reste récupérable pendant 30 jours.

---

### User Story 6 — Visibilité de l'historique d'une section (Priority: P2)

La dirigeante peut consulter l'historique des modifications d'une section (qui a changé quoi et quand, source : utilisateur ou chat) via un panneau latéral.

**Why this priority**: Renforce la confiance et la traçabilité (P3 audit append-only). Non bloquant pour l'usage quotidien mais indispensable pour les audits et conflits.

**Independent Test**: Modifier la raison sociale → ouvrir « Historique » sur la section Identité → vérifier la présence de l'entrée avec auteur, horodatage et ancienne/nouvelle valeur.

**Acceptance Scenarios**:

1. **Given** une section avec plusieurs modifications passées, **When** la dirigeante ouvre « Historique », **Then** un panneau latéral liste les changements en ordre antichronologique avec champ, ancienne valeur, nouvelle valeur, auteur et horodatage.

---

### Edge Cases

- **Réseau intermittent** : si l'autosave échoue, une bannière persistante « Modifications non sauvegardées » s'affiche avec retry automatique exponentiel ; aucune perte tant que l'utilisateur garde la page ouverte.
- **Conflit d'édition simultanée** : modification locale non sauvegardée + push backend (chat ou autre onglet) → dialogue de résolution avec aperçu des deux versions.
- **Saisie rapide multi-champs** : enchaînement de modifications dans plusieurs champs avant la fin du délai d'autosave → chaque champ déclenche son propre cycle, aucune ne doit écraser une autre.
- **Devise non disponible côté FX** : si la conversion live échoue (ex. USD indisponible), affichage du dernier taux connu avec horodatage et mention « taux du jj/mm/aaaa ».
- **Pays absent de la liste ISO** : la saisie libre est rejetée avec message d'erreur clair invitant à choisir dans la liste.
- **Pas de connectivité au chargement initial** : la page affiche un état dégradé avec bouton « Réessayer » plutôt qu'un écran blanc.
- **Wizard projet interrompu** : si la dirigeante quitte le wizard avant la fin, la progression est perdue (pas de brouillon en MVP) — confirmation explicite avant fermeture.
- **Fichier téléversé non supporté** : message d'erreur clair avec liste des formats acceptés.
- **Suppression d'un projet déjà supprimé** : action idempotente sans erreur visible.

## Requirements *(mandatory)*

### Functional Requirements

#### Profil entreprise

- **FR-001**: La page `/profil/entreprise` MUST afficher le profil sous forme de 5 sections logiques : Identité, Taille (CA, effectifs), Localisation, Gouvernance, Pratiques.
- **FR-002**: Chaque section MUST proposer un mode lecture par défaut et basculer en édition sur clic, avec retour automatique au mode lecture après sauvegarde.
- **FR-003**: Les modifications MUST être persistées en autosave silencieux après une pause de saisie de 800 ms, avec annulation automatique des sauvegardes en cours si une nouvelle modification arrive avant la fin du délai.
- **FR-004**: Le système MUST afficher un feedback de sauvegarde discret après chaque persistance réussie (ex. « Enregistré il y a 2 s »).
- **FR-005**: En cas d'échec réseau, le système MUST afficher une bannière persistante « Modifications non sauvegardées » avec tentative de retry automatique, sans bloquer la saisie.
- **FR-006**: Une barre de complétion globale MUST être affichée en haut de la page, calculée côté serveur, avec une infobulle listant les champs manquants.
- **FR-007**: Les champs monétaires MUST utiliser un composant typé exigeant un montant décimal et un sélecteur de devise (XOF, EUR, USD) ; aucune représentation flottante ne doit être utilisée côté client.
- **FR-008**: Le sélecteur de devise MUST proposer une conversion d'affichage en temps réel sur la base d'un taux référencé (XOF↔EUR fixe à 655,957 ; USD via taux du jour sourcé), sans modifier la valeur stockée d'origine.
- **FR-009**: Le sélecteur multi-pays MUST n'accepter que des codes ISO 3166-1 alpha-2, proposer une recherche par nom, et présenter les pays d'Afrique de l'Ouest (UEMOA) en tête de liste.
- **FR-010**: Tous les champs MUST être accessibles au clavier avec un ordre de tabulation cohérent et les erreurs MUST être annoncées via une association explicite description/erreur conforme aux pratiques d'accessibilité (WCAG 2.1 AA).

#### Projets

- **FR-011**: La page `/profil/projets` MUST lister les projets sous forme de cartes affichant : nom, statut, secteur, date de dernière mise à jour, badge de score ESG coloré. Les valeurs possibles du statut persisté sont les 5 statuts canoniques du backend F12-profile : `brouillon`, `en_recherche_financement`, `finance`, `en_execution`, `cloture` (la clarification initiale a été retraitée en research R2 : `actif` n'est pas persisté, `en_candidature` est un sous-badge dérivé affiché lorsqu'au moins une candidature `submitted` est associée, `abandonne` est exprimé via la suppression réversible — voir FR-016). Le badge de score ESG (échelle 0–100) MUST utiliser les paliers de couleur suivants : vert pour score ≥ 75, orange pour 50 ≤ score < 75, rouge pour score < 50.
- **FR-012**: Un état vide MUST s'afficher quand la PME n'a aucun projet, avec illustration et bouton d'appel à l'action « Créez votre premier projet ».
- **FR-013**: La création d'un projet MUST se faire via un assistant modal en 4 étapes : (1) nom + description, (2) secteur + type d'impact E/S/G, (3) localisation (pays au format ISO 3166-1 alpha-2 obligatoire, région/commune en texte libre obligatoire, latitude et longitude optionnelles), (4) budget typé + horizon temporel.
- **FR-014**: Chaque étape de l'assistant MUST valider ses champs avant d'autoriser la progression et MUST permettre le retour à l'étape précédente sans perdre la saisie en cours.
- **FR-015**: La page détail `/profil/projets/[id]` MUST afficher : Identité, Description, Localisation, Budget typé, Documents associés, lien vers le score ESG du projet.
- **FR-016**: La suppression d'un projet MUST exiger une confirmation explicite et MUST être réversible pendant 30 jours (soft delete).
- **FR-017**: La section Documents d'un projet MUST permettre le téléversement avec aperçu miniature et MUST référencer les documents stockés via le service documents existant. Les formats acceptés sont : PDF, JPG, PNG, DOCX, XLSX, avec une taille maximale de 25 Mo par fichier ; tout fichier hors de ces critères MUST être rejeté côté UI avec un message d'erreur explicite listant les formats autorisés et la limite de taille.

#### Synchronisation chat ↔ profil

- **FR-018**: Toute mutation provoquée par le chat IA sur un champ du profil MUST être propagée à la page ouverte en moins de 2 secondes via un mécanisme de bus d'évènements, accompagnée d'un feedback visuel discret.
- **FR-019**: Toute modification manuelle d'un champ MUST invalider immédiatement le contexte LLM associé afin que la prochaine question chat utilise les valeurs persistées.
- **FR-020**: Lorsqu'une modification locale non sauvegardée et une mutation chat portent sur le même champ, le système MUST afficher un dialogue de résolution présentant les deux valeurs et MUST proposer exactement trois choix : « Garder ma valeur » (la valeur locale est persistée), « Garder la valeur du chat » (la valeur poussée par le chat est persistée), « Annuler » (aucun changement n'est appliqué et la valeur d'origine est restaurée). Aucune des deux valeurs ne MUST être appliquée automatiquement.
- **FR-021**: La détection de conflit MUST s'appuyer sur un identifiant de version (concurrence optimiste) fourni par le service profil/projets ; un identifiant inférieur à celui en cours déclenche le dialogue de résolution.

#### Historique et audit

- **FR-022**: Chaque section MUST proposer un accès « Historique » qui ouvre un panneau latéral listant les modifications passées (champ, ancienne valeur, nouvelle valeur, auteur, horodatage, source utilisateur ou chat) en ordre antichronologique.

### Key Entities

- **Profil entreprise** : agrégat des données structurées de la PME (identité juridique, taille, localisation, gouvernance, pratiques) ; rattaché à un seul compte ; expose un identifiant de version pour la concurrence optimiste.
- **Projet** : objet central porté par la PME (identité, description, secteur, type d'impact E/S/G, localisation {pays ISO2 obligatoire, région/commune libre obligatoire, latitude/longitude optionnelles}, budget typé, horizon, statut canonique ∈ {`brouillon`, `en_recherche_financement`, `finance`, `en_execution`, `cloture`} avec sous-badge dérivé « Candidature en cours » lorsque applicable, score ESG, documents) ; supprimable de manière réversible (deleted_at) ; rattaché au compte de la PME.
- **Document projet** : fichier joint à un projet (nom, type MIME, taille, miniature, date d'ajout) ; géré par le service documents.
- **Section de profil** : regroupement logique de champs (Identité, Taille, Localisation, Gouvernance, Pratiques) servant à structurer l'UI et le calcul de complétion.
- **Évènement de mutation** : signal applicatif propagé entre le chat et l'UI pour synchroniser les valeurs en temps réel.
- **Entrée d'audit** : trace immuable d'un changement (qui, quand, quoi, source) consultable par section.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La page `/profil/entreprise` est entièrement utilisable (données affichées, sections cliquables) en moins de 1 seconde après navigation pour une PME de taille moyenne.
- **SC-002**: 100 % des modifications saisies par l'utilisateur sont persistées sans perte, y compris en cas de rechargement immédiat de la page après la pause d'autosave.
- **SC-003**: Une mutation déclenchée depuis le chat se reflète sur la page profil ouverte en moins de 2 secondes dans 95 % des cas.
- **SC-004**: Une PME peut compléter de 30 % à 80 % la barre de complétion de son profil entreprise en remplissant 5 champs ou moins.
- **SC-005**: La création d'un nouveau projet via l'assistant en 4 étapes peut être réalisée par une dirigeante en moins de 3 minutes.
- **SC-006**: Aucune valeur monétaire saisie n'est altérée par une arithmétique flottante : la valeur stockée et la valeur ré-affichée sont strictement identiques (à la décimale près de la devise).
- **SC-007**: Aucun pays renseigné dans l'application n'est en texte libre — 100 % des entrées sont des codes ISO valides.
- **SC-008**: En cas de modification simultanée chat ↔ utilisateur sur le même champ, 100 % des conflits sont signalés à l'utilisateur (zéro écrasement silencieux).
- **SC-009**: Un projet supprimé reste récupérable pendant 30 jours dans 100 % des cas.
- **SC-010**: La couverture de tests automatisés des écrans Profil entreprise et Projets atteint au moins 80 %.

## Assumptions

- Les services backend pour le profil entreprise (F11) et les projets (F12-profile) exposent déjà : récupération, mise à jour partielle, suppression, calcul de complétion, gestion des conflits par version, et journal d'audit.
- Le bus d'évènements chat ↔ UI (issu de F41) et l'écosystème documents (F22) sont disponibles et stables.
- Le design system (F36, F37, F38, F39) fournit les primitives UI requises (formulaire, sélecteurs, modale, panneau latéral, toasts, cartes).
- En MVP, une PME gère un seul projet « principal » à la fois ; la gestion multi-projets simultanés actifs est reportée en P2.
- Le comparateur de projets, l'éditeur de texte riche et le réordonnancement par glisser-déposer sont hors scope MVP.
- Les langues locales (Wolof, Bambara, …) ne sont pas couvertes ; l'interface est en français par défaut.
- Le taux fixe XOF↔EUR à 655,957 est sourcé conformément à l'invariant P5 ; le taux USD est obtenu via une source quotidienne référencée côté backend.
- La suppression réversible des projets s'aligne sur la rétention soft-delete de 30 jours déjà appliquée par le backend.
- L'accessibilité cible WCAG 2.1 niveau AA pour les écrans concernés.
