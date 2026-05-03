# Feature Specification: Plan d'action ESG UI (F45)

**Feature Branch**: `045-plan-action-ui`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "@docs_et_brouillons/features/45-plan-action-ui.md — Page `/plan-action` qui visualise la feuille de route ESG d'une PME : timeline horizontal par horizon (3/6/12/24 mois), cards triables/filtrables, édition de statut en bottom sheet, régénération du plan, sync chat. UI de F31 (backend plan d'action), dépend de F36/F37/F38/F39 (design system, primitives, shell, bottom sheet) + F23 (scoring) + F47 (visualisations)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Visualiser ma feuille de route en timeline (Priority: P1)

La PME ouvre `/plan-action` après avoir lancé son scoring ESG et voit immédiatement sa feuille de route sous forme de timeline horizontale segmentée par horizon (3/6/12/24 mois). Chaque jalon est coloré selon sa priorité (haute/moyenne/basse), affiche son titre au survol, et apparaît avec une animation stagger discrète à l'arrivée sur la page.

**Why this priority** : c'est la promesse centrale de la page — donner à la PME une vue d'ensemble lisible et motivante de ses actions ESG. Sans ce rendu, le plan reste une liste plate sans dimension temporelle, ce qui démotive et empêche de prioriser.

**Independent Test** : se connecter avec un compte PME ayant un plan d'action généré, naviguer sur `/plan-action`, vérifier que la timeline s'affiche avec au moins un jalon par horizon présent et que le hover révèle le titre. Ce test ne requiert ni édition ni filtre.

**Acceptance Scenarios** :

1. **Given** une PME connectée avec un plan d'action contenant 5+ étapes réparties sur 3/6/12/24 mois, **When** elle ouvre `/plan-action`, **Then** la timeline horizontale s'affiche en moins de 2 secondes, segmentée par horizon, avec chaque jalon coloré selon sa priorité.
2. **Given** la timeline affichée, **When** l'utilisatrice survole un jalon, **Then** le titre de l'étape s'affiche en tooltip sans modifier la mise en page.
3. **Given** un terminal mobile (largeur < 768 px), **When** la page est rendue, **Then** la timeline bascule en disposition verticale empilée et reste lisible sans scroll horizontal forcé.
4. **Given** un utilisateur avec `prefers-reduced-motion` activé, **When** la page se charge, **Then** les animations stagger sont désactivées et les jalons apparaissent immédiatement.

---

### User Story 2 — Filtrer et trier la liste d'étapes (Priority: P1)

Sous la timeline, la PME consulte la même feuille de route en vue liste : cards d'étapes triées par défaut par priorité décroissante puis horizon ascendant. Elle peut filtrer par priorité, statut, horizon et responsable. Les filtres sélectionnés sont reflétés dans l'URL (query string) pour permettre le partage et la persistance au rechargement.

**Why this priority** : la timeline donne la vue d'ensemble, la liste filtrée permet l'action — c'est ici que la PME identifie ce qu'elle doit faire en premier, ce qui est en cours et ce qui lui revient personnellement. Sans filtres, dès 20+ étapes la page devient inutilisable.

**Independent Test** : avec un plan de 10+ étapes mixant priorités/statuts, sélectionner « priorité haute » et vérifier que seules les étapes haute priorité restent affichées et que l'URL contient le filtre.

**Acceptance Scenarios** :

1. **Given** un plan de 10+ étapes, **When** la PME sélectionne le filtre « priorité = haute », **Then** seules les étapes de priorité haute s'affichent et l'URL devient `/plan-action?priority=haute`.
2. **Given** une URL `/plan-action?priority=haute&status=todo` ouverte directement, **When** la page est chargée, **Then** les filtres sont pré-sélectionnés et la liste est filtrée en conséquence.
3. **Given** une liste filtrée, **When** la PME applique un filtre supplémentaire, **Then** le résultat est visible en moins de 50 ms (filtrage client) sans re-fetch serveur.
4. **Given** une URL avec query string invalide (ex. `?priority=zzz`), **When** la page est rendue, **Then** elle s'affiche sans erreur, ignore le filtre invalide et conserve la liste complète.

