# Feature Specification: F51 — Matching offres + Wizard candidature + Simulateur (UI de F25/F26/F27)

**Feature Branch**: `051-matching-candidatures-simulateur-ui`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "F51 — UI des modules 5.0 matching, 5.1 candidatures et 5.3 simulateur. Trois pages métier liées par le parcours 'trouver un financement vert' : `/matching` (cards + filtres + comparateur + carte), `/candidatures` (wizard 5 étapes + suivi statut) et `/simulateur` (sliders + charts temps réel). Consommation intensive de `<ChatBottomSheet>` (F39) et `<Viz*>` (F40). Dépend de F25/F26/F27 backend, F36, F37, F38, F39, F40."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Découvrir les offres compatibles via `/matching` (Priority: P1)

Une PME ouvre `/matching` après avoir complété son profil et son projet. Elle voit immédiatement une liste d'offres de financement vert ordonnées par compatibilité avec son projet. Elle peut filtrer par type, montant, durée, intermédiaire, secteur, ouvrir le détail d'une offre, et lancer la préparation d'une candidature en un clic.

**Why this priority**: C'est le point d'entrée du parcours "trouver un financement". Sans cette page, les modules candidature et simulateur ne sont pas découvrables. Délivre la promesse de valeur centrale (matching automatique projet ↔ offre vert).

**Independent Test**: Avec un compte PME ayant un projet ESG renseigné et un catalogue de ≥10 offres seed, ouvrir `/matching`, vérifier que les cards s'affichent ordonnées par score de compatibilité, appliquer un filtre "subvention + < 100k EUR", obtenir la sous-liste filtrée, ouvrir le détail d'une offre, cliquer "Préparer ma candidature" → redirection vers le wizard pré-rempli.

**Acceptance Scenarios**:

1. **Given** la PME a un projet renseigné et le catalogue contient ≥10 offres, **When** elle ouvre `/matching`, **Then** la page liste les offres triées par compatibilité décroissante avec nom de l'intermédiaire, montant, type et durée visibles sur chaque card.
2. **Given** la PME est sur `/matching`, **When** elle applique les filtres `type=subvention` et `montant_max=100k EUR`, **Then** la liste se réduit aux offres correspondantes et l'URL persiste les filtres pour partage/recharge.
3. **Given** la PME ouvre le drawer détail d'une offre, **When** elle clique "Préparer ma candidature", **Then** elle est redirigée vers `/candidatures/new?offre_id=...` avec l'offre pré-sélectionnée.
4. **Given** la PME a coché "Ajouter au comparateur" sur 2 ou 3 offres, **When** elle clique "Comparer", **Then** elle accède à `/matching/compare` qui affiche un tableau side-by-side des conditions, durées, montants, documents requis.
5. **Given** la PME visualise la carte Leaflet, **When** elle clique sur un pin d'intermédiaire, **Then** les cards correspondantes sont mises en évidence dans la liste.

---

### User Story 2 — Constituer et soumettre une candidature via le wizard (Priority: P1)

Une PME, après avoir choisi une offre depuis `/matching`, suit un wizard 5 étapes pour générer un dossier de candidature complet : choix offre + projet, snapshot des données entreprise, dépôt des documents requis, réponses libres assistées par chat, récapitulatif et soumission. Elle peut sauvegarder un brouillon à tout moment et reprendre plus tard. La soumission crée un snapshot intangible (P4 constitution) reproductible 5 ans.

**Why this priority**: C'est la finalité opérationnelle de la plateforme — sans soumission, le matching n'a pas de débouché. La rigueur du snapshot intangible est une exigence constitutionnelle (P4) et juridique (preuve à 5 ans).

**Independent Test**: Démarrer un wizard depuis une offre choisie, parcourir les 5 étapes, fermer le navigateur à mi-parcours, rouvrir → reprendre exactement où on s'est arrêté, compléter, soumettre → confirmation visible avec ID candidature, statut "soumise", documents joints recensés, snapshot non modifiable.

**Acceptance Scenarios**:

