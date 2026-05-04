# Research — F46 Scoring ESG visualisations UI

**Date** : 2026-05-04
**Phase** : 0 (Outline & Research)

Aucun marqueur `[NEEDS CLARIFICATION]` dans `spec.md` ; cette page documente les **décisions techniques** prises avant la phase 1 et les alternatives écartées. Toutes les décisions ont pour cadre la constitution v1.0.0 et la stack imposée (Nuxt 4 + FastAPI + Postgres/pgvector + chart.js + gsap + chat F41).

---

## R1 — Endpoint historique (`GET .../history`)

**Décision** : ajouter une route `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}/history?limit=12` qui lit la table append-only `score_calculation` (déjà créée par F23) en filtrant `account_id` (RLS) + `entity_type` + `entity_id` + `referentiel_id` (joint via `referentiel_code`), trie `computed_at DESC`, limite par `limit` (default 12, max 50). Schéma `ScoreHistoryOut = list[ScoreHistoryEntry]` où chaque entry porte `computed_at`, `score_global`, `referentiel_version`, `score_calculation_id`.

**Rationale** :

- US7 (historique 12 derniers points), US8 (snapshot freeze sur un calcul historique), drawer indicateur (graphique linéaire 12 mois) ne peuvent pas être satisfaits sans cette donnée.
- La table existe déjà (`backend/app/models/score_calculation.py`), append-only et audit-friendly par construction (P3 respecté ; pas d'audit additionnel pour une lecture).
- L'endpoint reste cohérent avec l'arborescence F23 (`/me/scoring/{entity_type}/{entity_id}/{referentiel_code}`) : ajouter un sous-chemin `/history` est la convention REST la moins disruptive.
- 100 % RLS-aware : la query SQL inclut `account_id = :acc` ; cross-tenant retourne 404 (testé).

**Alternatives écartées** :

1. Charger l'historique par lecture multiple de `GET .../{referentiel_code}` avec un paramètre temporel : impossible, l'endpoint actuel ne retourne que le dernier calcul.
2. Construire l'historique côté front en accumulant les `ScoreDetailOut` reçus à chaque visite : faux, n'existe pas si l'utilisateur ouvre la page après plusieurs jours.
3. Exposer `score_calculation` via un endpoint admin générique : violerait P2 (RLS) et le scope PME.

**Forme du contrat** (détaillée dans `contracts/backend-history-endpoint.md`) :

```python
# backend/app/scoring/schemas.py — ajout
class ScoreHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score_calculation_id: uuid.UUID
    computed_at: datetime
    score_global: float | None
    referentiel_version: int

class ScoreHistoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_type: str
    entity_id: uuid.UUID
    referentiel_code: str
    entries: list[ScoreHistoryEntry] = Field(default_factory=list)
```

```python
# backend/app/scoring/service.py — ajout
def list_history(
    db: Session,
    *,
    account_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
    limit: int = 12,
) -> list[dict]: ...
```

`limit` est borné à `[1, 50]` ; au-delà → 422.

---

## R2 — Édition d'un indicateur depuis le drawer (US4) — sans nouveau pivot

**Décision** : conserver le **pivot Indicateur** côté backend (F23 résout les valeurs depuis `entreprise` via `VALUE_SOURCE_MAP`). L'édition d'un indicateur depuis le drawer écrit le **champ entreprise** correspondant (route F11 `PATCH /me/entreprise` existante), puis la page déclenche `POST /me/scoring/.../recompute` pour rafraîchir le score. Un mapping miroir manuel (`lib/scoringEditableIndicateurs.ts`) liste les indicateurs effectivement éditables depuis cette UI au MVP (= clés présentes dans `VALUE_SOURCE_MAP` côté backend).

**Rationale** :

- Cohérent avec P6 (Pivot Indicateur unique) : on ne crée pas de table de valeurs d'indicateur ; la valeur reste sur le profil entreprise.
- Cohérent avec P8 (édition manuelle ↔ sync LLM) : la PATCH F11 émet déjà l'évènement chat sur le bus + invalide le contexte LLM ; le recompute se chaîne après.
- Cohérent avec P3 (audit) : la PATCH F11 trace `source_of_change='manual'` automatiquement.
- Évite tout changement de modèle de données et tout risque de duplication.

**Limitation MVP documentée** : un indicateur **non présent** dans `VALUE_SOURCE_MAP` (p.ex. un nouvel indicateur catalogue qui n'a pas encore été câblé sur un champ entreprise) ne peut pas être édité depuis le drawer ; le bouton « Modifier » affiche alors un message « Cet indicateur ne peut pas être édité directement ici ; ouvrez la conversation pour le compléter » avec CTA chat. Cette restriction est gérée par `scoringEditableIndicateurs.ts` qui DOIT être tenu en sync avec le backend (changement de `VALUE_SOURCE_MAP` → MAJ du miroir TS et test de cohérence).

**Alternatives écartées** :

1. Créer une table `indicateur_value` indépendante : violerait P6, doublon avec `entreprise`.
2. Ajouter un endpoint générique `PATCH /me/indicateurs/{code}` côté backend : aurait nécessité une nouvelle abstraction et un nouveau modèle d'audit ; non requis pour le MVP F46.
3. Inférer dynamiquement le mapping côté front via un endpoint catalogue : surdimensionné pour le MVP ; le mapping change rarement.

**Test de cohérence** : `frontend/tests/unit/lib/scoringEditableIndicateurs.test.ts` lit la liste hardcodée et vérifie qu'elle contient au moins les clés MVP attendues (`EFFECTIFS_TOTAL`, `CA_AMOUNT`, `PAYS_SIEGE`, `GOUVERNANCE_BOARD_INDEPENDENCE`, etc.). Si le backend ajoute des entrées dans `VALUE_SOURCE_MAP`, un commentaire de tâche dans `tasks.md` rappelle la double mise à jour.

---

## R3 — Radar vs Bar chart (≥ 7 axes)

**Décision** : la vue d'ensemble utilise `<VizRadarChart>` lorsque le référentiel a **3 à 6 piliers/axes** (cas BOAD/CDP/GRI standard avec E/S/G), et bascule automatiquement sur `<VizBarChart>` vertical lorsque le référentiel a ≥ 7 axes (cas ODD-aligné qui peut atteindre 17 axes). La bascule est calculée à partir du nombre de clés non-nulles dans `scores_by_pillar`.

**Rationale** :

- Au-delà de 6 axes, un radar devient illisible (chevauchement, étiquettes en collision). Le brief F46 le mentionne explicitement.
- `<VizBarChart>` vertical permet d'afficher 17 axes proprement avec libellés en bas.
- Aucun nouveau composant nécessaire — F40 fournit les deux primitives.

**Alternatives écartées** :

1. Toujours radar (option par défaut chart.js) : illisible sur ODD.
2. Sliding-window radar (5 axes affichés à la fois) : interaction parasite, peu clair pour le décideur.

---

## R4 — Mode snapshot (US8) — freeze UI vs duplication

**Décision** : le mode snapshot est **un état UI** (drapeau `isSnapshot` dans le store + `frozen_calculation_id`). Quand activé, le store (a) substitue les données live par les données figées d'un `score_calculation_id` historique récupéré via le nouvel endpoint history (qui ne retourne que les sommaires) puis re-fetch le détail figé via `GET .../{referentiel_code}` paramétré pour ce calcul (voir R5), (b) désactive les actions de mutation (`Modifier`, `Recalculer`) au niveau du composant (props/computed `disabled`), (c) cache le bandeau « état courant » et affiche un bandeau « SNAPSHOT du JJ/MM/AAAA — version v.X » non dismissible.

**Rationale** :

- Aucun stockage parallèle (P4 : la table `score_calculation` est déjà un snapshot par construction).
- Conforme P4 (versioning) : la `referentiel_version` figée s'affiche partout.
- Pas de risque de mutation accidentelle car les actions sont désactivées au niveau du composant et **non** simplement masquées (test e2e dédié `scoring-snapshot-freeze.spec.ts`).

**Alternatives écartées** :

1. Server-side mode (param `?at=<calculation_id>` sur les routes) : nécessiterait modifier toutes les routes existantes F23 ; surdimensionné.
2. Cloner les données dans un store séparé : duplication inutile.

---

## R5 — Récupération du détail figé d'un calcul historique

**Décision** : l'endpoint `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}` retourne déjà le **dernier** détail. Pour récupérer un détail historique précis (snapshot), nous **n'ajoutons pas** d'endpoint additionnel au MVP : la vue snapshot affiche uniquement le sommaire historique (score global, scores par pilier, version) tel que retourné par l'endpoint history, **pas** la liste détaillée des indicateurs couverts/manquants à ce moment-là. La vue d'ensemble (radar + KPI) reste fidèle ; le drilldown indicateur est désactivé en mode snapshot avec un message « Le détail des indicateurs n'est disponible qu'en mode courant ».

**Rationale** :

- Au MVP, le besoin principal du snapshot est l'archivage / l'audit du **score**, pas la rejouabilité fine indicateur par indicateur.
- Évite d'élargir le contrat de l'endpoint detail F23 (paramètre `at` ou `id`) qui aurait des implications RLS, perf et test importantes.
- Documenté dans la spec (US8 : « fige la vue sur cet état (scores, indicateurs, sources, version) »). On ajuste légèrement la promesse au MVP : la vue d'ensemble est figée et auditable (radar + KPI + version + date) ; le drilldown indicateur est disponible uniquement en mode courant. Le PDF (P2) inclura la même portée.
- Post-MVP : un endpoint `GET .../calculation/{id}` permettra le détail historique complet.

**Alternatives écartées** :

1. Étendre l'endpoint detail F23 avec un paramètre `?calculation_id=` : viable, mais non requis pour le MVP ; reporté.
2. Stocker le `snapshot_json` complet dans `score_calculation` : déjà partiellement le cas via `indicateurs_couverts` (jsonb) — mais l'exposer via un nouvel endpoint serait identique au choix précédent et reste post-MVP.

---

## R6 — Comparaison multi-référentiels (US3)

**Décision** : implémentée **côté client uniquement**. Le composable `useScoringCompare` lit la liste des derniers scores via `GET /me/scoring/{entity_type}/{entity_id}` (qui retourne déjà tous les référentiels), filtre les référentiels sélectionnés par l'utilisateur, et fournit une projection `{ referentiel_code, score_global, scores_by_pillar }[]` que `<VizBarChart>` consomme directement (mode horizontal, dataset par référentiel).

**Rationale** :

- Aucune nouvelle route backend.
- Très peu de payload (≤ 5 référentiels × ≤ 6 piliers).
- Lecture déjà cachée dans le store ; switch instantané.

**Alternatives écartées** :

1. Endpoint `/compare?codes=BOAD,CDP` côté backend : utile en théorie, mais ferait double emploi avec `list_scores` qui retourne déjà tous les scores latest pour l'entité.

---

## R7 — Synchronisation EventBus chat ↔ scoring (US11)

**Décision** : le store `scoring.ts` s'abonne (via `useChatEventBus`) à deux familles d'évènements émis par F41 :

- `entity_updated{entity_type='indicateur', entity_id=<uuid>, source='chat'|'tool'}` → invalidation ciblée du **détail courant** (re-fetch `GET .../{referentiel_code}`) + **historique** (re-fetch `GET .../history`). Pas d'invalidation des autres référentiels (sauf si l'indicateur est partagé — au MVP on invalide tous les référentiels chargés pour rester simple, ce qui se traduit par un re-fetch de la liste light `GET /me/scoring/{entity_type}/{entity_id}`).
- `entity_updated{entity_type='score_calculation', entity_id=<uuid>, source='tool'}` → re-fetch du détail courant + historique (un nouveau calcul est apparu).

À l'inverse, le store **émet** sur le bus :

- Après PATCH entreprise + recompute : `entity_updated{entity_type='indicateur', source='manual'}` puis `entity_updated{entity_type='score_calculation', source='manual'}`.
- Après recompute manuel (US7) : `entity_updated{entity_type='score_calculation', source='manual'}`.

**Rationale** :

- Aligné avec le pattern F44/F45 (`useDashboardBus`, `useChatEventBus`).
- Invalidations ciblées (jamais un re-fetch global multi-tenant).
- La direction des évènements respecte P8 (sync bidirectionnelle, DB source de vérité).

**Alternatives écartées** :

1. WebSocket dédié au scoring : surdimensionné, le bus chat suffit (déjà dans la stack F41).
2. Polling périodique : violerait NFR-002 (LCP) et la frugalité réseau attendue en Afrique de l'Ouest.

---

## R8 — Pastille source révoquée (FR-017, edge case)

**Décision** : un nouveau composant `<RevokedSourceBadge>` (composé de `<UiBadge variant="warning">` + `<UiTooltip>`) remplace `<VizSourcePin>` dans la `IndicateurRow` lorsque la `Source` référencée par `source_id` a un `status='revoked'`. La valeur est affichée en `text-gray-400 line-through`. Le composant `<VizSourcePin>` reçoit donc un prop `source` (chargé via `useSourceFetch` existant) ; en cas de révocation, il rend `<RevokedSourceBadge>`.

**Rationale** :

- L'information de révocation est déjà disponible côté backend (P3 audit + F07 catalogue sources). Le front doit simplement la lire et l'afficher.
- Ne casse aucun contrat existant : `<VizSourcePin>` continue de fonctionner pour les sources `verified`.

**Alternatives écartées** :

1. Masquer entièrement la valeur : surinterprétation, l'utilisateur doit voir qu'une valeur existait mais n'est plus probante.
2. Bloquer le calcul du score : décision backend (F23) ; côté UI, on se contente d'afficher.

---

## R9 — Performance : 50+ indicateurs sans virtualisation

**Décision** : pas de virtualisation au MVP. Pour atteindre LCP < 2 s avec 50+ indicateurs :

- L'accordéon E/S/G est rendu mais les `<VizLineChart>` (historique 12 mois) ne sont **créés qu'à l'ouverture du drawer** (`v-if="drawerOpen"`).
- Les `<VizSourcePin>` chargent les sources en lazy (`useSourceFetch` avec cache de 5 min déjà en place).
- Les rangs initialement repliés (`<details>` natif Tailwind) ne montent pas leurs enfants via `v-show=false` mais via le comportement natif `<details>` (pas de pré-rendu).
- Le radar est servi par `<VizRadarChart>` qui utilise déjà `chart.js` (canvas, performant).

**Si > 30 indicateurs sur un pilier** : ajout d'un seuil de 30 lignes affichées par défaut + bouton « Voir les N restants » qui révèle le reste. Pas de virtualisation Vue côté MVP. Mesuré en e2e (`scoring-overview-render.spec.ts`).

**Alternatives écartées** :

1. `vue-virtual-scroller` : ajout de dépendance et de complexité a11y ; non justifié pour un cap de 200 indicateurs.

---

## R10 — Intégration F44 (CardScoringSummary du dashboard)

**Décision** : modifier `frontend/app/components/dashboard/CardScoringSummary.vue` (livré par F44) pour qu'il **lise** `useScoringStore` au lieu de fetcher en propre. Le store est instancié au mount du dashboard (état `current_score_summary` rempli par `GET /me/scoring/{entity_type}/{entity_id}` avec le référentiel par défaut). Quand l'utilisateur clique « Voir le scoring complet », il navigue vers `/scoring` et le store contient déjà le sommaire ; le détail est fetché à l'arrivée sur la page si pas déjà en cache.

**Rationale** :

- Cohérence : une seule source de vérité côté front pour le scoring.
- Performance : pas de double fetch dashboard → /scoring.
- Pattern reproduit de F45 (`CardActionPlan` / `useActionPlanStore`).

**Alternatives écartées** :

1. Laisser `CardScoringSummary` fetcher en propre : double appel inutile, état désynchronisable.

---

## R11 — Export PDF (US9 / P2)

**Décision** : reportée à F51 (Rapports). Au MVP F46 on ajoute le composant `ExportPdfButton.vue` qui appelle l'endpoint d'export PDF (à confirmer côté F51) avec en payload `referentiel_code`, `entity_type`, `entity_id`, et optionnellement `score_calculation_id` si mode snapshot. Tant que F51 n'est pas livré, le bouton est rendu **désactivé** avec un tooltip « Export disponible dans la prochaine version ».

**Rationale** :

- Évite de créer un blocage F46 → F51.
- Le composant reste prêt pour activation par feature flag.

**Alternatives écartées** :

1. Implémenter l'export PDF directement dans F46 via `puppeteer`/`weasyprint` : hors scope, ferait doublon avec F51 prévu.

---

## R12 — Tests e2e : seed minimal

**Décision** : créer un fixture Playwright `frontend/tests/e2e/fixtures/scoring-seed.ts` qui (a) authentifie un compte PME de test, (b) appelle `POST /me/entreprise` pour pré-remplir des champs déclencheurs (`taille_effectifs=120`, `taille_ca_amount={amount: 5_000_000, currency: 'XOF'}`, `gouvernance_json={board_independence: true, audit_interne: false}`, `pratiques_actuelles_json={politique_rse: true, bilan_carbone: false}`), (c) appelle `POST /me/scoring/entreprise/{me}/recompute?referentiel=BOAD` puis idem CDP et GRI, ce qui produit un état déterministe : 3 référentiels couverts + plusieurs indicateurs manquants + au moins un calcul historique. Une seconde série de mutations + recompute génère 2 calculs historiques par référentiel pour les tests d'historique et de snapshot.

**Rationale** :

- Pas de manipulation SQL directe en e2e (RLS oblige).
- Reproductible et indépendant des seeds applicatifs.
- ~3 s par test de setup, acceptable.

---

## R13 — Accessibilité du radar

**Décision** : le `<VizRadarChart>` rend en complément un tableau `<table>` masqué visuellement (`sr-only`) listant chaque axe et son score, pour les lecteurs d'écran. Le composant est déjà compatible (F40 — vérifier `aria-label`). Sinon, ajouter le tableau dans `ScoreOverview.vue` à côté du radar.

**Rationale** :

- WCAG 2.1 AA : un canvas n'est pas accessible nativement, le tableau invisible est la pratique standard.
- Aucun nouvel outil ; HTML pur.

---

## Récapitulatif des artefacts générés en Phase 1

- `data-model.md` — ViewModels UI, entités piliers, snapshot, comparaison.
- `contracts/backend-history-endpoint.md` — contrat OpenAPI du nouvel endpoint history.
- `contracts/frontend-api-consumption.md` — contrats des endpoints F23 + F11 consommés.
- `contracts/frontend-components.md` — props/events/slots de chaque nouveau composant.
- `contracts/chat-eventbus-sync.md` — détail des évènements chat ↔ scoring.
- `quickstart.md` — procédure de test local de bout en bout.