---

### User Story 3 — Modifier rapidement le statut d'une étape (Priority: P1)

Pour chaque card d'étape, la PME voit un bouton/checkbox de changement rapide de statut. Une checkbox bascule l'étape entre `todo` et `done` de manière optimiste (mise à jour visuelle immédiate). Pour des changements plus riches (statut intermédiaire, réassignation responsable), un bouton « Modifier » ouvre un bottom sheet avec un formulaire complet.

**Why this priority** : avancer dans le plan = cocher des étapes. Si l'action n'est pas instantanée et fluide, la PME ne se réapproprie pas son plan. C'est l'interaction de plus haute fréquence sur la page.

**Independent Test** : cocher la checkbox d'une étape `todo`, vérifier que l'UI passe à `done` immédiatement, puis recharger la page et vérifier la persistance.

**Acceptance Scenarios** :

1. **Given** une étape en statut `todo`, **When** la PME coche sa checkbox, **Then** l'étape passe visuellement à `done` immédiatement et la barre de progression globale est mise à jour en moins d'une seconde.
2. **Given** un changement optimiste vient d'être déclenché, **When** la requête de persistance échoue (réseau ou erreur serveur), **Then** la card revient à son état précédent, un message d'erreur non bloquant s'affiche et la barre de progression est re-synchronisée.
3. **Given** une étape sélectionnée, **When** la PME clique sur « Modifier statut », **Then** un bottom sheet s'ouvre avec les champs statut + responsable, et la validation persiste les changements puis rafraîchit la card concernée.
4. **Given** un bottom sheet d'édition ouvert, **When** la PME clique en dehors ou appuie sur Échap, **Then** le sheet se ferme sans modifier l'étape.

---

### User Story 4 — Suivre la progression globale (Priority: P1)

En haut de page, la PME voit un indicateur synthétique : barre de progression « X / Y étapes terminées » et KPI « Avancement : Z % ». Cet indicateur reflète à tout moment l'état du plan, et se met à jour à chaque changement de statut (US3) ou régénération (US5).

**Why this priority** : c'est la récompense visible qui donne envie de progresser. Sans rétroaction agrégée, cocher des étapes une par une perd son sens.

**Independent Test** : ouvrir un plan avec 3 étapes terminées sur 10, vérifier l'affichage `3 / 10` et `30 %`. Cocher une étape supplémentaire, vérifier que le KPI passe à `4 / 10` / `40 %` sans rafraîchir la page.

**Acceptance Scenarios** :

1. **Given** un plan de N étapes dont K en statut `done`, **When** la page se charge, **Then** la barre de progression affiche `K / N` et le pourcentage `round(K/N × 100) %`.
2. **Given** une étape passe de `todo` à `done` (US3), **When** la mise à jour est persistée, **Then** le KPI et la barre se recalculent sans rechargement de page.
3. **Given** un plan vide (0 étape), **When** la page se charge, **Then** l'indicateur n'affiche pas de division par zéro mais un état neutre (« — » ou cacher l'indicateur au profit d'un empty state US7/US8).

---

### User Story 5 — Régénérer son plan d'action (Priority: P1)

La PME peut demander la régénération complète de son plan via un bouton « Régénérer mon plan ». Une modale de confirmation explique l'action destructive (le plan courant sera versionné en historique et remplacé), demande le sélecteur d'horizon (6/12/24 mois) et exige une confirmation explicite avant l'appel backend.

**Why this priority** : la PME doit pouvoir réagir à un nouveau scoring ou à une situation modifiée sans support technique. Sans régénération en libre-service, le plan se périme.

**Independent Test** : cliquer « Régénérer », sélectionner « 12 mois », confirmer, vérifier qu'un nouveau plan version v+1 s'affiche en moins de quelques secondes (selon backend F31).

**Acceptance Scenarios** :

