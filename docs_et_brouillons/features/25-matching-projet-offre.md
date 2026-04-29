# F25 — Matching Projet ↔ Offre (double score, comparateur, alertes)

**Phase** : 6 — Conseiller Financement (Module 3)
**Modules brainstorm** : 3.2 (Matching Intelligent Projet ↔ Offre)
**Dépendances** : F12, F23, F08
**Estimation** : 2.5 jours

## Contexte et objectif

> **Vérité du terrain (du brainstorming)** : le matching n'est jamais "Projet ↔ Fonds" mais toujours "Projet ↔ Offre" (couple Fonds × Intermédiaire). L'intermédiaire est souvent le **vrai filtre** — un projet peut être éligible GCF mais incompatible BOAD.

Cette feature livre :
- Un service de **matching automatique** projet ↔ offre avec score de compatibilité,
- **Décomposition en deux scores** : compatibilité fonds source + compatibilité intermédiaire,
- Liste des **critères couverts / manquants** par couche, chacun cliquable vers sa source,
- Recommandations personnalisées d'offres,
- **Comparateur d'offres pour un même fonds** via plusieurs intermédiaires (ex : GCF via BOAD vs GCF via UNDP) — différenciation majeure vs autres plateformes,
- Alertes sur les nouveaux appels à projets pertinents.

## User Stories

### US1 — Voir les Offres compatibles avec mon projet (P1)
**En tant que** PME,
**je veux** sur la page d'un projet, voir une liste d'Offres recommandées triées par compatibilité décroissante,
**afin de** identifier les pistes de financement pertinentes.

**Test indépendant** : projet renseigné (montant, type d'impact, géographie) → endpoint matching → liste d'au moins 3 Offres avec score de compatibilité.

### US2 — Score de compatibilité décomposé fonds + intermédiaire (P1)
**En tant que** PME,
**je veux** que chaque Offre recommandée affiche **deux scores** :
- compatibilité avec le **fonds source** (taxonomie, plafonds, géographie),
- compatibilité avec l'**intermédiaire** (politique sectorielle, taille PME, garanties),

et le score global = `min(fonds, intermediaire)`.

**afin de** voir où je suis bloquée (intermédiaire le plus souvent).

**Composant** : `<ShowMatchCard>` (F16) avec layout dédié 2 scores.

### US3 — Détail des critères couverts/manquants par couche (P1)
**En tant que** PME,
**je veux** cliquer sur une Offre recommandée et voir :
- critères du **fonds** : ✓ couverts, ✗ manquants (avec source officielle de chaque critère),
- critères de l'**intermédiaire** : idem,
- documents requis (union fonds + intermédiaire) : checklist,
- frais effectifs (fonds + marges intermédiaire) en Money typé,
- délais effectifs.

**afin de** comprendre exactement ce qui me sépare de l'éligibilité.

### US4 — Comparateur multi-intermédiaires pour un même fonds (P1)
**En tant que** PME,
**je veux** voir un tableau comparatif des Offres dérivées d'un même fonds (ex : GCF) à travers ses différents intermédiaires (BOAD, UNDP, PNUE, Acumen),
**afin de** choisir la voie d'accès la plus pertinente.

**Composant** : `<ShowComparisonTable>` (F16) avec colonnes : intermédiaire, score compat., délais, frais, docs requis (count), taux de succès historique (si dispo).

### US5 — Alertes sur les nouveaux appels à projets pertinents (P2)
**En tant que** PME,
**je veux** recevoir une notification (email + dashboard) quand :
- une nouvelle Offre `submission_mode=call_for_proposals` est ajoutée et je matche ≥ 60%,
- une Offre dont je matche ≥ 60% a une deadline approchant (J-30, J-7, J-1).

**afin de** ne rater aucune opportunité.

### US6 — Filtres et tri (P2)
**En tant que** PME,
**je veux** filtrer les recommandations par : pays/zone, instrument (subvention/prêt/blending), montant, score min, intermédiaire,
**afin de** explorer.

### US7 — Action "Lancer une candidature" (P1)
**En tant que** PME,
**je veux** un bouton "Candidater à cette Offre" qui crée une `Candidature` (cohérent F08, F04 snapshot) et m'amène vers F26 (Génération de dossier),
**afin de** transformer une recommandation en action.

### US8 — Tool LLM `find_offers(projet_id, filters)` (P2)
**En tant que** PME via le chat,
**je veux** dire "trouve-moi des offres pour ce projet" → le LLM invoque `find_offers` → réponse avec `show_match_card` × N,
**afin de** matcher en conversationnel.

## Exigences fonctionnelles

- **FR-001** : Service backend `MatchingService` :
  - `match(projet_id, max=10) -> list[OfferMatch]`,
  - parcourt les Offres `published` avec accréditation active,
  - pour chaque, calcule `(fonds_score, intermediaire_score, criteres_couverts_fonds, criteres_manquants_fonds, criteres_couverts_intermediaire, criteres_manquants_intermediaire, documents_requis_count)`,
  - retour trié par `min(fonds, intermediaire)` desc.
- **FR-002** : Le calcul d'un score de compatibilité réutilise le moteur F23 (`ScoringService`) appliqué au référentiel du fonds (puis de l'intermédiaire) avec les valeurs du projet.
- **FR-003** : Endpoints :
  - `GET /me/projets/{id}/matching` (liste recommandations),
  - `GET /me/projets/{id}/matching/{offre_id}` (détail compat.),
  - `GET /me/fonds/{fonds_id}/intermediaires-comparator?projet_id=` (US4),
  - `POST /me/projets/{id}/candidatures` body `{offre_id}` (créer candidature, snapshot — cohérent F08/F04).
