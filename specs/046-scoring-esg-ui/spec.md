# Feature Specification: Scoring ESG visualisations UI

**Feature Branch**: `046-scoring-esg-ui`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "F46 — Scoring ESG visualisations UI (UI de F23). Page `/scoring` permettant à la PME de consulter ses scores ESG par référentiel (BOAD, CDP, GRI, ODD, custom), comparer les référentiels, drilldown par pilier E/S/G et par indicateur, voir les sources, modifier les valeurs, recalculer, consulter l'historique et figer un snapshot."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vue d'ensemble du score ESG (Priority: P1)

En tant que dirigeant de PME, j'arrive sur `/scoring` et je vois immédiatement mon score ESG global, sa décomposition Environnement/Social/Gouvernance sous forme de radar, le taux de couverture des indicateurs renseignés, la date du dernier calcul et la version du référentiel utilisé. Chaque chiffre affiché est cliquable et m'amène à la (ou les) source(s) qui le justifient.

**Why this priority** : c'est la valeur principale que la PME attend du module Scoring. Sans cette vue, il n'y a pas de produit. La transparence sur les sources est aussi la clef de confiance imposée par la constitution (P1 Sourcing — toute assertion ESG/financière doit pointer vers une source vérifiée).

**Independent Test** : un compte PME avec un calcul de score existant ouvre `/scoring`, lit son score global et son radar E/S/G, clique sur un indicateur d'un pilier et voit une source vérifiée s'ouvrir.

**Acceptance Scenarios** :

1. **Given** une PME avec un calcul de score BOAD finalisé, **When** elle ouvre `/scoring`, **Then** elle voit le score global numérique, le radar E/S/G, le pourcentage de couverture, la date du dernier calcul et la version du référentiel.
2. **Given** la même page, **When** la PME clique sur la pastille « source » d'un pilier ou d'un indicateur, **Then** la source vérifiée associée s'affiche (titre, organisme, date, lien).
3. **Given** une PME sans aucun calcul de score, **When** elle ouvre `/scoring`, **Then** elle voit un état vide explicite avec un appel à l'action « Lancez votre premier diagnostic ».

---

### User Story 2 — Choix du référentiel et comparaison (Priority: P1)

En tant que dirigeant, je peux basculer entre plusieurs référentiels (BOAD par défaut, CDP, GRI, ODD-aligné, référentiel personnalisé si disponible) sans rechargement complet et comparer simultanément deux ou plusieurs référentiels côte à côte pour comprendre où ma PME se positionne selon chaque cadre.

**Why this priority** : la valeur différenciante du produit est la lecture multi-référentiels. Sans la bascule et la comparaison, l'utilisateur reste enfermé dans une seule grille.

**Independent Test** : sur `/scoring`, l'utilisateur change l'onglet « BOAD » → « CDP », l'URL se met à jour, le score s'adapte sans rechargement perçu, puis il clique sur « Comparer », sélectionne un second référentiel, et voit un graphique côte à côte.

**Acceptance Scenarios** :

1. **Given** la page `/scoring`, **When** la PME clique sur l'onglet « CDP », **Then** l'URL devient `/scoring/cdp`, les données du référentiel CDP s'affichent, et le passage perçu prend moins d'une demi-seconde une fois le référentiel chargé.
2. **Given** la page sur un référentiel donné, **When** la PME clique sur « Comparer » et sélectionne un second référentiel, **Then** un graphique en barres horizontales place les scores côte à côte par pilier.
3. **Given** un compte qui n'a pas calculé un référentiel, **When** elle ouvre l'onglet correspondant, **Then** un état vide propose de lancer le calcul pour ce référentiel.

---

### User Story 3 — Drilldown par pilier puis par indicateur (Priority: P1)

En tant que dirigeant, je veux dérouler chaque pilier (E, S, G) pour voir la liste des indicateurs, leur statut (renseigné / manquant), leur score individuel et leur source, puis ouvrir un panneau latéral détaillé pour un indicateur précis (définition, valeur, unité, formule, sources, historique 12 derniers points).

**Why this priority** : le drilldown est la mécanique de transparence et de pédagogie qui transforme un score en plan d'action.

**Independent Test** : depuis la vue d'ensemble, l'utilisateur déroule le pilier Environnement, voit l'indicateur « Émissions GES », clique dessus et voit le panneau détail avec l'historique sur 12 mois.

**Acceptance Scenarios** :