1. **Given** une PME sur `/plan-action`, **When** elle clique « Régénérer mon plan », **Then** une modale s'ouvre avec un avertissement clair sur le caractère destructif (versionnement) et un sélecteur d'horizon.
2. **Given** la modale ouverte, **When** la PME confirme avec horizon = 12 mois, **Then** le backend est appelé avec ce paramètre et la page recharge le nouveau plan une fois prêt.
3. **Given** la modale ouverte, **When** la PME annule, **Then** la modale se ferme sans appel backend et le plan courant reste intact.
4. **Given** une régénération qui échoue côté backend, **When** la réponse d'erreur revient, **Then** un message lisible s'affiche, le plan courant reste intact et la PME peut réessayer.

---

### User Story 6 — Sélectionner l'horizon affiché (Priority: P1)

Au-dessus de la timeline, un toggle `6 / 12 / 24 mois` permet à la PME de filtrer les horizons visibles. Le sélecteur n'altère pas le plan stocké : il restreint l'affichage temporel.

**Why this priority** : la PME pense parfois en court terme (6 mois pour un appel) et parfois en stratégique (24 mois). Un toggle d'horizon couvre les deux usages sans dupliquer le plan.

**Independent Test** : avec un plan couvrant 3/6/12/24 mois, basculer sur « 6 mois » et vérifier que seules les étapes ≤ 6 mois restent visibles dans la timeline et la liste.

**Acceptance Scenarios** :

1. **Given** un plan multi-horizons, **When** la PME sélectionne « 6 mois », **Then** seuls les jalons d'horizon ≤ 6 mois s'affichent dans la timeline ET la liste, et l'indicateur de progression se recalcule sur ce sous-ensemble.
2. **Given** « 24 mois » sélectionné par défaut, **When** la PME bascule sur « 12 mois » puis « 6 mois », **Then** les transitions sont fluides et la sélection persiste pendant la session.

---

### User Story 7 — Empty state : pas encore de scoring (Priority: P1)

Si la PME ouvre `/plan-action` sans avoir encore lancé son scoring ESG, la page affiche un empty state explicite : « Lancez votre scoring ESG d'abord » avec un CTA vers `/scoring`. Aucun appel à la génération de plan n'est tenté.

**Why this priority** : sans cet empty state, la page renvoie une erreur ou une liste vide incompréhensible. Diriger explicitement vers le scoring débloque le funnel.

**Independent Test** : se connecter avec un compte PME sans scoring, ouvrir `/plan-action`, vérifier l'empty state et le CTA actif.

**Acceptance Scenarios** :

1. **Given** une PME sans scoring ESG, **When** elle ouvre `/plan-action`, **Then** l'empty state s'affiche avec le message d'amorçage et un bouton menant à `/scoring`.
2. **Given** l'empty state affiché, **When** la PME clique le CTA, **Then** elle est redirigée vers la page de scoring.

---

### User Story 8 — Empty state : aucun gap détecté (Priority: P1)

Si le scoring n'a détecté aucun gap suffisamment significatif pour générer un plan, la page affiche un état de célébration sobre : « Excellent ! Aucune action prioritaire détectée. » avec une suggestion de revenir après prochaine évaluation.

**Why this priority** : valoriser une PME mature et éviter l'anxiété d'une page vide qui semble cassée.

**Independent Test** : seed un scoring sans gap → ouvrir `/plan-action` → vérifier le message de célébration.

**Acceptance Scenarios** :

1. **Given** un scoring complété sans gap exploitable, **When** la PME ouvre `/plan-action`, **Then** un message de célébration s'affiche sans liste vide ni erreur.

---

### User Story 9 — Synchronisation avec le chat (Priority: P1)

Quand un agent ou la PME elle-même modifie une étape via le chat conversationnel (F41), la card concernée sur `/plan-action` se met à jour sans rechargement manuel.

**Why this priority** : le chat est le canal principal de modification dans l'expérience F41 ; sans sync, la page `/plan-action` devient désynchronisée et trompeuse.

**Independent Test** : ouvrir `/plan-action` dans un onglet, déclencher la mutation `entity_updated{action_step}` (via chat ou API simulée), vérifier que la card cible se rafraîchit dans la seconde.

**Acceptance Scenarios** :