- **FR-004** : Page Vue `/profil/projets/[id]/matching` : liste des Offres + composant `<ShowMatchCard>` × N.
- **FR-005** : Page Vue `/profil/projets/[id]/matching/[offre_id]` : détail compat avec critères (couverts/manquants) + checklist docs + frais + délais.
- **FR-006** : Page Vue `/profil/fonds/[fonds_id]/comparator` (depuis carte projet, navigation latérale) : tableau comparatif intermédiaires.
- **FR-007** : Job cron (cohérent F31) `notify_new_matching_calls` : tous les matins, pour chaque PME, identifie les nouvelles Offres `call_for_proposals` matchant ≥ 60% sur ses projets actifs → email.
- **FR-008** : Tool LLM `find_offers(projet_id, max=5, filters?)` exposé en F14, utilise `MatchingService`.
- **FR-009** : Bouton "Candidater" sur la carte/page d'une Offre : POST sur l'endpoint candidature, redirection vers F26 (génération dossier).
- **FR-010** : Filtres et tri implémentés côté client (pour réactivité), mais le backend supporte aussi des query params pour l'API.

## Exigences non-fonctionnelles

- **NFR-001** : Matching d'un projet contre 100 Offres en < 1s (calcul de score F23 réutilisé, parallélisable).
- **NFR-002** : Sources cliquables sur tous les critères (cohérent F03).
- **NFR-003** : Le snapshot (F04) à la création d'une candidature contient bien tous les éléments nécessaires (projet, offre, référentiels, scores calculés).
- **NFR-004** : Les notifications par email sont envoyées avec un template HTML + lien cliquable.

## Entités clés

- **Candidature** (déjà créée F01, étendue ici) : `id, account_id, projet_id, offre_id, statut ENUM('brouillon','en_redaction','soumise','en_instruction','acceptee','refusee','retiree'), snapshot_json, soumission_at NULL, version`.
- **OfferMatch** (objet de transport, pas table).

## Success Criteria

- **SC-001** : Projet renseigné → 5+ Offres recommandées avec scores corrects (test sur PME démo).
- **SC-002** : Cliquer sur une Offre montre détail des 2 scores avec critères sourcés.
- **SC-003** : Comparateur GCF via BOAD vs GCF via UNDP affiche correctement.
- **SC-004** : "Candidater" crée une candidature + snapshot conforme.
- **SC-005** : Cron alertes nouveaux appels exécuté quotidiennement (testable manuellement).

## Hors-scope MVP

- Apprentissage du matching (post-MVP : si une PME accepte/refuse régulièrement certains types d'Offres, ajuster recommandations).
- Notifications push mobile (post-MVP).
- Workflow de validation interne d'une candidature avant soumission (post-MVP).
- Tracker externe de soumission (Module 8 extension Chrome reprendra).
- Score de pré-financement (probabilité de succès) — post-MVP, dépend de track-record.

## Risques et points de vigilance

- **Critères qualitatifs vs quantitatifs** : un critère "projet doit avoir un sponsor public" est qualitatif et difficile à scorer. Solution : `severity=warning` + interrogation par tool LLM si non renseigné.
- **Données manquantes côté projet** : si la PME n'a pas renseigné le pays ou le secteur, le matching donne du n'importe quoi. UX : afficher "Veuillez compléter ces champs pour des recommandations fiables" + lien vers F12.
- **Complexité fonds + intermédiaire** : pour 100 fonds × 100 intermédiaires = potentiellement 10 000 Offres. En MVP, on aura ~50 Offres réelles. Penser scaling post-MVP (index sur critères + lookup matriciel).
- **Performance + mise à jour** : si un projet est édité, les scores sont à recalculer. Réutiliser le cache F23 + invalidation.
- **Critères blocking vs warning** : un critère blocking non couvert => score = 0. Un warning baisse le score. Définir clairement (cohérent F09 `severity`).
