# Phase 0 — Research & Decisions : Credit scoring UI (F48)

Ce document consolide les décisions techniques prises pour résoudre les zones grises identifiées en Phase Outline du plan. Format `Decision / Rationale / Alternatives considered`. Aucun `NEEDS CLARIFICATION` ne reste ouvert : les 5 questions de clarification de la spec sont déjà tranchées et reflétées ici.

---

## R-01 — Mapping factor → bucket sous-score (4 sous-scores UI vs 4 axes backend)

**Decision** : Implémenter un mapping déclaratif côté backend dans `backend/app/credit/subscore_mapping.py` (Python pure module, pas de DB) qui associe chaque `factor_name` exposé par F29 à l'un des 4 buckets `solidite_financiere | performance_operationnelle | engagement_esg | gouvernance`. La fonction `compute_subscores(facteurs: list[FactorOut]) -> dict[str, int|None]` calcule la moyenne pondérée des `contribution` de chaque facteur du bucket, normalisée sur 100. Si aucun facteur n'est rattaché à un bucket (ex. PME n'a pas renseigné les volets ESG), `subscores[bucket] = None` ; l'UI affiche alors « non calculé » (US2 AS2).

**Mapping initial** (à valider lors de l'implémentation contre la liste réelle des facteurs F29) :

| Bucket UI | Axes backend impliqués | Indices typiques de filtrage |
|--|--|--|
| `solidite_financiere` | `financiere` | facteurs liés à `liquidite`, `endettement`, `fonds_propres`, `tresorerie` |
| `performance_operationnelle` | `financiere` | facteurs liés à `marge`, `rentabilite`, `croissance_ca`, `productivite`, `ebe_ratio` |
| `engagement_esg` | `environnementale` + `sociale` | tous les facteurs des deux axes — pondération 50/50 par défaut, surcharge possible par bucket |
| `gouvernance` | `gouvernance` | tous les facteurs de l'axe |

**Rationale** :

- Aucune migration DB : les `facteurs` sont déjà persistés en JSONB sur `credit_score.factor_breakdown` et exposés via `CreditScoreOut.facteurs`.
- L'UI demande explicitement 4 sous-scores nommés (FR-002). Un mapping déterministe et versionné dans le code Python est plus testable qu'un calcul client.
- Le bucket « performance opérationnelle » n'existe pas dans les axes F29 ; on le tire du sous-ensemble approprié de l'axe `financiere`. Le mapping est documenté en tête de fichier comme contrat front/back.
- Si un facteur change de nom côté F29 (méthodologie v2+), le test `test_subscores_extension.py` détectera la dérive (cas 2 : cohérence avec moyenne pondérée des `facteurs` mappés).

**Alternatives considered** :

- *Calcul client-side du mapping* : rejeté — duplique la connaissance entre front/back et casse la cohérence avec l'API publique `GET /methodologie/credit-scoring`.
- *Ajouter un 4e axe backend `operationnelle`* : rejeté — change la sémantique de la méthodologie F29 et requiert une migration des `methodologie.factors` ; surdimensionné pour un besoin UI.
- *Stocker les `subscores` en colonnes propres sur `credit_score`* : rejeté — duplique l'information, casse P6 (pivot Indicateur unique), et ajoute une migration inutile puisque le calcul est déterministe à partir de `facteurs`.

---

## R-02 — Catalogue des dispositifs d'éligibilité (BOAD-vert, SUNREF, Ecobank Green Lending)

**Decision** : Catalogue déclaratif versionné en pure Python dans `backend/app/credit/eligibility_catalog.py`. Chaque dispositif est un objet immuable :

```python
@dataclass(frozen=True)
class EligibilityRule:
    code: str                              # "boad_vert" | "sunref" | "ecobank_green_lending"
    label: str                             # libellé affiché
    description: str                       # 1-2 phrases d'introduction
    min_combine_score: int | None          # seuil minimum sur CreditScoreOut.combine
    min_subscore_engagement_esg: int | None
    min_subscore_solidite_financiere: int | None
    excluded_sectors: tuple[str, ...]      # codes secteurs NACE/CITI exclus
    required_min_size: str | None          # "tpe" | "pme" | "eti"
    source_id: UUID                        # Source verified (document officiel BOAD/AFD/Ecobank)
    version: int
    valid_from: datetime
    valid_to: datetime | None
    matching_offer_query: str              # query_string passée au matching F53 pour filtrer les offres
```

`evaluate_eligibility(score, entreprise) -> list[EligibilityBadgeOut]` itère sur le catalogue actif (filtré par `valid_from <= now < valid_to or valid_to is None`), évalue chaque règle, et retourne pour chaque dispositif : `status ∈ {eligible, not_eligible, incomplete}`, `primary_reason: str | None` (premier critère non satisfait, format human-readable FR), `criteria: list[CriterionEvalOut]` (liste exhaustive — clarification Q5).

**Rationale** :

- Aucune nouvelle table : 3 dispositifs au MVP, ajout d'autres = ajout de constantes Python (revue de code suffit).
- `version` + `valid_from`/`valid_to` respectent P4 (versioning) — un changement de seuil n'invalide pas les scores historiques.
- `source_id` `verified` par dispositif respecte P1 — la modal exposera la pastille `<VizSourcePin>` (FR-018 et P1).
- Catalogue dynamique côté front : l'UI itère sur la liste reçue (clarification Q3) — aucun composant ne code en dur les 3 dispositifs.
- Statut `incomplete` (et non `not_eligible`) est utilisé quand un seuil dépend d'un sous-score `null` (cohérent avec le bandeau « Couverture partielle » FR-012a).

**Alternatives considered** :

- *Table SQL `eligibility_rule`* : rejeté pour MVP — l'admin de catalogue n'est pas dans le scope F48 et l'évolution se fait par PR (revue, audit git suffit). Migration possible plus tard sans casser le contrat API.
- *Évaluation côté front à partir de `methodologie/credit-scoring`* : rejeté — duplique la logique métier sensible (éligibilité financement) côté client et expose les règles aux navigateurs ; moins testable.

---

## R-03 — Endpoint d'historique : forme et limites

**Decision** : `GET /me/credit-score/history?limit=N` retourne `{items: ScoreHistoryEntry[]}` triés desc par `computed_at`. `limit` borné `[1..24]`, défaut `6`. Chaque entrée :

```json
{
  "id": "uuid",
  "combine": 72,
  "solvabilite": 68,
  "impact_vert": 78,
  "subscores": {"solidite_financiere": 70, "performance_operationnelle": 80, "engagement_esg": 65, "gouvernance": 75},
  "methodologie_version": 3,
  "computed_at": "2026-04-01T10:30:00Z",
  "coherence_warning": false
}
```

**Rationale** :

- La spec demande 6 derniers calculs (FR-011, US7) ; cap à 24 pour permettre des vues étendues post-MVP sans changer le contrat.
- Réutilise les mêmes sous-scores (R-01) pour cohérence d'affichage (`ScoreHistoryChart` peut afficher la courbe globale OU une courbe par sous-score).
- Tri desc par `computed_at` permet à l'UI de prendre directement `items[0]` comme « courant » et `items[1]` comme « N-1 » pour le delta (US1).

**Alternatives considered** :

- *Pagination cursor-based* : rejeté — pour 6-24 éléments, `limit` simple suffit.
- *Inclure les `facteurs` dans chaque entry* : rejeté — gonfle la réponse pour un usage hover-only ; détail accessible via `GET /me/credit-score` pour le score courant.

---

## R-04 — Recommandations : dépendance F45 (plan d'action)

**Decision** : `GET /me/credit-score/recommendations?limit=N` lit la table `action_item` de F45 filtrée par `account_id`, où chaque `action_item` est attendu avec :

- `target_subscore: 'solidite_financiere'|'performance_operationnelle'|'engagement_esg'|'gouvernance'|null` (nouveau champ requis F45 — voir ci-dessous).
- `estimated_credit_points_impact: int|null` (nouveau champ requis F45).
- `step_id: UUID` (déjà existant) pour le lien `/plan-action#step-{step_id}`.

Tri : (1) filtrer sur `target_subscore` égal au sous-score le plus faible du score courant (clarification Q1) ; si moins de 5 actions retournées, élargir aux deux sous-scores les plus faibles ; (2) trier par `estimated_credit_points_impact` desc ; (3) limiter à `N` (défaut 5, max 5).

**Si F45 n'expose pas encore ces deux champs** : la décision est de les ajouter en F45 backend en tant qu'extension non rétro-incompatible (champs optionnels) — à coordonner avec l'équipe F45. Comme garde-fou, le service `list_recommendations` retourne **liste vide** si `target_subscore`/`estimated_credit_points_impact` ne sont pas disponibles (graceful degradation), et le test `test_recommendations_endpoint.py` cas (6) couvre le skip explicite.

**Rationale** :

- Centraliser la sélection côté backend rend le contrat clair et permet des évolutions (filtres temporels, statut « non terminée ») sans toucher l'UI.
- Le helper front `selectCreditRecommendations.ts` reste un filet de sécurité (cas où le backend renvoie >5 par bug ou par bord changé) — conforme à la défense en profondeur.

**Alternatives considered** :

- *Sélection 100 % côté front à partir de `GET /me/plan-action`* : rejeté — couple le scoring à l'implémentation interne du plan d'action ; expose toutes les actions au navigateur et fait la sélection sensible côté client.
- *Endpoint UI-only sans F45 backend* : rejeté — duplique la logique de plan d'action et casse SC-005 (clic redirige vers une étape qui doit exister dans `/plan-action`).

---

## R-05 — Composant gauge : bibliothèque vs implémentation locale

**Decision** : Implémenter `GaugeHero.vue` localement en SVG + gsap. Pas de dépendance nouvelle. Forme : arc de cercle 0-100 (270° sweep, demi-cercle évasé), couleur dérivée du token de la classification courante (4 tokens design system du F36), aiguille animée par tween gsap 320 ms. Texte central = score numérique + classification + delta vs N-1. Texte alternatif daltonien-friendly via `<ClassificationLabel>` adjacent (couleur + libellé toujours visible).

**Rationale** :

- F40 `viz/` n'expose pas de `<VizGaugeChart>` à date (à vérifier dans le repo réel ; si présent, on l'utilise). En son absence, un SVG 50 LOC + animation gsap est largement suffisant pour le besoin.
- chart.js n'a pas de gauge natif sans plugin (`chartjs-gauge`) — éviter d'ajouter une dépendance pour un seul composant.
- 60 fps mobile et desktop atteignable trivialement avec un tween gsap sur un attribut SVG `stroke-dashoffset`.

**Alternatives considered** :

- *`chartjs-gauge` plugin* : rejeté — dépendance peu maintenue, pour un seul composant.
- *D3.js arc* : rejeté — dépendance lourde non utilisée ailleurs dans le projet.
- *Image statique + animation CSS* : rejeté — granularité insuffisante pour un score variable continu.

---

## R-06 — Seuils de classification : duplication front/back ?

**Decision** : Implémentation **côté front uniquement** dans `frontend/app/lib/classifyCreditScore.ts`. Le backend ne renvoie **pas** la classification (ni `bucket`, ni `label`), juste `combine` (déjà existant). Les seuils 80/60/40 (clarification Q2) sont contractualisés dans `contracts/backend-subscores-extension.md` comme « contrat partagé » à respecter en cas d'évolution.

**Rationale** :

- La classification est un libellé d'UI, pas une donnée métier persistée — la dupliquer côté backend introduirait une source de vérité concurrente sans bénéfice.
- Le helper est testé exhaustivement aux bornes (`test_classifyCreditScore.test.ts` cas 0/39/40/59/60/79/80/100).
- Si dans le futur les seuils doivent dépendre de la `methodologie_version`, on pourra faire évoluer le helper en lui passant la version courante — sans changement d'API.

**Alternatives considered** :

- *Renvoyer `bucket` et `label` depuis le backend* : rejeté — rigidifie l'i18n (un changement de libellé = release backend).
- *Stocker la classification sur `credit_score`* : rejeté — donnée dérivée de `combine`, viole P6 indirectement (duplication d'information).

---

## R-07 — Saisie monétaire dans le bottom sheet : `Money` typé sur `POST /me/credit-data`

**Decision** : Le payload de `POST /me/credit-data` (kind=`declaratif`) accepte un `payload: dict[str, Any]` libre côté F29. Pour F48, le contrat front s'engage à envoyer chaque montant sous la forme :

```json
{"chiffre_affaires": {"amount": "12500000", "currency": "XOF"}, "ebe": {...}, "dette": {...}, "fonds_propres": {...}}
```

`amount` est une **string** (`Decimal.toString()`) pour préserver la précision côté JSON. Côté UI, `<UiNumber money>` (F37) émet `Decimal` via `decimal.js` ; la sérialisation conserve la précision en string. Côté backend F29, le service `submit_credit_data` stocke tel quel dans `payload_json` (JSONB) et le scoring engine convertit string→Decimal avant calcul (déjà robuste si F29 le fait via `decimal.Decimal(str(value))`).

**Rationale** :

- P5 imposé par la constitution : pas de `float`. Le format `{amount: str, currency: str}` est le standard Money du projet (utilisé par `MoneyOut` ailleurs).
- Compatible avec le schéma `dict[str, Any]` actuel — pas de changement de F29.
- Le wizard et le bottom sheet partagent le même format.

**Alternatives considered** :

- *Étendre `CreditDataIn` avec un schéma typé `FinancialDeclaratifPayload`* : rejeté pour MVP F48 (changement de contrat F29) ; à proposer en hardening post-MVP.
- *Envoyer les montants en `float`* : interdit par P5.

---

## R-08 — Mode wizard empty-state : persistance localStorage + reprise

**Decision** : Le wizard 4 étapes (Financier→ESG→Gouvernance→Récap) persiste les réponses partielles dans `localStorage` sous la clé `credit-score-wizard-{account_id}-{entreprise_id}`. Reprise automatique à l'ouverture si une session est en cours ET datée < 7 jours (TTL court pour éviter les zombies). À la soumission finale, l'entrée localStorage est effacée. Si la session est >7 jours, l'utilisateur est invité à recommencer.

**Rationale** :

- US8 AS2 + edge case « wizard interrompu » exigent la reprise sans perte ; localStorage est suffisant pour un wizard de quelques minutes (NFR-002 / SC-006 : <3 min).
- Aucun appel backend tant que la dernière étape n'est pas validée → pas de demi-écriture côté DB.
- Clé scopée par `account_id+entreprise_id` permet le multi-tenant côté navigateur (cas multi-comptes).

**Alternatives considered** :

- *Backend draft endpoint* : rejeté pour MVP — ajoute des endpoints, des migrations, et de la complexité pour une session de 3 minutes.
- *sessionStorage* : rejeté — perdu à la fermeture d'onglet, ce qui casse l'UX si la PME ferme par accident.

---

## R-09 — Synchronisation chat ↔ credit-score : événements écoutés et émis

**Decision** :

| Événement | Émetteur | Récepteur | Action |
|--|--|--|--|
| `entity_updated{credit_data}` | chat F41, bottom sheet F48, wizard F48 | F48 store + chat F41 | invalider `credit_data` + déclencher `recompute` automatique côté backend |
| `entity_updated{credit_score}` | F29 service après recompute | F48 store, chat F41, dashboard F44 | recharger le score courant + animer la gauge (`animateGaugeTransition`) + rafraîchir sous-scores + éligibilité + recommandations |
| `entity_invalidated{credit_eligibility}` | aucun direct | F48 store | invalidation passive (cache 60 s sur `useCreditEligibility`) — déclenchée si le catalogue change (post-déploiement, hors MVP) |

Le contrat est documenté dans `contracts/chat-eventbus-sync.md`.

**Rationale** :

- Pattern strictement aligné sur F46/F47, garantissant la cohérence d'expérience.
- L'invalidation est ciblée (pas de full-refresh) pour préserver les animations gsap en cours.
- Le recompute après mutation `credit_data` est déclenché côté backend (F29 le fait déjà dans `submit_credit_data` → `recompute_score` ?) — à vérifier ; sinon, l'UI déclenche elle-même `POST /me/credit-score/recompute` après `POST /me/credit-data`.

**Alternatives considered** :

- *Polling toutes les 30 s* : rejeté — gaspille la bande passante et casse la fluidité des animations.
- *WebSocket dédié* : rejeté — l'EventBus chat existant suffit, pas besoin d'ouvrir un canal nouveau.

---

## R-10 — Accessibilité daltonien

**Decision** : `<ClassificationLabel>` affiche **toujours** le libellé textuel de la classification (« Excellent »/« Bon »/« À améliorer »/« Insuffisant ») à côté du visuel coloré. Le composant `GaugeHero` n'utilise jamais la couleur seule comme porteuse d'information. Les badges d'éligibilité incluent une icône (chèck/croix) + texte. Le test E2E `credit-score-color-blind-friendly.spec.ts` applique un filtre CSS `grayscale(1)` à la page et vérifie que toutes les informations critiques restent identifiables.

**Rationale** : conforme WCAG 2.1 AA (1.4.1 Use of Color), exigé implicitement par FR-015 et explicitement par les Risques/points de vigilance du brief.

**Alternatives considered** :

- *Mode haut contraste séparé* : reporté post-MVP — la stratégie « texte + couleur » couvre la majorité des cas d'usage daltoniens et ne nécessite pas d'écran dédié.

---

## Synthèse des décisions

| ID | Sujet | Décision résumée |
|--|--|--|
| R-01 | Mapping factor → bucket sous-score | Backend pure data `subscore_mapping.py`, calcul à la volée |
| R-02 | Catalogue éligibilité | Pure Python `eligibility_catalog.py` versionné, source_id par dispositif |
| R-03 | Endpoint historique | `GET /me/credit-score/history?limit=N` ∈[1..24], défaut 6 |
| R-04 | Recommandations | Endpoint backend lit F45 ; F45 doit exposer `target_subscore` + `estimated_credit_points_impact` |
| R-05 | Gauge | SVG + gsap local, pas de nouvelle dépendance |
| R-06 | Seuils classification | Front-only, helper `classifyCreditScore.ts`, contrat partagé documenté |
| R-07 | Saisies Money | `{amount: str, currency: str}` dans `payload_json` libre F29 |
| R-08 | Wizard persistance | localStorage scopé `account_id+entreprise_id`, TTL 7 jours |
| R-09 | Chat sync | Événements `entity_updated{credit_data, credit_score}` |
| R-10 | Daltonisme | Texte toujours présent + icône, jamais couleur seule |

Tous les `NEEDS CLARIFICATION` initiaux sont résolus. La spec peut maintenant entrer en Phase 1.
