# Feature Specification: Credit scoring UI (F48)

**Feature Branch**: `048-credit-scoring-ui`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "F48 — UI de F29 credit scoring : page `/credit-score` avec gauge 0-100, sous-scores, badges éligibilité (BOAD-vert, SUNREF, Ecobank Green Lending), recommandations actionnables, saisie data financière en bottom sheet, recalcul animé et historique."

## Clarifications

### Session 2026-05-04

- Q: Comment sélectionner les 3-5 recommandations affichées sur `/credit-score` parmi celles du plan d'action ? → A: Tri par impact estimé sur le score crédit décroissant, filtré sur les sous-scores les plus faibles (top 3-5).
- Q: Quels sont les seuils de classification du score crédit ? → A: Insuffisant 0-39, À améliorer 40-59, Bon 60-79, Excellent 80-100 (bornes inférieures inclusives).
- Q: Le catalogue des dispositifs d'éligibilité est-il figé ou dynamique ? → A: Liste dynamique fournie par le backend (référentiel versionné) ; BOAD-vert, SUNREF et Ecobank Green Lending constituent le minimum MVP garanti.
- Q: Que se passe-t-il quand les données financières sont partielles ? → A: Calcul partiel — dès que les 4 montants financiers (CA, EBE, dette, fonds propres) sont saisis, le score est calculé avec un bandeau « Couverture partielle » ; les sous-scores ESG/Gouvernance manquants restent en « non calculé ».
- Q: Quelle granularité pour la raison de non-éligibilité ? → A: Raison principale (critère le plus impactant) sur le badge + liste exhaustive de tous les critères non satisfaits dans la fiche détaillée au clic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vue synthèse score crédit (Priority: P1)

En tant que dirigeant·e de PME, j'arrive sur `/credit-score` et je découvre immédiatement mon score de crédit ESG sur une gauge 0-100, accompagné d'une classification qualitative (Excellent / Bon / À améliorer / Insuffisant) et de l'évolution par rapport à l'année précédente, afin de comprendre en un coup d'œil ma solvabilité perçue par les banques de finance verte.

**Why this priority**: La gauge centrale est le cœur de la page : sans elle, l'utilisateur ne peut pas situer son entreprise. C'est l'écran « hero » qui détermine la lisibilité de toute la fonctionnalité.

**Independent Test**: Avec un score crédit existant (ex. 72), ouvrir `/credit-score` et vérifier que la gauge affiche 72, la classification « Bon » et un delta « +X points vs N-1 ». Si aucun score n'existe, l'écran bascule sur l'empty state (US8).

**Acceptance Scenarios**:

1. **Given** un score crédit calculé à 72 et un score N-1 à 64, **When** la PME accède à `/credit-score`, **Then** la gauge affiche « 72 / 100 », la classification « Bon » et un KPI « +8 points vs N-1 ».
2. **Given** un score crédit à 38, **When** la page se charge, **Then** la classification « Insuffisant » s'affiche avec un code couleur distinct (et un libellé textuel explicite pour l'accessibilité, pas uniquement la couleur).
3. **Given** une baisse de 5 points par rapport à N-1, **When** le KPI delta se rend, **Then** il indique « −5 points » avec un indicateur visuel et textuel de variation négative.

---

### User Story 2 — Décomposition en sous-scores (Priority: P1)

En tant que PME, je veux comprendre **comment** mon score global est composé, en visualisant quatre sous-scores : Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance — chacun sous forme de carte avec valeur numérique et barre de progression — afin d'identifier les leviers d'amélioration.

**Why this priority**: Sans décomposition, le score global est opaque. La pédagogie sur les composantes est indispensable pour que la PME passe à l'action.

**Independent Test**: Avec un score crédit calculé, vérifier que quatre cartes apparaissent, chacune affichant un sous-score (0-100) et une barre proportionnelle. Le total pondéré doit être cohérent avec le score global affiché en US1.

**Acceptance Scenarios**:

1. **Given** un score global de 72 décomposé en {Solidité 70, Opérationnelle 80, ESG 65, Gouvernance 75}, **When** l'utilisateur consulte la décomposition, **Then** les quatre cartes s'affichent avec ces valeurs et leurs barres respectives.
2. **Given** un sous-score manquant (donnée non fournie), **When** la carte se rend, **Then** elle affiche un état « non calculé » avec un appel à l'action « Compléter mes données ».

---

### User Story 3 — Badges d'éligibilité aux financements verts (Priority: P1)

En tant que PME, je veux voir immédiatement à quels financements verts je suis éligible (BOAD-vert, SUNREF, Ecobank Green Lending) avec des badges proéminents, et pouvoir cliquer sur chaque badge pour ouvrir une fiche détaillant les conditions et le lien vers le matching d'offres correspondant.

**Why this priority**: L'éligibilité est la promesse business de la fonctionnalité — c'est ce qui transforme un score en opportunité concrète de financement.

**Independent Test**: Avec un profil éligible à BOAD-vert et SUNREF mais pas à Ecobank Green Lending, vérifier que deux badges « éligible » et un badge « non éligible » (ou masqué) sont affichés, et qu'un clic sur BOAD-vert ouvre une fiche avec les conditions.

**Acceptance Scenarios**:

1. **Given** un score de 72 et un profil éligible BOAD-vert, **When** l'utilisateur clique sur le badge BOAD-vert, **Then** une fiche s'ouvre avec les conditions d'éligibilité, les seuils requis et un bouton « Voir les offres compatibles » menant au matching.
2. **Given** une PME non éligible à un dispositif, **When** la liste des badges se rend, **Then** le dispositif est marqué « non éligible » avec **uniquement la raison principale** (critère le plus impactant, ex. « Score < 60 requis ») et non simplement masqué ; le détail exhaustif des critères non satisfaits n'est révélé qu'au clic dans la fiche.

---

### User Story 4 — Recommandations actionnables priorisées (Priority: P1)

En tant que PME, je veux recevoir 3 à 5 recommandations concrètes et priorisées pour améliorer mon score (ex. « Réduire la dette court terme », « Documenter votre politique RSE »), chacune annotée d'un impact estimé en points, et je veux pouvoir cliquer pour basculer vers l'étape correspondante de mon plan d'action.

**Why this priority**: Sans actions, la PME reste passive. Les recommandations transforment le diagnostic en feuille de route.

**Independent Test**: Avec un score décomposé identifiant deux faiblesses (ex. dette élevée, gouvernance faible), vérifier qu'au moins 3 recommandations s'affichent avec un impact estimé « +X points » et qu'un clic redirige vers `/plan-action#step-{id}`.

**Acceptance Scenarios**:

1. **Given** un sous-score Gouvernance faible (45/100), **When** les recommandations se rendent, **Then** au moins une recommandation traite la gouvernance avec un impact estimé clair (ex. « +6 points »).
2. **Given** une recommandation cliquée, **When** la navigation se déclenche, **Then** l'utilisateur arrive sur l'étape correspondante du plan d'action.
3. **Given** l'affichage d'un impact estimé, **When** le libellé est rendu, **Then** la mention « estimation » est visible pour éviter toute promesse ferme.

---

### User Story 5 — Saisie de la donnée financière (Priority: P1)

