# F27 — Simulateur de Financement (coût total réel, ROI vert, comparateur)

**Phase** : 6 — Conseiller Financement (Module 3)
**Modules brainstorm** : 3.4 (Simulateur de Financement)
**Dépendances** : F25, F08
**Estimation** : 1.5–2 jours

## Contexte et objectif

Permettre à la PME de **simuler le coût total réel** d'un financement via une Offre, pas seulement le montant emprunté. C'est un outil de **transparence financière** qui révèle ce que les autres plateformes cachent : les marges intermédiaire, les frais de dossier, les garanties exigées, le taux de change.

> **Du brainstorming Module 3.4** : "**Coût total réel pour la PME** = montant emprunté + marges intermédiaire + frais de dossier + garanties — différencie subvention vs prêt concessionnel vs blending."

Inclut aussi :
- **ROI vert** (méthodologie sourcée — IRIS+/Verra en post-MVP),
- **Projection de l'impact environnemental** (tCO2e évitées, etc. — facteurs sourcés F09),
- **Timeline réaliste** = délais fonds + délais intermédiaire,
- **Comparateur multi-offres** : "Quelle offre coûte le moins / va le plus vite / a le meilleur taux de succès ?".

## User Stories

### US1 — Simuler une Offre (P1)
**En tant que** PME,
**je veux** sur la page d'une candidature ou recommandation, un onglet "Simulateur" qui calcule :
- montant éligible (selon plafonds Offre),
- marges intermédiaire (selon `frais_specifiques`),
- frais de dossier,
- garanties exigées (Money typé),
- coût total sur la durée du financement,
- coût total en pourcentage du montant emprunté.

**afin de** comprendre l'engagement réel.

**Test indépendant** : projet 5M EUR + Offre SUNREF Ecobank → simulation affiche ~5M EUR emprunt + 2% marge + 1% frais dossier + 30% garantie → coût total Y EUR sur 7 ans.

### US2 — Différencier subvention vs prêt vs blending (P1)
**En tant que** PME,
**je veux** que la simulation distingue selon `instruments` de l'Offre (F08) :
- subvention → coût direct = 0 (mais souvent contre-engagements ESG),
- prêt concessionnel → taux faible + remboursement,
- equity → dilution capital,
- blending → mix subvention + prêt avec ratio configurable.

**afin de** comparer pommes avec pommes.

### US3 — Risque de change explicite (P1)
**En tant que** PME emprunteuse en EUR ou USD,
**je veux** voir la différence entre devise d'emprunt (EUR) et devise de remboursement (FCFA) avec :
- équivalent FCFA aujourd'hui (peg fixe ou taux du jour),
- bandeau "risque de change USD" si applicable,
- scénario de stress (taux ±10%).

**afin de** ne pas être surprise.