1. **Given** `/plan-action` ouverte, **When** un événement `entity_updated{action_step}` est émis, **Then** la card concernée recharge ses données et affiche les nouveaux champs.
2. **Given** plusieurs cards sont visibles, **When** un événement cible une seule étape, **Then** seule cette card se rafraîchit (pas de re-fetch global).

---

### User Story 10 — Détail d'une étape (Priority: P1)

Chaque card affiche : titre, description, priorité, horizon (date cible), statut (chip), responsable (avatar), source du gap (lien vers l'indicateur d'origine). Un clic sur le lien source ouvre la fiche indicateur correspondante.

**Why this priority** : la traçabilité (« pourquoi cette action ? ») est exigée par la constitution P1 (sourcing) et rassure la PME.

**Independent Test** : afficher une card et cliquer sur le lien source → vérifier la navigation vers l'indicateur source.

**Acceptance Scenarios** :

1. **Given** une étape liée à un indicateur source, **When** la card s'affiche, **Then** tous les champs (titre, description, priorité, horizon, statut, responsable, source) sont visibles ou explicitement marqués « non renseigné ».
2. **Given** un clic sur le lien source, **When** l'indicateur existe, **Then** la fiche indicateur s'ouvre. Sinon, un fallback discret indique « source non disponible ».

---

### User Story 11 — Historique des versions (Priority: P2)

La PME peut consulter en lecture seule les plans antérieurs à la version courante via un drawer « Historique ». Utile après une régénération (US5).

**Why this priority** : utile mais non bloquant pour le MVP. Permet d'en différer l'implémentation en P2.

**Independent Test** : régénérer un plan, ouvrir l'historique et vérifier la présence de la version précédente en lecture seule.

**Acceptance Scenarios** :

1. **Given** au moins 2 versions de plan existent, **When** la PME ouvre le drawer historique, **Then** elle voit la liste des versions antérieures avec date de création, sans pouvoir les modifier.

---

### User Story 12 — Export PDF (Priority: P2)

La PME peut exporter son plan d'action courant au format PDF via un bouton dédié.

**Why this priority** : valeur ajoutée mais non critique pour le MVP. Dépend du backend F51 (génération PDF).

**Independent Test** : cliquer « Exporter en PDF », vérifier le téléchargement d'un fichier PDF lisible contenant la liste des étapes filtrées.

**Acceptance Scenarios** :

1. **Given** un plan affiché, **When** la PME clique « Exporter en PDF », **Then** un PDF est généré côté backend et téléchargé localement, contenant titre, KPI de progression et liste des étapes.

---

### Edge Cases