1. **Given** la PME accède à `/candidatures/new?offre_id=X`, **When** elle parcourt les 5 étapes (offre+projet → snapshot data PME read-only → documents requis → réponses libres chat → récapitulatif), **Then** chaque étape se valide indépendamment et la progression (% complétion) est visible en permanence.
2. **Given** la PME a complété 3 étapes sur 5, **When** elle ferme le navigateur puis rouvre `/candidatures`, **Then** la candidature en cours apparaît avec statut "brouillon" et un bouton "Reprendre" la repositionne sur l'étape interrompue avec toutes ses saisies préservées.
3. **Given** la checklist documents requise n'est pas complète, **When** la PME tente de passer à l'étape suivante, **Then** un bandeau indique les documents manquants avec un lien direct vers l'upload (F50).
4. **Given** la PME est à l'étape récapitulatif, **When** elle clique "Soumettre", **Then** une modale de confirmation apparaît avec un avertissement explicite "Snapshot intangible — non modifiable après envoi" et une checkbox obligatoire avant validation finale.
5. **Given** la candidature est soumise, **When** la PME revient sur le détail, **Then** elle voit la timeline des transitions de statut, les éventuels commentaires de l'intermédiaire, et tous les champs sont en lecture seule.
6. **Given** la PME est dans l'étape "réponses libres", **When** elle pose une question via le chat F41 contextuel, **Then** le chat répond en se référant au contexte projet+offre+entreprise et toute saisie interactive (radios, checkboxes, sliders) apparaît dans un bottom sheet (P10) jamais en bulle.

---

### User Story 3 — Simuler un financement et basculer vers le matching (Priority: P1)