1. **Given** la page `/scoring`, **When** la PME déroule l'accordéon « Environnement », **Then** la liste des indicateurs du pilier s'affiche avec score, statut couvert/manquant, et pastille de source.
2. **Given** la liste des indicateurs, **When** la PME clique sur l'indicateur « Émissions GES », **Then** un panneau latéral droit s'ouvre avec le nom, la définition, la valeur courante, l'unité, la formule, les sources et un graphique linéaire des 12 derniers points historiques.
3. **Given** un pilier comportant plus de 30 indicateurs, **When** la PME le déroule, **Then** la liste reste fluide et navigable.

---

### User Story 4 — Modifier la valeur d'un indicateur depuis le drawer (Priority: P1)

En tant que dirigeant, depuis le panneau détail d'un indicateur, je peux cliquer sur « Modifier » pour saisir une nouvelle valeur via un bottom sheet dédié (saisie chiffrée), puis voir le score recalculé automatiquement.

**Why this priority** : la modification au sein du flux est la promesse de bidirectionnalité entre l'IA et l'utilisateur (P8 de la constitution). Sans cela, la transparence est une impasse.

**Independent Test** : ouvrir le drawer d'un indicateur, cliquer « Modifier », saisir une valeur dans le bottom sheet, valider, et constater que le score global et le radar se mettent à jour.

**Acceptance Scenarios** :

1. **Given** le drawer d'un indicateur ouvert, **When** la PME clique sur « Modifier », **Then** un bottom sheet de saisie chiffrée s'ouvre avec la valeur courante pré-remplie et l'unité affichée.
2. **Given** la saisie d'une nouvelle valeur valide, **When** la PME valide, **Then** la valeur est persistée, le score du référentiel courant est recalculé, et la vue d'ensemble (score global + radar + couverture) est mise à jour sans rechargement complet.
3. **Given** une saisie hors bornes ou de mauvais type, **When** la PME valide, **Then** un message d'erreur clair en français s'affiche dans le bottom sheet et la valeur précédente est conservée.

---

### User Story 5 — Indicateurs manquants et passage à l'action (Priority: P1)

En tant que dirigeant, je vois clairement la liste des indicateurs « à renseigner » qui empêchent un score complet, et je peux lancer une conversation guidée par l'IA pour les compléter, dans le contexte de l'indicateur cliqué.

**Why this priority** : c'est la passerelle entre la consultation et l'action. Elle évite que la PME reste face à un score sans savoir comment le faire progresser.

**Independent Test** : un compte PME avec couverture incomplète ouvre `/scoring`, voit la section « À renseigner », clique sur « Compléter » d'un indicateur manquant, et un chat contextualisé s'ouvre pour cet indicateur.

**Acceptance Scenarios** :

1. **Given** un référentiel avec des indicateurs non renseignés, **When** la PME ouvre `/scoring`, **Then** une section « À renseigner » liste ces indicateurs avec un appel à l'action « Compléter ».
2. **Given** la liste des manquants, **When** la PME clique « Compléter » sur un indicateur, **Then** le chat conversationnel s'ouvre avec le contexte de cet indicateur précis.
3. **Given** un référentiel avec couverture 100 %, **When** la PME ouvre la page, **Then** la section « À renseigner » est masquée.

---

### User Story 6 — Recalcul à la demande et synchronisation avec le chat (Priority: P1)

En tant que dirigeant, je peux déclencher un recalcul manuel du score pour le référentiel courant, voir un indicateur de progression, et obtenir le nouveau résultat. Par ailleurs, toute mise à jour d'un indicateur effectuée depuis le chat conversationnel met à jour la page `/scoring` ouverte sans nécessiter de rafraîchissement manuel.

**Why this priority** : recalcul et synchronisation garantissent que la page reflète toujours la vérité courante du dossier ESG, conformément à P8 (DB source de vérité, propagation IA → UI).

**Independent Test** : (a) cliquer sur « Recalculer », observer un spinner puis le nouveau score ; (b) ouvrir `/scoring`, modifier un indicateur depuis le chat dans un autre onglet, observer la page se rafraîchir.

**Acceptance Scenarios** :

1. **Given** la page chargée, **When** la PME clique « Recalculer », **Then** un indicateur de progression s'affiche, puis le nouveau score remplace l'ancien avec une nouvelle date de calcul.
2. **Given** la page ouverte, **When** un indicateur est mis à jour depuis le chat, **Then** la vue se rafraîchit automatiquement avec la nouvelle valeur et le score recalculé.
3. **Given** un échec de recalcul (par exemple aucune donnée), **When** le calcul échoue, **Then** un message clair en français explique le motif et propose de compléter les indicateurs manquants.

---

### User Story 7 — Historique des scores (Priority: P1)