- **Plan partiellement chargé** : si l'API renvoie une réponse partielle (timeout sur certaines étapes), la timeline et la liste affichent ce qui est disponible avec un indicateur d'erreur localisé, pas une page entièrement cassée.
- **Étape sans horizon défini** : afficher l'étape dans une colonne « Sans échéance » plutôt que de la masquer.
- **Étape sans responsable** : afficher un avatar neutre + libellé « Non assigné » plutôt qu'un champ vide.
- **Régénération concurrente** : si la PME clique « Régénérer » deux fois rapidement, la seconde requête est ignorée tant que la première n'a pas répondu.
- **Cocher pendant un fetch en cours** : la mise à jour optimiste est mise en file et appliquée séquentiellement pour préserver la cohérence.
- **Filtres multi-valeurs incompatibles** : si une combinaison ne renvoie aucune étape, afficher un état « Aucune étape ne correspond à ces filtres » avec un bouton pour réinitialiser.
- **Connexion perdue** : un bandeau d'avertissement signale que les modifications optimistes seront retentées à la reconnexion ; les changements en attente sont mis en file d'attente locale.
- **Préférence `prefers-reduced-motion`** : toutes les animations stagger et entrées/sorties de bottom sheet sont désactivées ou réduites à un fondu instantané.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT afficher la feuille de route ESG d'une PME sur la route `/plan-action`, accessible uniquement à un utilisateur PME authentifié sur son propre tenant (RLS).
- **FR-002** : Le système DOIT afficher la feuille de route sous deux formes synchronisées : une timeline horizontale segmentée par horizon (3/6/12/24 mois) et une liste de cards triables/filtrables.
- **FR-003** : La timeline DOIT colorer chaque jalon selon sa priorité (haute, moyenne, basse) et révéler le titre au survol.
- **FR-004** : La timeline DOIT basculer en disposition verticale sur viewport < 768 px.
- **FR-005** : La liste DOIT être triée par défaut par priorité décroissante puis horizon ascendant.
- **FR-006** : Le système DOIT permettre de filtrer la liste par priorité, statut, horizon et responsable, avec persistance des filtres dans l'URL (query string).
- **FR-007** : Une URL contenant un filtre invalide DOIT charger la page sans erreur en ignorant le filtre invalide.
- **FR-008** : Chaque card DOIT afficher : titre, description, priorité, horizon (date), statut, responsable et lien vers la source du gap.
- **FR-009** : Chaque card DOIT proposer une checkbox de bascule rapide `todo` ↔ `done` avec mise à jour optimiste de l'UI.
- **FR-010** : En cas d'échec de persistance d'une mise à jour optimiste, le système DOIT restaurer l'état précédent et afficher un message d'erreur non bloquant.
- **FR-011** : Chaque card DOIT proposer un bouton « Modifier statut » qui ouvre un bottom sheet permettant d'éditer le statut et le responsable, conformément à la règle UX constitutionnelle (P10) interdisant les inputs inline.
- **FR-012** : Le bottom sheet d'édition DOIT pouvoir être fermé par clic extérieur ou touche Échap sans modifier l'étape.
- **FR-013** : Le système DOIT afficher en haut de page une barre de progression et un KPI « X / Y étapes — Z % » qui se mettent à jour à chaque changement de statut sans rechargement.
- **FR-014** : Le système DOIT proposer un bouton « Régénérer mon plan » qui ouvre une modale de confirmation avec sélecteur d'horizon (6 / 12 / 24 mois) et avertissement explicite sur le versionnement du plan courant.
- **FR-015** : La régénération DOIT être idempotente côté UI : un double-clic ne déclenche qu'une requête tant que la précédente n'a pas répondu.
- **FR-016** : Le système DOIT proposer un toggle d'horizon `6 / 12 / 24 mois` qui filtre l'affichage (timeline + liste + KPI) sans modifier le plan stocké.
- **FR-017** : Si la PME n'a pas encore lancé son scoring ESG, la page DOIT afficher un empty state explicite avec CTA vers `/scoring` sans tenter de générer de plan.
- **FR-018** : Si le scoring est complété mais sans gap exploitable, la page DOIT afficher un message de célébration sobre.
- **FR-019** : Le système DOIT s'abonner à l'EventBus chat (`entity_updated{action_step}`) et rafraîchir la card concernée sans re-fetch global de la page.
- **FR-020** : Toutes les animations (stagger timeline, entrée bottom sheet, transitions) DOIVENT respecter la préférence `prefers-reduced-motion`.
- **FR-021** : Toutes les chaînes utilisateur (libellés, messages, erreurs) DOIVENT être en français par défaut.
- **FR-022** : Le système DOIT exposer un drawer « Historique des versions » en lecture seule (priorité P2) accessible depuis la page.
- **FR-023** : Le système DOIT exposer un bouton « Exporter en PDF » (priorité P2) qui s'appuie sur le backend de génération PDF.
- **FR-024** : La page DOIT être protégée par authentification : un utilisateur non authentifié est redirigé vers la page de connexion.
- **FR-025** : Le système DOIT afficher un fallback discret « source non disponible » si l'indicateur source d'une étape n'existe pas / n'est pas accessible.

### Key Entities *(include if feature involves data)*