### US4 — Projection d'impact environnemental (P1)
**En tant que** PME,
**je veux** voir l'impact carbone du projet financé, calculé via les facteurs d'émission (F09) :
- tCO2e évitées sur la durée,
- emplois verts créés,
- bénéficiaires touchés (selon les indicateurs d'impact du projet F12).

**afin de** valoriser l'impact.

### US5 — Timeline réaliste (P2)
**En tant que** PME,
**je veux** voir une timeline visuelle (`show_timeline` F16) :
- soumission dossier,
- pré-instruction intermédiaire (X semaines),
- soumission au fonds (X semaines),
- instruction fonds (X mois),
- décision,
- décaissement (X semaines après accord).

**afin de** anticiper le calendrier.

Données : `delais_effectifs` calculé en F08 (FR-005).

### US6 — Comparateur multi-offres pour un même projet (P1)
**En tant que** PME,
**je veux** sélectionner 2-5 Offres recommandées et lancer un comparateur côte-à-côte qui aligne :
- coût total réel,
- timeline,
- score compatibilité (F25),
- taux de succès historique (si dispo F08),
- documents requis (count).

**afin de** choisir.

**Composant** : `<ShowComparisonTable>` (F16).

### US7 — Tool LLM `simulate_financing(offre_id, projet_id)` (P2)
**En tant que** PME,
**je veux** dire au chat "simule le financement de mon projet panneaux par SUNREF Ecobank" → réponse `show_kpi_card` x N + `show_timeline` + `show_comparison_table`,
**afin de** simulation conversationnelle.

## Exigences fonctionnelles

- **FR-001** : Service backend `SimulationService` :
  - `simulate(projet_id, offre_id, hypotheses?) -> SimulationResult`,
  - calcule : montant éligible, marges, frais, garanties, coût total, équivalent devises, impact CO2e, timeline,
  - retourne tous les éléments avec leurs sources (cohérent F03).
- **FR-002** : Modèle `SimulationHypotheses` configurable : taux d'intérêt par défaut (par instrument), variabilité change ±X%, durée projet (issu de F12 ou override), méthodologie ROI (default basique, pas IRIS+).
- **FR-003** : Endpoints :
  - `POST /me/simulations` body `{projet_id, offre_id, hypotheses?}` → renvoie SimulationResult.
  - `POST /me/simulations/comparator` body `{projet_id, offre_ids:[]}` → tableau comparatif.
- **FR-004** : Page Vue `/profil/candidatures/[id]/simulation` ou `/profil/projets/[id]/simulation?offre_ids=` :
  - Section coût total avec décomposition (carte + barres),
  - Section timeline,
  - Section impact (CO2e, emplois, bénéficiaires),
  - Section change avec bandeau risque,
  - Comparateur si plusieurs offres.
- **FR-005** : Tool LLM `simulate_financing(offre_id, projet_id, hypotheses?)` exposé en F14, utilise `SimulationService`.
- **FR-006** : Sources cliquables sur tous les chiffres affichés (cohérent F03).
- **FR-007** : Helper utilisé F23 (`compute_score`) ou F09 (`compute_impact_co2e`) pour la projection environnementale, branché ici.
- **FR-008** : Pas de persistance des simulations en MVP — recalcul à la volée. Post-MVP : table `simulation_saved` pour comparer dans le temps.

## Exigences non-fonctionnelles

- **NFR-001** : Calcul d'une simulation < 200ms.
- **NFR-002** : Tous les chiffres sont sourcés (cohérent F03).
- **NFR-003** : Money typé partout (cohérent F05).
- **NFR-004** : Gestion explicite de `null`/`unknown` quand une donnée manque (ex : taux d'intérêt non précisé pour un intermédiaire) — afficher "Donnée non disponible — utiliser hypothèses par défaut" plutôt que d'inventer.

## Entités clés

- **SimulationResult** (objet de transport, pas de table en MVP).
- Réutilise **Offre, Fonds, Intermediaire** (F08).
- Réutilise **FacteurEmission** (F09).

## Success Criteria

- **SC-001** : Simulation projet 5M EUR via SUNREF Ecobank donne un coût total réaliste avec sources.
- **SC-002** : Comparateur 3 Offres affiche tableau lisible avec différenciation visuelle.
- **SC-003** : Bandeau risque de change apparaît correctement pour Offre USD vs PME XOF.
- **SC-004** : Tool LLM `simulate_financing` fonctionne dans le chat.
- **SC-005** : Toutes les méthodologies de calcul (intérêts, ROI, impact) sont documentées et sourcées.

## Hors-scope MVP

- Méthodologie IRIS+ ou Verra complète pour ROI vert (post-MVP, MVP : approximation simple sourcée).
- Modèle de Monte-Carlo pour scénarios de risque.
- Persistance des simulations historiques.
- Notifications "votre simulation a évolué" (taux change, mise à jour Offre).
- Support du blending complexe (multi-tranches simultanées).

## Risques et points de vigilance

- **Précision des données catalogue** : si les `frais_json` et `delais_json` (F08) sont approximatifs, la simulation l'est aussi. Préférer des bornes "entre X et Y" plutôt que des valeurs exactes.
- **ROI vert difficile** : il n'existe pas de méthode simple universelle. MVP : on calcule juste l'impact direct (CO2e évitées) sourcé via facteurs d'émission. Post-MVP : IRIS+.
- **Devises et taux** : utiliser le `FxService` de F05. Snapshots quotidiens.
- **Comparateur surchargé** : 5 colonnes × 10 lignes deviennent illisibles. Filtre par "ce qui m'intéresse" (coût, délais, succès).
- **UX simplicité** : un simulateur de financement peut vite devenir un Excel. Démarrer simple, ne pas exposer toutes les hypothèses au début.
