# Research — F47 Empreinte carbone UI

**Date** : 2026-05-04
**Phase** : 0 (Outline & Research)
**Statut** : Toutes les `NEEDS CLARIFICATION` du Technical Context sont résolues ci-dessous.

## Décisions techniques

### D1 — Modèle d'édition de ligne sans introduire de table `carbon_line`

**Décision** : implémenter `POST /me/carbon/{year}/edit-line` comme un wrapper qui (a) lit le **dernier** `carbon_footprint` de l'année (`source_data_json`), (b) reconstruit la liste `CarbonSourceItem`, (c) remplace ou ajoute la ligne ciblée par `code`, (d) appelle `service.compute_footprint(...)` qui crée une **nouvelle** row `carbon_footprint` (snapshot complet, append-only).

**Rationale** :
- Aucune nouvelle table → 0 migration → conforme au principe « ajouts ciblés » du plan.
- Append-only → P3 satisfait par construction (chaque édition = nouvelle empreinte avec `version` incrémenté + audit `manual`).
- Réutilise 100 % du moteur existant (`engine.compute_total`, `engine.compute_line`) → pas de duplication ni de divergence de logique.

**Alternatives évaluées** :
- *Table `carbon_data` (ligne unitaire éditable + recalc à la volée)* : rejeté → introduit une migration, doublonne le `source_data_json`, complique l'audit (faut-il auditer chaque ligne **et** l'agrégat ?), inflige une dette à F28.
- *PATCH ciblé sur `breakdown_json`* : rejeté → mute un snapshot supposé immuable (P4), casse l'append-only.

### D2 — Représentation des « lignes virtuelles » côté UI

**Décision** : la `breakdown` retournée par `GET /me/carbon/{year}` est groupée côté frontend par `(scope, categorie)` via `groupCarbonByScope.ts`. Chaque entrée groupée porte la clé `code` (clé naturelle de `CarbonSourceItem`) qui sert d'identifiant pour l'édition (`POST .../edit-line` accepte `code` en payload, **pas** un UUID).

**Rationale** : le backend n'expose pas d'UUID de ligne (les lignes vivent dans `source_data_json` et `breakdown_json` du dernier snapshot). `code` est stable, lisible, et déjà unique par poste dans le source_data soumis.