- **Plan d'action** : feuille de route ESG d'une PME, versionnée. Attributs clés : version (entier croissant), date de création, horizon par défaut (mois), statut courant/historique. Un seul plan « courant » à la fois par PME.
- **Étape (action step)** : élément atomique d'un plan d'action. Attributs clés : titre, description, priorité (haute/moyenne/basse), horizon (date cible), statut (todo/doing/done), responsable (utilisateur PME), référence vers l'indicateur ou le gap source.
- **Indicateur source** : pointeur vers l'indicateur ESG ayant généré l'étape (provenant de F23 scoring). Permet la traçabilité exigée par la constitution P1.
- **Filtre vue** : ensemble côté client { priorité, statut, horizon, responsable } persisté dans l'URL.
- **Événement de synchronisation** : message émis par le bus chat (`entity_updated`) indiquant qu'une étape précise a été mise à jour à distance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME ayant un plan généré peut visualiser timeline + liste de 5+ étapes en moins de 2 secondes après l'ouverture de la page (perception « instantanée »).
- **SC-002** : 90 % des changements de statut par checkbox aboutissent en moins d'une seconde côté UI (avant ou après confirmation serveur), grâce à la mise à jour optimiste.
- **SC-003** : Un filtre client (priorité, statut, horizon, responsable) renvoie son résultat visible en moins de 50 ms pour des plans jusqu'à 100 étapes.
- **SC-004** : Lorsqu'une PME applique le filtre « priorité = haute », seules les étapes haute priorité s'affichent et l'URL reflète le filtre, garantissant la reproductibilité du partage de lien.
- **SC-005** : Une régénération de plan (US5) débouche sur une nouvelle version v+1 sans perte de l'ancienne, vérifiable via l'historique (US11) lorsque celui-ci est livré (P2).
- **SC-006** : La page est utilisable sur mobile (< 768 px) sans scroll horizontal forcé et conserve la lisibilité de la timeline (passage en vertical).
- **SC-007** : 100 % des utilisateurs ayant `prefers-reduced-motion` activé voient une page sans animations stagger ni transitions superflues.
- **SC-008** : Les utilisateurs qui ouvrent `/plan-action` sans scoring préalable atteignent la page `/scoring` en un clic depuis l'empty state.
- **SC-009** : Une mutation déclenchée depuis le chat (sync via EventBus) met à jour la card concernée en moins d'une seconde sans rechargement de la page.
- **SC-010** : Aucune régression de sécurité : un utilisateur authentifié sur le tenant A ne peut pas voir ni modifier le plan d'un tenant B (404, pas 403, conformément à la constitution P2).

## Assumptions

- Le backend F31 (plan d'action) expose les endpoints nécessaires : récupération du plan courant, des versions historiques, mise à jour d'étape (`PATCH /me/action-plan/steps/{id}`), régénération (`POST /me/action-plan/generate?horizon=`).
- Le backend F23 (scoring) est disponible pour déterminer l'éligibilité à la génération de plan (US7) et fournir les indicateurs sources (US10).
- Le backend F51 (export PDF) est livré au moment où l'US12 (P2) est implémentée. Si non, l'US12 reste désactivée derrière un flag.
- Le bus d'événements chat (F41) émet bien des événements de type `entity_updated{action_step, id}` consommables côté frontend via le composable existant `useChatEventBus`.
- Le design system (F36), les primitives UI (F37), le shell de navigation (F38) et le moteur de bottom sheet (F39) sont en place et fournissent les composants `<ChatBottomSheet>`, `<ShowForm>` et les jetons de design (couleurs priorité, typographie, espacements).
- La librairie de visualisation (F47) est disponible pour rendre la timeline horizontale (SVG ou divs animées via gsap stagger 80 ms).
- Les rôles applicatifs sont uniquement PME et Admin (constitution P7). Aucune logique d'intermédiaire (banque, fonds) n'est requise dans cette UI.
- Les responsables d'étape sont des utilisateurs internes à la PME (ID utilisateur du même tenant), pas des contacts externes.
- L'authentification et la session active suffisent à propager le contexte tenant (`account_id`) côté API (RLS Postgres), pas de logique frontend supplémentaire pour le multi-tenant.
- La langue par défaut est le français ; aucune autre langue n'est requise pour le MVP de cette UI.
- Les visualisations restent statiques après chargement (pas de drag-and-drop pour réordonner — hors scope MVP, voir feature brief).
- Les notifications email d'échéance sont hors scope (deferred F31 selon le brief).
- Les filtres URL sont parsés côté client : la version SSR de la page n'a pas besoin d'interpréter les filtres pour rendre du contenu utile.