En tant que dirigeant, je peux consulter un graphique d'historique sur les 12 derniers calculs du référentiel courant, et au survol je vois la date du calcul, la valeur et la version du référentiel utilisée à ce moment-là.

**Why this priority** : l'historique apporte une lecture progrès / régression indispensable au pilotage. La traçabilité de la version du référentiel est exigée par la constitution (P4 Versioning).

**Independent Test** : sur un référentiel avec au moins 2 calculs historiques, vérifier que le graphique affiche les points et que le survol révèle date/valeur/version.

**Acceptance Scenarios** :

1. **Given** un référentiel avec plusieurs calculs, **When** la PME ouvre `/scoring`, **Then** un graphique linéaire affiche les 12 derniers points.
2. **Given** ce graphique, **When** la PME survole un point, **Then** la date, la valeur et la version du référentiel s'affichent.
3. **Given** un référentiel avec un seul calcul, **When** la PME ouvre la page, **Then** le graphique l'affiche sans erreur.

---

### User Story 8 — Snapshot intangible d'un calcul (Priority: P1)

En tant que dirigeant, je peux activer un mode « snapshot » pour figer la vue sur une version donnée du référentiel et un calcul donné, en lecture seule, afin d'archiver, partager ou auditer un état précis.

**Why this priority** : la reproductibilité à 5 ans imposée par la constitution (P4) et l'usage d'attestation/audit côté finance verte rendent ce mode essentiel.

**Independent Test** : activer le toggle « Voir snapshot », vérifier que les actions de mutation (modifier, recalculer) sont désactivées et que la version du référentiel affichée est figée.

**Acceptance Scenarios** :

1. **Given** la page `/scoring`, **When** la PME active le mode snapshot et choisit un calcul historique, **Then** la vue se fige sur cet état (scores, indicateurs, sources, version du référentiel) et le marque visuellement comme « snapshot ».
2. **Given** le mode snapshot actif, **When** la PME tente d'utiliser « Modifier » ou « Recalculer », **Then** ces actions sont désactivées avec un libellé explicatif.
3. **Given** le mode snapshot, **When** la PME le désactive, **Then** la vue revient à l'état courant en temps réel.

---

### User Story 9 — Exporter un rapport scoring (Priority: P2)

En tant que dirigeant, je peux exporter le résultat de scoring courant (ou un snapshot) sous forme de rapport PDF.

**Why this priority** : utile mais pas bloquant pour la consultation ; couvert par la fonctionnalité Rapports (F51) et donc déléguable.

**Independent Test** : cliquer sur « Exporter PDF », recevoir un fichier PDF téléchargeable contenant la vue d'ensemble du scoring, les piliers et les sources.

**Acceptance Scenarios** :

1. **Given** la page `/scoring` chargée, **When** la PME clique « Exporter PDF », **Then** un rapport PDF est généré et proposé au téléchargement.
2. **Given** un mode snapshot actif, **When** la PME exporte, **Then** le PDF reflète l'état figé y compris la version du référentiel et la date du calcul.

---

### Edge Cases