**Alternatives évaluées** :
- *Générer un UUID par ligne côté backend lors du compute* : rejeté → casse la rétrocompat (les empreintes existantes n'en ont pas) et complique le edit-line sans valeur ajoutée pour le MVP.

### D3 — Calcul de la couverture % côté frontend

**Décision** : la couverture est calculée côté frontend par `computeCarbonCoverage.ts` à partir de la `breakdown` reçue et d'une constante `CARBON_EXPECTED_POSTS_BY_SCOPE` partagée :
- Scope 1 : `combustion_fixe`, `combustion_mobile`, `fugitives` (3 postes attendus).
- Scope 2 : `electricite`, `vapeur`, `chaleur`, `froid` (4 postes attendus).
- Scope 3 : `achats`, `transport_amont`, `dechets`, `deplacements`, `transport_aval` (5 postes attendus, MVP).
- Couverture par scope = `postes_renseignés / postes_attendus × 100` ; couverture globale = moyenne pondérée par le nombre de postes attendus.

**Rationale** : couverture est une notion d'UX (« ai-je rempli tout ce que je devrais ? ») qui dépend d'un référentiel implicite (GHG Protocol MVP) ; la mettre côté frontend évite un endpoint dédié, garde la liste évolutive à un seul endroit, et permet d'afficher un avertissement contextuel.

**Alternatives évaluées** :
- *Calcul backend retourné dans `GET /me/carbon/{year}`* : rejeté pour MVP → couplerait l'API à la liste MVP des postes Scope 3, ralentirait l'évolution. À reconsidérer en F49+ si la liste devient configurable.

### D4 — Persistance des réponses partielles du wizard empty-state

**Décision** : `useCarbonWizard` persiste les réponses partielles dans `localStorage` sous la clé `carbon-wizard-{account_id}-draft`. À chaque pas, on sérialise `{ step: 1|2|3, answers: { energy: {...}, mobility: {...}, purchases: {...} } }`. La validation finale du pas 3 envoie un `POST /me/carbon/compute` agrégé puis purge la clé.

**Rationale** : le brouillon F47 demande explicitement « réponses partielles conservées » (US6 AS3, edge case « wizard interrompu »). `localStorage` est suffisant (pas de besoin cross-device). La clé est scopée par `account_id` pour éviter la fuite entre comptes sur le même navigateur.

**Alternatives évaluées** :
- *Persistance backend (table `carbon_wizard_draft`)* : rejeté → introduirait une table, hors scope ajouts ciblés.
- *`sessionStorage`* : rejeté → ne survit pas à la fermeture d'onglet, ce qui contredit l'US6.

### D5 — Switch ADEME ↔ IPCC (US8 P2)

**Décision** : au MVP F47, le composant `FactorReferentielSwitch.vue` est livré **présent mais désactivé** (avec infobulle « Comparateur IPCC à venir » et badge « Estimation, pas référence officielle » sur le côté). Aucun support backend du paramètre `factor_dataset`. La vraie implémentation (lookup multi-référentiels + recalcul à la volée + persistance non) est traitée par une feature ultérieure (F49 ou suite F28).

**Rationale** :
- Construire le multi-référentiel correctement nécessite (a) un dataset IPCC AR6 catalogué et versionné dans `facteur_emission`, (b) un mapping code → (ADEME, IPCC), (c) un paramétrage du `service.compute_footprint`. Trois chantiers backend hors scope d'une feature « UI ».
- Conserver le composant dans le DOM permet de valider l'emplacement UX et le badge, et garantit que le jour où le backend arrive, l'intégration est triviale (un `fetch` change).

**Alternatives évaluées** :
- *Retirer complètement le switch du MVP* : rejeté → le brouillon F47 le mentionne explicitement comme P2 visible (réassurance utilisateur sur la rigueur méthodologique).
- *Mock côté frontend (multiplie les valeurs ADEME par un facteur fixe)* : rejeté → trompeur, contraire à P1 Sourcing.

### D6 — Source obligatoire & rétrocompat schéma `CarbonSourceItem`

**Décision** : étendre `CarbonSourceItem` avec `source_id: UUID | None = None`. Comportement :
- `POST /me/carbon/compute` (existant) : continue d'accepter `source_id` absent ou `None` → rétrocompat assurée pour les clients existants (extension Chrome F33–F34, scripts d'import).
- `POST /me/carbon/{year}/edit-line` (nouveau) : `source_id` **non null** + service vérifie `Source.statut == "verified"`. Sinon `400 source_not_verified`.
- Toute ligne créée par l'UI nouvelle (`/carbone`) passe par `edit-line` ou par le wizard (qui collecte source obligatoirement) → 100 % source_id.
- Lignes anciennes sans source_id : affichées avec badge « Source manquante » + CTA « Compléter » qui ouvre l'edit-line drawer pré-rempli.

**Rationale** : équilibre entre P1 Sourcing strict pour les nouvelles écritures et continuité opérationnelle des intégrations existantes. La conformité progressive est journalisée par la couverture % (qui peut intégrer un poste « source manquante » comme dégradé).

**Alternatives évaluées** :
- *Faire `source_id` obligatoire partout* : rejeté → casse l'extension Chrome F33–F34 et les imports CSV historiques jusqu'à leur migration.

### D7 — Évolution annuelle vs mensuelle

**Décision** : la courbe `EvolutionLineChart.vue` affiche **un point par année** sur les N dernières années (max 5) — pas de granularité mensuelle au MVP, car le modèle `carbon_footprint` est annualisé. Si plusieurs `carbon_footprint` existent pour une année (recalculs), seule la dernière (`computed_at` max) est utilisée.

**Rationale** : aligne strictement sur le modèle de données existant. Le brouillon F47 parle d'« évolution annuelle » dans la description et de « N courante vs N-1 par scope » dans US6 — pas de mensuel.