Une PME ouvre `/simulateur` pour explorer "qu'est-ce que je peux financer ?". Elle ajuste des sliders (montant, durée, type d'investissement, part de subvention) et voit en temps réel les mensualités, le coût total, l'économie estimée et l'impact CO2 évité, sous forme de charts. Elle peut sauvegarder une simulation et basculer vers `/matching` pré-filtré pour trouver des offres compatibles avec ses paramètres.

**Why this priority**: Outil pédagogique et de qualification clé — beaucoup de PME ne savent pas combien elles peuvent financer ni le coût réel d'un investissement vert. Le simulateur convertit les utilisateurs hésitants vers le matching réel.

**Independent Test**: Ouvrir `/simulateur`, déplacer le slider "montant" de 50k à 500k, observer que mensualités, coût total et CO2 évité se mettent à jour de manière fluide (perception < 200 ms), cliquer "Trouver des offres compatibles" → redirection vers `/matching?montant=X&duree=Y` avec filtres pré-appliqués.

**Acceptance Scenarios**:

1. **Given** la PME ouvre `/simulateur`, **When** elle ajuste un slider (montant, durée, type, part subvention), **Then** les sorties (mensualités, coût total, économie estimée, CO2 évité) se recalculent et les charts (barres mensualités, ligne cumul intérêts, camembert décomposition) se mettent à jour avec une perception < 200 ms.
2. **Given** la PME a configuré une simulation intéressante, **When** elle clique "Sauvegarder cette simulation", **Then** la simulation apparaît dans `/simulateur/historique` réutilisable plus tard.
3. **Given** la PME visualise un résultat de simulation, **When** elle clique "Trouver des offres compatibles", **Then** elle est redirigée vers `/matching?montant=X&duree=Y` avec les filtres correspondants déjà appliqués et l'URL partageable.
4. **Given** un calcul de simulation est en cours, **When** la PME modifie un slider rapidement plusieurs fois, **Then** les requêtes sont debounced (un seul calcul effectif final) et l'UI ne flicker pas.

---

### User Story 4 — Suivre l'évolution de ses candidatures (Priority: P1)

Une PME ouvre `/candidatures` pour voir la liste de toutes ses candidatures (en cours, brouillons, soumises, en revue, acceptées, refusées) avec leur progression. Elle peut filtrer par statut, ouvrir le détail, voir la timeline des changements de statut et les commentaires reçus.

**Why this priority**: Sans suivi, la PME perd le fil de ses candidatures multi-offres. Le dashboard candidatures ferme la boucle du parcours.

**Independent Test**: Avec un compte ayant ≥3 candidatures dans des statuts différents, ouvrir `/candidatures`, vérifier que la table affiche nom offre, statut, date maj, % complétion, ouvrir une candidature en revue → voir la timeline avec commentaire intermédiaire affiché.

**Acceptance Scenarios**:

1. **Given** la PME a ≥3 candidatures de statuts variés (brouillon, soumise, en revue), **When** elle ouvre `/candidatures`, **Then** une table liste chaque candidature avec nom de l'offre, statut (parmi les 5 valeurs), date de dernière mise à jour, et % de complétion.
2. **Given** la PME clique sur une candidature, **When** la page détail s'ouvre, **Then** elle voit la timeline des transitions de statut et les commentaires de l'intermédiaire (s'il y en a).
3. **Given** une candidature est en statut "documents manquants", **When** la PME ouvre son détail, **Then** un bandeau l'invite à compléter via l'upload (F50).

---

### Edge Cases

- **Carte Leaflet sans données géolocalisées** : empty state explicite "Aucun intermédiaire dans cette zone" et la liste reste utilisable.
- **Comparateur > 3 offres** : l'utilisateur est bloqué avec un message clair "Maximum 3 offres comparables" plutôt qu'une dégradation silencieuse.
- **Reload navigateur en plein wizard** : autosave doit garantir aucune perte de données ; un brouillon vide ne doit pas créer d'entrée fantôme.
- **Soumission accidentelle** : la double confirmation (modale + checkbox) doit empêcher tout envoi non intentionnel.
- **Catalogue d'offres vide** : `/matching` affiche un empty state pédagogique avec un CTA "Découvrez le simulateur" plutôt qu'une page vide.
- **Calcul simulateur erroné** : un message d'erreur lisible apparaît, les anciens résultats restent affichés (pas de flash blanc).
- **Filtres sans résultat** : message "Aucune offre ne correspond" + bouton "Réinitialiser les filtres".
- **Snapshot data PME modifié pendant un wizard ouvert** : à la soumission, le snapshot finalise les données affichées dans le wizard, pas l'état mutable temps réel ; un avertissement signale tout écart si l'utilisateur a modifié son profil pendant le wizard.
- **Reprise d'un brouillon dont l'offre a été retirée du catalogue** : la candidature passe en statut "offre indisponible" avec instructions claires et option d'archivage.
- **Réseau lent / hors-ligne** : autosave bufferise localement et synchronise au retour réseau ; la PME voit un indicateur "sauvegarde en attente".

## Requirements *(mandatory)*

### Functional Requirements

#### Page `/matching`

- **FR-001**: Le système DOIT afficher sur `/matching` une liste de cards d'offres triées par score de compatibilité décroissant, chaque card montrant nom de l'intermédiaire, montant, type d'offre et durée.
- **FR-002**: Le système DOIT permettre de filtrer la liste par type d'offre, montant min/max, durée, intermédiaire et secteur, avec persistance des filtres dans l'URL pour partage et rechargement.
- **FR-003**: Le système DOIT proposer une carte géographique des intermédiaires (avec pins) et lier l'interaction sur un pin à la mise en évidence des cards correspondantes.
- **FR-004**: Le système DOIT permettre d'ajouter jusqu'à 3 offres au comparateur (persistance locale entre sessions) puis d'ouvrir une vue tabulaire side-by-side sur `/matching/compare`.
- **FR-005**: Le système DOIT proposer un drawer détail offre listant conditions, documents requis, lien externe, et un CTA "Préparer ma candidature" qui amène à `/candidatures/new?offre_id=...`.

#### Pages `/candidatures` et wizard

- **FR-006**: Le système DOIT afficher sur `/candidatures` la liste tabulaire des candidatures de l'utilisateur avec nom offre, statut (parmi 5 valeurs : brouillon, soumise, en revue, acceptée, refusée), date de mise à jour et % de complétion.
- **FR-007**: Le système DOIT proposer un wizard à 5 étapes pour créer une nouvelle candidature : (1) sélection offre + projet, (2) snapshot des données PME en lecture seule avec lien "Modifier dans profil", (3) checklist + upload documents requis, (4) réponses libres assistées par chat contextuel, (5) récapitulatif et soumission.
- **FR-008**: Le système DOIT autosauvegarder chaque saisie avec un debounce de 800 ms et permettre la reprise d'un brouillon depuis l'étape interrompue.
- **FR-009**: Le système DOIT afficher un bandeau bloquant lorsque la checklist de documents requis est incomplète et fournir un lien direct vers l'upload.
- **FR-010**: Le système DOIT exiger une double confirmation (modale + checkbox cochée) avant la soumission d'une candidature, avec un avertissement explicite "Snapshot intangible — non modifiable après envoi".
- **FR-011**: Le système DOIT, sur le détail d'une candidature soumise, afficher la timeline des transitions de statut et les éventuels commentaires de l'intermédiaire, en lecture seule.
- **FR-012**: Le système DOIT enregistrer chaque soumission dans le journal d'audit (action utilisateur, identifiant candidature, horodatage).
- **FR-013**: Toute saisie interactive du chat assistant en étape 4 (radios, checkboxes, upload, sliders, datepickers) DOIT s'afficher dans un bottom sheet animé, jamais inline dans la bulle de l'IA, et un bouton "Répondre librement" DOIT permettre à tout moment de basculer en saisie texte libre.

#### Page `/simulateur`

- **FR-014**: Le système DOIT proposer 4 sliders (montant, durée, type d'investissement, part de subvention) et calculer en temps réel mensualités, coût total, économie estimée et impact CO2 évité.
- **FR-015**: Le système DOIT visualiser les résultats sous forme de chart de barres (mensualités), chart en ligne (cumul intérêts) et camembert (décomposition coûts).
- **FR-016**: Le système DOIT debounce les recalculs à 300 ms pour éviter les requêtes en rafale lors d'ajustements rapides de slider.
- **FR-017**: Le système DOIT permettre de sauvegarder une simulation et de la retrouver dans `/simulateur/historique`.
- **FR-018**: Le système DOIT proposer un CTA "Trouver des offres compatibles" qui redirige vers `/matching` avec les paramètres montant et durée passés en query string et appliqués comme filtres pré-cochés.

#### Transverses

- **FR-019**: Toutes les valeurs monétaires affichées DOIVENT respecter le format `{montant, devise}` typé (FCFA et EUR pour le MVP), sans calculs en virgule flottante imprécise (P5 constitution).
- **FR-020**: Toute donnée financière ou ESG affichée DOIT être traçable à une source vérifiée (P1 constitution) ; les estimations issues d'un calcul (mensualités, CO2) sont étiquetées comme telles.
- **FR-021**: Les pages DOIVENT être mobile-first, navigables au clavier, et compatibles avec les lecteurs d'écran pour les tableaux et les charts (alt-textes/résumés).
- **FR-022**: Toute mutation (sauvegarde brouillon, soumission, sauvegarde simulation) DOIT être audit-tracée avec `{user_id, account_id, ts, entity, source_of_change}` (P3 constitution) et propagée bidirectionnellement vers le chat si une session est ouverte (P8).

### Key Entities

- **Offre** : entité du catalogue (nom, intermédiaire, type, montant_min, montant_max, durée, secteurs éligibles, documents requis, lien externe, géolocalisation intermédiaire).
- **Score de compatibilité** : valeur calculée côté backend (F25) entre projet PME et offre, exposée comme attribut décoratif des cards.
- **Candidature** : dossier en construction ou soumis (offre liée, projet lié, statut, % complétion, étape courante, snapshot_json à la soumission, documents joints, réponses libres). Cycle : brouillon → soumise → en revue → acceptée|refusée. `snapshot_json` immuable après soumission.
- **Simulation** : configuration d'inputs (montant, durée, type, part subvention) + résultats calculés (mensualités, coût total, économie, CO2 évité) + horodatage. Sauvegardable, listable.
- **Comparateur (état UI)** : ensemble jusqu'à 3 offres, persistant en stockage local, consommé par `/matching/compare`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME peut filtrer "subvention + < 100k EUR" sur `/matching` et obtenir une liste cohérente d'au moins 5 offres en moins de 2 secondes (LCP) sur catalogue de 50 offres.
- **SC-002**: 90 % des PME testées (panel de 5) complètent le wizard 5 étapes en moins de 15 minutes lors d'un test utilisateur réel.
- **SC-003**: Le simulateur recalcule et restitue les charts en moins de 200 ms perçus après chaque mouvement de slider, sur connexion 4G standard.
- **SC-004**: 100 % des candidatures soumises pendant la période de test produisent un snapshot intangible vérifiable et reproductible 5 ans après (test : exporter le snapshot, le réimporter, l'afficher à l'identique).
- **SC-005**: Le comparateur affiche jusqu'à 3 offres en table side-by-side, et 100 % des participants au test utilisateur identifient correctement les différences de conditions sans aide.
- **SC-006**: Depuis le simulateur, le CTA "Trouver des offres compatibles" amène 100 % du temps vers `/matching` avec les filtres montant et durée correctement pré-appliqués.
- **SC-007**: Un brouillon de candidature interrompu (fermeture navigateur) est repris à l'identique dans 100 % des cas testés (10 reload tests sur 5 wizards différents).
- **SC-008**: Aucune candidature n'est soumise sans la double confirmation (test : 0 soumission accidentelle observée sur 20 sessions de test).

## Assumptions

- Les modules backend F25 (matching), F26 (générateur dossiers), F27 (simulateur) exposent les API nécessaires (endpoints REST documentés) ; cette feature est strictement UI/UX.
- Les composants F36 (design tokens), F37 (UI primitives), F38 (app shell), F39 (bottom sheet engine), F40 (viz library), F41 (chat conversational layer) sont disponibles et stables.
- Les devises supportées au MVP sont FCFA et EUR (pas d'USD ni multi-currency), avec parité fixe FCFA-EUR à 655.957 (P5 constitution).
- Les rôles applicatifs sont uniquement `PME` et `Admin` (P7 constitution) — aucune notification push ou webhook vers un intermédiaire ; la mise à jour des statuts de candidature se fait manuellement par la PME via l'UI ou l'admin.
- Le scoring de compatibilité utilise des poids par défaut figés au MVP ; l'ajustement admin des poids est hors-scope.
- Les langues PME utilisateur sont FR par défaut ; l'EN n'est activé que pour les candidatures dont l'offre liée déclare `accepted_languages` incluant `'en'`. Wolof/Bambara post-MVP.
- Les utilisateurs PME ont une connexion 4G ou wifi acceptable ; le mode hors-ligne complet (PWA service worker) est hors-scope du MVP.
- L'historique de simulations est privé à la PME (pas de partage public au MVP).
- Les comparateurs sont stockés en `localStorage` côté navigateur et donc liés au device — pas de synchronisation multi-device au MVP.
- La carte Leaflet utilise un fond carto OpenStreetMap public (pas d'abonnement payant requis au MVP).

## Hors-scope MVP

- Match scoring custom (poids ajustables par admin) → P2.
- Notifications push d'acceptation/refus → interdit par P7 constitution ; mise à jour manuelle PME ou admin uniquement.
- Multi-currency simulateur au-delà de FCFA + EUR → post-MVP.
- Co-signature wizard (CFO + CEO sur la même candidature) → post-MVP.
- Synchronisation multi-device du comparateur → post-MVP.
- Mode PWA hors-ligne complet → post-MVP.
- Notifications email/SMS automatiques sur changement de statut → post-MVP (déclencheurs manuels uniquement au MVP).