- Une **source associée à un indicateur a été révoquée** : l'indicateur reste affiché, mais sa pastille de source est marquée d'un avertissement et la valeur est visuellement grisée pour signaler qu'elle ne peut plus être utilisée comme preuve.
- Un **référentiel possède plus de 6 piliers/axes** que le radar ne peut pas afficher lisiblement : la vue d'ensemble bascule automatiquement sur un graphique en barres verticales.
- Un **pilier contient plus de 30 indicateurs** : la liste reste fluide (virtualisation/chargement progressif côté UI).
- L'utilisateur **modifie une valeur pendant qu'un recalcul est en cours** : la modification est mise en file d'attente jusqu'à la fin du calcul puis déclenche un recalcul ultérieur.
- L'utilisateur **passe en mode snapshot puis tente de se rendre dans le chat conversationnel pour modifier une valeur** : le chat se signale en lecture seule pour les indicateurs ESG concernés ou redirige vers la sortie du mode snapshot.
- Un **référentiel personnalisé** existe sans calcul : son onglet est visible mais propose un état vide « Lancez le diagnostic ».
- Le **calcul est déclenché sans aucune valeur d'indicateur** : un message clair indique qu'au moins un indicateur doit être renseigné, sans laisser la PME face à un échec opaque.
- L'utilisateur **navigue directement à `/scoring/<code>` pour un référentiel inconnu** : la page affiche un message d'erreur clair et propose de revenir à la liste des référentiels disponibles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : La page `/scoring` MUST afficher, pour le référentiel courant, le score global numérique, la décomposition E/S/G sous forme de radar (ou barres verticales si > 6 axes), le taux de couverture des indicateurs et la date du dernier calcul.
- **FR-002** : Chaque score affiché (global, par pilier, par indicateur) MUST exposer une référence cliquable à au moins une source vérifiée ; un indicateur sans source vérifiée doit être visuellement signalé.
- **FR-003** : La page MUST permettre de basculer entre référentiels via un sélecteur (BOAD par défaut, CDP, GRI, ODD-aligné, référentiel personnalisé si disponible) et l'URL MUST refléter le référentiel courant (`/scoring/<code>`).
- **FR-004** : La page MUST permettre de comparer simultanément le score du référentiel courant avec un ou plusieurs autres référentiels via un graphique en barres horizontales côte à côte par pilier.
- **FR-005** : La page MUST proposer un drilldown par pilier (accordéon E/S/G) listant les indicateurs avec score, statut (renseigné/manquant) et source.
- **FR-006** : Le clic sur un indicateur MUST ouvrir un panneau latéral détaillé (slide-in droite) contenant nom, définition, valeur courante, unité, formule, sources et historique des 12 derniers points.
- **FR-007** : Le panneau détail MUST proposer un bouton « Modifier » qui ouvre un bottom sheet de saisie chiffrée avec validation (type, bornes, unité) ; toute saisie invalide MUST afficher une erreur explicite en français.
- **FR-008** : Une modification valide d'un indicateur MUST persister la valeur, déclencher un recalcul du score du référentiel courant et propager la mise à jour à la vue d'ensemble sans rechargement complet.
- **FR-009** : La page MUST afficher une section « À renseigner » listant les indicateurs manquants avec un appel à l'action « Compléter » ouvrant le chat conversationnel pré-contextualisé sur cet indicateur.
- **FR-010** : La page MUST exposer un bouton « Recalculer » déclenchant le recalcul du score du référentiel courant, avec indicateur de progression et affichage du nouveau résultat. Les échecs MUST produire un message d'erreur explicite en français.
- **FR-011** : La page MUST afficher un graphique linéaire des 12 derniers calculs du référentiel courant, avec révélation au survol de la date, de la valeur et de la version du référentiel utilisée à ce moment.
- **FR-012** : La page MUST proposer un mode snapshot, activable via un toggle, qui fige la vue sur une version donnée d'un calcul historique, désactive toutes les actions de mutation (Modifier, Recalculer), et signale visuellement l'état figé.
- **FR-013** : La page MUST proposer un bouton d'export PDF du scoring courant ou du snapshot actif.
- **FR-014** : La page MUST écouter les évènements de mise à jour d'indicateur ou de recalcul de score émis par d'autres surfaces (chat conversationnel notamment) et rafraîchir sa vue automatiquement.
- **FR-015** : La page MUST afficher un état vide explicite et un appel à l'action de premier diagnostic lorsqu'aucun calcul n'existe pour le compte / le référentiel courant.
- **FR-016** : Toutes les valeurs monétaires éventuellement présentes dans la page (objectifs, seuils, indicateurs financiers) MUST être affichées avec leur devise (ISO 4217) et la conversion FCFA-EUR MUST utiliser le pivot fixe 655,957 lorsque pertinent.
- **FR-017** : La page MUST signaler visuellement (badge d'avertissement + valeur grisée) tout indicateur dont la source associée a été révoquée.
- **FR-018** : La page MUST être servie en français par défaut, les libellés, messages d'erreur et exports PDF étant rédigés en français.
- **FR-019** : Toute action visible sur la page (ouverture, changement de référentiel, ouverture de drawer, modification, recalcul, export, activation snapshot) MUST être tracée par le journal d'audit immuable du back-office (entité, champ, valeur ancienne/nouvelle, source de changement).

### Key Entities

- **Score ESG** : résultat d'un calcul pour un référentiel donné, à une date donnée, dans une version donnée du référentiel ; comporte un score global, un score par pilier (E/S/G), un taux de couverture et une référence aux indicateurs utilisés.
- **Référentiel** : grille d'évaluation (BOAD, CDP, GRI, ODD-aligné, custom) versionnée, avec date de validité ; jamais écrasée, conserve son historique.
- **Indicateur** : unité atomique de donnée ESG ayant une valeur, une unité, une définition, une formule potentielle et une ou plusieurs sources ; indépendant de tout pilier (vue E/S/G dérivée).
- **Source** : preuve vérifiée associée à une valeur d'indicateur (titre, organisme, date, lien) ; possède un statut « vérifié » ou « révoqué ».
- **Snapshot de scoring** : capture immuable d'un score à un instant T, incluant la version du référentiel et l'identité des indicateurs et sources utilisés.
- **Évènement de synchronisation** : message diffusé entre surfaces (chat ↔ page scoring) signalant qu'un indicateur ou un calcul a changé.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME ouvrant la page voit son score global, son radar E/S/G et la date du dernier calcul en moins de 2 secondes après le chargement initial pour un compte typique (50+ indicateurs).
- **SC-002** : Le passage d'un référentiel à un autre (changement d'onglet) est perçu comme instantané, c'est-à-dire en moins de 200 ms lorsque les données du référentiel cible sont déjà en cache local.
- **SC-003** : 100 % des scores affichés (global, par pilier, par indicateur) exposent une source cliquable lorsqu'une source vérifiée existe ; les autres sont visuellement signalés comme dépourvus de source vérifiée.
- **SC-004** : Une modification d'indicateur effectuée depuis le drawer entraîne un score global et un radar mis à jour visibles à l'écran sans action manuelle de rafraîchissement.
- **SC-005** : Une comparaison entre deux référentiels est obtenue en moins de 3 clics depuis l'arrivée sur la page.
- **SC-006** : Une PME ayant un score à couverture incomplète peut, depuis la page, identifier au moins un indicateur manquant et lancer la conversation IA pour le compléter en moins de 2 clics.
- **SC-007** : Le mode snapshot empêche, à 100 % des tentatives, toute mutation (modification, recalcul) sur la vue figée.
- **SC-008** : Le drilldown d'un pilier comportant 30+ indicateurs reste navigable sans saccade perceptible (60 fps en interaction continue sur un appareil de référence).
- **SC-009** : 100 % des actions visibles sur la page (changement de référentiel, ouverture de drawer, modification, recalcul, export, activation snapshot) produisent une trace d'audit consultable côté back-office.
- **SC-010** : 100 % des libellés, messages d'erreur, infobulles et exports PDF sont en français.