En tant que PME, je veux saisir ou mettre à jour mes données financières (chiffre d'affaires, EBE, dette, fonds propres) via un formulaire conversationnel multi-étapes affiché en **bottom sheet** (jamais inline), avec montants typés et devise explicite, afin de déclencher un nouveau calcul de score.

**Why this priority**: Sans entrée de données, pas de score. La saisie est la porte d'entrée du calcul ; le format bottom sheet est imposé par la constitution P10.

**Independent Test**: Cliquer sur « Mettre à jour mes données financières » ouvre un bottom sheet en plusieurs étapes ; chaque montant est saisi avec sa devise ; à la soumission, le bottom sheet se ferme et un recalcul est déclenché (US6).

**Acceptance Scenarios**:

1. **Given** un utilisateur cliquant sur l'action « Mettre à jour mes données financières », **When** le bottom sheet s'ouvre, **Then** le formulaire propose les étapes CA, EBE, dette, fonds propres avec le montant et la devise.
2. **Given** un montant saisi sans devise, **When** l'utilisateur tente de valider l'étape, **Then** une erreur claire empêche la soumission tant que la devise n'est pas choisie.
3. **Given** un montant aberrant ou non numérique, **When** la validation s'exécute, **Then** un message d'erreur explicite s'affiche sans perdre les saisies des autres champs.

---

### User Story 6 — Recalcul automatique avec animation (Priority: P1)

En tant que PME, après avoir soumis de nouvelles données financières, je veux que le score soit immédiatement recalculé et que la gauge passe de l'ancienne valeur à la nouvelle de manière animée et fluide, accompagnée d'une confirmation indiquant le delta (« +8 points »).

**Why this priority**: L'animation crée une boucle de feedback gratifiante qui motive la PME à compléter ses données. Sans recalcul immédiat, l'expérience est cassée.

**Independent Test**: Soumettre de nouvelles données financières → la gauge anime sa transition vers la nouvelle valeur, un toast de confirmation indique le delta de points, et tous les sous-scores et badges sont rafraîchis.

**Acceptance Scenarios**:

1. **Given** un score initial de 64, **When** la PME soumet des données qui font passer le score à 72, **Then** la gauge anime fluidement de 64 vers 72 et un toast « +8 points » s'affiche.
2. **Given** un recalcul ramenant le score à une valeur inférieure, **When** la gauge s'anime, **Then** elle redescend visuellement et le delta négatif est clairement indiqué.
3. **Given** un échec serveur lors du recalcul, **When** la requête échoue, **Then** un message d'erreur s'affiche sans corrompre l'état de la gauge (la valeur précédente reste visible).

---

### User Story 7 — Historique des scores (Priority: P1)

En tant que PME, je veux visualiser l'évolution de mon score sur les 6 derniers calculs sous forme de graphique linéaire, afin de constater les progrès dans le temps.

**Why this priority**: La perception du progrès est un puissant moteur d'engagement. L'historique relie chaque action à un résultat mesurable.

**Independent Test**: Avec au moins 2 calculs historiques disponibles, vérifier qu'un graphique linéaire affiche les points dans l'ordre chronologique avec leurs dates.

**Acceptance Scenarios**:

1. **Given** 6 calculs historiques, **When** le graphique se rend, **Then** les 6 points sont affichés avec leur date et leur valeur.
2. **Given** un seul calcul (premier), **When** le graphique se rend, **Then** un état adapté est affiché (point unique avec message « Premier calcul ») plutôt qu'un graphique vide.

---

### User Story 8 — Empty state pédagogique (Priority: P1)

En tant que PME n'ayant jamais calculé de score crédit, je veux qu'à mon arrivée sur `/credit-score`, un wizard pédagogique en 4 étapes (CA, dette, ESG, gouvernance) m'explique ce qu'est le score et me guide pour le calculer pour la première fois.

**Why this priority**: L'empty state évite l'écran vide ; il convertit l'arrivée en action de calcul. Sans lui, la PME repart sans valeur.

**Independent Test**: Pour un compte sans aucun score, vérifier que `/credit-score` affiche le wizard 4 étapes au lieu de la gauge, et qu'à la fin du wizard un premier score est calculé.

**Acceptance Scenarios**:

1. **Given** un compte sans aucun score crédit antérieur, **When** la PME ouvre `/credit-score`, **Then** le wizard 4 étapes s'affiche avec une explication initiale.
2. **Given** un wizard complété, **When** la dernière étape est soumise, **Then** le premier score est calculé et la PME bascule sur la vue synthèse (US1).

---

### User Story 9 — Synchronisation avec le chat conversationnel (Priority: P1)

En tant que PME interagissant avec l'assistant IA, lorsque le chat enregistre une mise à jour de mes données crédit ou recalcule mon score, la page `/credit-score` doit se rafraîchir automatiquement sans rechargement manuel.

**Why this priority**: La cohérence bidirectionnelle entre le chat et l'UI est imposée par la constitution P8. Sans cela, la PME voit des données obsolètes après une interaction chat.

**Independent Test**: Ouvrir `/credit-score`, déclencher depuis le chat une mise à jour de credit_data ou un recalcul, vérifier que la gauge, les sous-scores et les badges se mettent à jour sans action de l'utilisateur.

**Acceptance Scenarios**:

1. **Given** la page ouverte et un événement chat « entity_updated{credit_data} », **When** l'événement est reçu, **Then** la page rafraîchit ses données affichées.
2. **Given** un événement « entity_updated{credit_score} », **When** il est reçu, **Then** la gauge anime sa transition vers la nouvelle valeur comme dans US6.

---

### User Story 10 — Export du rapport crédit (Priority: P2)

En tant que PME, je veux pouvoir exporter mon score crédit, ses sous-scores et les recommandations sous forme de rapport partageable.

**Why this priority**: Utile pour partager avec un partenaire bancaire, mais non critique au MVP — le partage formel passe par les attestations vérifiables (P7).

**Independent Test**: Cliquer sur « Exporter » génère un rapport téléchargeable contenant les éléments principaux de la page.

**Acceptance Scenarios**:

1. **Given** un score calculé, **When** l'utilisateur déclenche l'export, **Then** un rapport contenant gauge, sous-scores, badges et recommandations est produit.

---

### Edge Cases

- Score juste à la limite d'un seuil de classification (ex. 60 entre « À améliorer » et « Bon ») : la borne inférieure est inclusive — un score de 60 est classé « Bon », un score de 59 reste « À améliorer ».
- Profil partiellement éligible (ex. score OK mais secteur exclu) : le badge doit clairement indiquer la raison spécifique du refus.
- Recommandation cliquée renvoyant vers une étape de plan d'action qui n'existe plus : redirection vers la racine du plan d'action plutôt qu'une 404.
- Devises mixtes dans les saisies financières : conversion via taux peg FCFA-EUR fixe et `fx_rate` USD du jour ; jamais de calcul approximatif sur des `float`.
- Recalcul lancé en parallèle (ex. depuis chat ET depuis bottom sheet) : le système doit traiter le résultat le plus récent et éviter les flickerings de gauge.
- Utilisateur daltonien : la classification (Excellent/Bon/À améliorer/Insuffisant) doit être identifiable par le texte seul, pas uniquement la couleur.
- Recalcul échouant côté serveur : la gauge ne doit jamais être laissée dans un état intermédiaire incohérent.
- Wizard d'empty state interrompu en cours : reprise possible à l'étape en cours sans perte des saisies déjà validées.
- Données partielles : la PME a saisi les 4 montants financiers mais pas les volets ESG/Gouvernance — le score s'affiche avec un bandeau « Couverture partielle » et les badges d'éligibilité dont les règles dépendent d'un sous-score absent doivent indiquer « éligibilité incomplète » plutôt que « non éligible ».

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : La page `/credit-score` MUST afficher une gauge 0-100 avec la valeur actuelle du score, une classification textuelle parmi {Excellent, Bon, À améliorer, Insuffisant}, et un KPI delta vs N-1. Les seuils de classification sont : Insuffisant `0-39`, À améliorer `40-59`, Bon `60-79`, Excellent `80-100`. Les bornes inférieures sont inclusives (un score de 60 est classé « Bon », un score de 80 est classé « Excellent »).
- **FR-002** : La page MUST afficher quatre cartes de sous-scores (Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance), chacune avec valeur numérique et barre de progression.
- **FR-003** : La page MUST afficher des badges d'éligibilité pour l'ensemble des dispositifs fournis dynamiquement par le backend (référentiel versionné), avec un état explicite (éligible / non éligible avec raison). Le MVP garantit a minima la présence de BOAD-vert, SUNREF et Ecobank Green Lending. L'ordre d'affichage est défini par le référentiel.
- **FR-004** : Chaque badge d'éligibilité MUST être cliquable et ouvrir une fiche détaillant les conditions et un lien vers le matching d'offres correspondant. Pour un dispositif non éligible, la fiche MUST lister de façon exhaustive **tous** les critères non satisfaits, tandis que le badge lui-même n'affiche que la **raison principale** (critère le plus impactant) pour rester lisible.
- **FR-005** : La page MUST afficher 3 à 5 recommandations actionnables priorisées issues du plan d'action, avec un impact estimé en points clairement libellé comme estimation. La sélection se fait en filtrant d'abord les actions rattachées aux sous-scores les plus faibles (US2), puis en triant ces actions par impact estimé sur le score crédit décroissant et en conservant les 3 à 5 premières.
- **FR-006** : Chaque recommandation MUST être cliquable et rediriger vers l'étape correspondante du plan d'action (`/plan-action#step-{id}`).
- **FR-007** : Le système MUST proposer une saisie multi-étapes des données financières (CA, EBE, dette, fonds propres) en bottom sheet conformément à la règle UX P10 — jamais inline dans une bulle de chat.
- **FR-008** : Tout montant saisi MUST être typé `{amount, currency}` ; le système ne doit jamais utiliser de représentation flottante imprécise pour de la monnaie (P5).
- **FR-009** : À la soumission de nouvelles données financières, le score MUST être recalculé automatiquement et la gauge MUST animer sa transition de l'ancienne valeur vers la nouvelle.
- **FR-010** : Après recalcul, le système MUST afficher une confirmation avec le delta de points obtenu.
- **FR-011** : La page MUST afficher un graphique linéaire de l'historique des 6 derniers calculs avec leurs dates.
- **FR-012** : Lorsque aucun score n'existe pour le compte, la page MUST afficher un wizard pédagogique 4 étapes (CA, dette, ESG, gouvernance) à la place de la gauge.
- **FR-012a** : Le score global MUST être calculable dès que les 4 montants financiers (CA, EBE, dette, fonds propres) sont fournis, même si les données ESG ou Gouvernance sont manquantes. Dans ce cas, la page MUST afficher un bandeau « Couverture partielle » au-dessus de la gauge, et les sous-scores manquants MUST rester dans l'état « non calculé » défini en US2 AS2 avec un appel à l'action « Compléter mes données ».
- **FR-013** : La page MUST écouter les événements de synchronisation chat (`entity_updated{credit_data,credit_score}`) et rafraîchir son contenu sans rechargement manuel (P8).
- **FR-014** : Toute modification manuelle d'un champ écrit par le LLM MUST invalider immédiatement le contexte LLM correspondant (P8) ; la base de données reste source de vérité.
- **FR-015** : Le rendu de la gauge et des badges MUST rester accessible aux utilisateurs daltoniens en combinant texte et couleur.
- **FR-016** : Toute donnée affichée issue d'un référentiel ou d'un calcul ESG MUST être traçable à une source vérifiée (P1) ; les sources sont consultables via l'UI.
- **FR-017** : L'interface MUST être en français par défaut, avec orthographe et accentuation correctes.
- **FR-018** : L'export de rapport (US10, P2) MUST produire un document contenant gauge, sous-scores, badges et recommandations, et MUST inclure une annexe « Sources et références » conformément à P1.
- **FR-019** : Toutes les actions impactant la donnée crédit (saisie, recalcul) MUST être enregistrées en audit append-only avec `{user_id, account_id, ts, entity, field, old, new, source_of_change}` (P3).

### Key Entities *(include if feature involves data)*

- **CreditScore** : score global crédit ESG d'un compte PME, avec valeur numérique 0-100, classification, date de calcul, version de référentiel utilisée et lien vers les sous-scores.
- **CreditSubScore** : composante du score (Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance), valeur numérique et pondération.
- **CreditData** : entrée financière de la PME (CA, EBE, dette, fonds propres) typée en monnaie `{amount, currency}` (P5), versionnée et auditée.
- **EligibilityBadge** : indicateur d'éligibilité à un dispositif de financement vert (BOAD-vert, SUNREF, Ecobank Green Lending), avec statut, raison du refus le cas échéant, conditions détaillées et lien vers les offres compatibles.
- **CreditRecommendation** : action priorisée issue du plan d'action, avec libellé, impact estimé en points, lien vers l'étape du plan correspondante.
- **CreditScoreHistoryEntry** : enregistrement historique d'un calcul (date, valeur, version de référentiel) pour l'évolution temporelle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Avec un score crédit calculé à 72, la PME voit la gauge à 72/100 et la classification « Bon » dans les premiers instants suivant l'ouverture de la page (chargement perçu inférieur à 1,5 seconde).
- **SC-002** : Une PME qui met à jour son chiffre d'affaires depuis le bottom sheet voit son score recalculé et la gauge animée sans avoir à rafraîchir manuellement la page.
- **SC-003** : Au moins 80 % des PME interagissant avec la page peuvent identifier en moins de 30 secondes leur principal levier d'amélioration via les sous-scores et les recommandations.
- **SC-004** : Un clic sur le badge BOAD-vert ouvre la fiche détaillée des conditions et propose un chemin vers les offres compatibles en moins de 2 interactions.
- **SC-005** : Une recommandation cliquée amène la PME directement sur l'étape concernée du plan d'action sans rechargement complet de l'application.
- **SC-006** : Le wizard d'empty state permet à une PME de calculer son premier score en moins de 3 minutes sur mobile.
- **SC-007** : L'animation de la gauge reste fluide et perçue comme telle par 95 % des utilisateurs sur mobile et desktop.
- **SC-008** : Aucun montant affiché ou recalculé ne présente de perte de précision visible due à un arrondi de représentation.
- **SC-009** : Une mise à jour de données crédit déclenchée depuis le chat se reflète sur la page ouverte sans intervention manuelle de l'utilisateur.
- **SC-010** : 100 % des informations ESG affichées sont consultables via leur source dans l'UI.

## Assumptions

- Le backend F29 (`credit_data`, `credit_score`) expose déjà les endpoints permettant la lecture, la mise à jour des données financières et le recalcul du score, conformément aux dépendances annoncées.
- Le score crédit consomme un référentiel versionné ; chaque calcul est rattaché à une version pour reproductibilité (P4).
- Les badges d'éligibilité reposent sur des règles déjà modélisées côté backend dans un référentiel versionné ; l'UI itère sur la liste reçue et ne code en dur aucun dispositif.
- Le matching d'offres correspondant aux badges est livré par une autre feature (référencée comme F53) — l'UI se contente du lien sortant.
- Les recommandations sont fournies par le plan d'action (F45) ; l'UI ne calcule pas l'impact estimé, elle l'affiche tel que reçu.
- Les rendus monétaires utilisent un composant numérique commun déjà disponible en design system (F37) avec support de la précision décimale et des devises ISO 4217.
- L'historique des scores conserve au minimum les 6 derniers calculs ; les calculs plus anciens sont accessibles ailleurs (post-MVP).
- Les utilisateurs cibles sont des dirigeants ou responsables financiers de PME ouest-africaines, avec accès mobile prioritaire.
- L'export PDF (US10) est livré par une feature distincte (F51) ; cette spec définit uniquement le déclenchement et le contenu attendu.
- Hors-scope MVP : benchmark sectoriel, simulateur « Si X alors Y » (couvert F55), notation Bâle III détaillée.
- L'interface respecte la palette et les composants du design system livrés par F36/F37/F38.