**Alternatives évaluées** :
- *Désagréger le source_data en mensualisé via la date de la facture-source* : rejeté → la `source` actuelle ne porte pas de période, modèle pas prêt, hors scope.

### D8 — Stratégie de cache et invalidation

**Décision** : `useCarbonStore` cache (par `account_id` implicite via JWT) :
- `index` (liste multi-année) : TTL 60 s, invalidé sur tout `entity_updated{carbon_footprint}` reçu via `useChatEventBus`.
- `footprint[year]` : pas de TTL, invalidé sur tout `entity_updated{carbon_footprint, year}` ou succès local d'`edit-line` / `recompute`.
- `coverage[year]` : dérivée pure de `footprint[year]`, recalculée à la volée (pas de cache).

**Rationale** : reproduit le pattern de `useScoringStore` (F46) qui a déjà fait ses preuves. Évite les rechargements inutiles tout en garantissant la fraîcheur après chaque mutation.

**Alternatives évaluées** :
- *TanStack Query (vue-query)* : rejeté → pas dans la stack, surcoût de dépendance pour pas de gain net sur cette feature.

### D9 — Gestion de l'erreur backend lors d'un `edit-line` ou `recompute`

**Décision** : en cas d'échec backend (5xx, timeout, FactorNotFound), le store ne met **pas** à jour son état ; un toast français explicite est affiché via `useToast` (« Recalcul indisponible. Veuillez réessayer dans un instant. ») et l'état précédent reste visible. Pour `FactorNotFound` (404 backend), message dédié indiquant la ligne en faute si possible.

**Rationale** : SC-FR-017. Évite d'afficher un état incohérent. Pattern déjà employé par F46 pour les recalculs scoring.

**Alternatives évaluées** :
- *Optimistic update + rollback* : rejeté pour les recalculs (l'utilisateur n'a pas de valeur prédite à afficher) ; envisageable pour edit-line mais introduit une complexité non justifiée au MVP.

### D10 — Accessibilité du donut et de la courbe

**Décision** : utiliser les composants `<VizDonutChart>` et `<VizLineChart>` de F40 qui exposent déjà :
- Un `<table>` invisible (sr-only) avec les données tabulées (catégorie + valeur + %).
- Navigation clavier (Tab + flèches) entre segments avec annonce ARIA (`role="img"` + `aria-label` dynamique).
- `prefers-reduced-motion` respecté (pas d'animation).

**Rationale** : F40 livre l'accessibilité out-of-the-box. SC-008 satisfait sans code spécifique F47.

**Alternatives évaluées** :
- *Implémenter l'accessibilité ad-hoc* : rejeté → duplique l'effort, divergence garantie à terme.

## Risques résiduels & vigilance

- **R1 — Lookup facteur en `recompute`** : si entre N et N+1 un facteur a été révoqué sans remplaçant actif (cas extrême), `recompute` lèvera `FactorNotFound`. Mitigation : message d'erreur explicite + bouton « Modifier la ligne » qui ouvre le drawer pré-rempli (l'utilisateur change l'unité ou le code pour basculer sur un facteur valide).
- **R2 — Race condition sur `edit-line` concurrents** : deux onglets éditent la même ligne en parallèle. Le second `edit-line` part du dernier snapshot **incluant** le premier → pas de perte. Test à couvrir en E2E (deux onglets).
- **R3 — Volume `breakdown_json` après 5 ans × 12 recalculs/an** : ~60 snapshots par tenant, ~30 lignes chacun → ~1800 lignes JSONB cumulées. Largement sous le seuil critique. Pas d'action requise.
- **R4 — Wizard interrompu sur navigateur tiers** : si `localStorage` est vidé (mode privé, paramètres), les réponses sont perdues. Acceptable au MVP, message explicite dans le wizard (« Vos réponses sont conservées localement »).
- **R5 — Composant `<UiBanner>` ou `<UiPopover>` non livré par F37** : à vérifier dans `frontend/app/components/ui/`. Si absent, fallback vers Tailwind brut + script gsap minimal pour la popover. À confirmer en début de Phase 2.