## Assumptions

- Le **backend de scoring (F23)** expose déjà la lecture des scores par référentiel, le détail des indicateurs, l'historique de calculs, le déclenchement de recalcul et l'identification des indicateurs manquants, conformément aux dépendances annoncées.
- Le **catalogue des référentiels et indicateurs (F09)** est en place et fournit les définitions, formules, unités et versions des indicateurs.
- Le **chat conversationnel (F41)** et son **bus d'évènements** sont disponibles et peuvent être ouverts avec un contexte d'indicateur prédéfini et émettre des évènements de mise à jour.
- Le **moteur de bottom sheet (F39)** prend en charge un type de saisie chiffrée (`ask_number`) avec validation (bornes, unité, type).
- La **viz library (F40)** fournit les primitives de radar, barres horizontales/verticales, ligne et la pastille « source » réutilisable.
- L'**export PDF (F51)** existe (ou existera avant la livraison) et expose une API d'export du scoring courant ou d'un snapshot.
- Le **module d'audit (épine dorsale du back-office)** trace toute mutation et permet de consulter les évènements liés au scoring.
- Le mode `BOAD` est le **référentiel par défaut** lorsque l'utilisateur n'a fait aucun choix explicite.
- L'**utilisateur est authentifié** en tant que rôle PME ; la séparation multi-tenant (RLS sur `account_id`) garantit qu'il ne voit que ses propres scores.
- Les **valeurs des indicateurs** lues et écrites par cette page sont stockées une seule fois (pivot Indicateur unique, P6) ; la page n'introduit aucune duplication par axe E/S/G.
- L'**hébergement et le traitement** restent localisés en Europe ou Afrique de l'Ouest, conformément aux contraintes RGPD/UEMOA/loi ivoirienne 2013-450.

## Dependencies

- F23 — Scoring ESG multi-référentiels (backend)
- F09 — Catalogue référentiels & indicateurs
- F36 — Design System tokens
- F37 — UI primitives
- F38 — App shell & navigation
- F39 — Bottom sheet engine (saisie `ask_number`)
- F40 — Viz library (radar, bars, line, source pin)
- F41 — Chat conversational layer (event bus, ouverture contextuelle)
- F51 — Export PDF (rapport scoring)

## Out of Scope (MVP)

- Édition des pondérations du référentiel (réservée à l'admin / F09).
- Suggestions IA inline directement sur la page de scoring (couvertes par le plan d'action F45).
- Comparaison vs benchmark sectoriel.
- Heatmap d'indicateurs.
- Référentiels personnalisés créés par la PME elle-même (post-MVP).
- Langues locales (Wolof, Bambara, ...) — post-MVP.
