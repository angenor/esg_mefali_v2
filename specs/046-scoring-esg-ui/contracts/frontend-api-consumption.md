# Contract — Frontend API Consumption (F46)

Toutes les requêtes émises par la page `/scoring` et ses composants. Aucune n'est bricolée côté front : chacune passe par un service `services/api/scoring.ts` (à créer en miroir de `services/api/action-plan.ts` F45) qui encapsule `$fetch` Nuxt + propagation du JWT.

## 1. `GET /me/scoring/{entity_type}/{entity_id}` — F23 (existant)

**Quand** : au mount de la page `/scoring` ou du `dashboard` (mini-card).
**Réponse** : `ScoreListOut` ; alimente `summariesByRef` du store.

## 2. `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}` — F23 (existant)

**Quand** : à la sélection d'un référentiel (mount sous-page `/scoring/[code]`) ; au cache miss (TTL 60 s).
**Réponse** : `ScoreDetailOut` ; alimente `detailsByRef[code]`.

## 3. `POST /me/scoring/{entity_type}/{entity_id}/recompute?referentiel={code}` — F23 (existant)

**Quand** : (a) clic « Recalculer » (US7), (b) après une édition d'indicateur réussie (US4), (c) automatiquement au mount si `summariesByRef[currentRef]` est manquant (lazy first-compute uniquement si le user clique « Lancer mon premier diagnostic »).
**Réponse** : `ScoreDetailOut` (le nouveau snapshot persisté) ; remplace `detailsByRef[code]` ; pousse une nouvelle entrée dans `historyByRef[code]` au début (ou re-fetch).

## 4. `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}/history?limit=12` — **F46 (nouveau)**

Voir `contracts/backend-history-endpoint.md`.

## 5. `PATCH /me/entreprise` — F11 (existant)

**Quand** : à la validation du bottom sheet `ask_number` pour un indicateur **éditable** (US4).
**Body** : payload partiel selon `SCORING_INDICATEUR_TO_ENTREPRISE_PATH` (voir `data-model.md` §5.2). Exemples :

- `EFFECTIFS_TOTAL` → `{ "taille_effectifs": 120 }`
- `CA_AMOUNT` → `{ "taille_ca_amount": { "amount": "5000000", "currency": "XOF" } }`
- `GOUVERNANCE_BOARD_INDEPENDENCE` → `{ "gouvernance_json": { "board_independence": true } }` (merge via service F11 — vérifier que F11 supporte le merge JSONB partiel ; sinon, le composable lit la valeur courante via `useEntrepriseProfile`, applique le diff, et envoie l'objet complet).

**Réponse** : `EntrepriseRead` ; le composable n'utilise pas la réponse, mais déclenche immédiatement (3) pour rafraîchir le score.

## 6. `GET /me/sources/{source_id}` — F07 (existant via `useSourceFetch`)

**Quand** : rendu d'une `IndicateurRow` ou de `<VizSourcePin>` ; lecture du statut `verified | revoked` pour décider du badge.
**Cache** : 5 minutes (déjà implémenté par `useSourceFetch`).

## 7. (P2) `POST /me/rapports/scoring/export` — F51 (à confirmer)

**Quand** : clic « Exporter PDF ».
**Body** : `{ entity_type, entity_id, referentiel_code, score_calculation_id?: string }` (présent en mode snapshot).
**Réponse** : `application/pdf` (binaire) ; téléchargement direct via `<a download>`.
**Statut** : si l'endpoint n'existe pas encore au moment du build F46, le bouton `<ExportPdfButton>` est rendu **désactivé** + tooltip explicatif (voir `research.md` R11).

## 8. Évènements WebSocket / SSE

Aucune connexion directe. Toute synchronisation passe par le bus `useChatEventBus` (voir `contracts/chat-eventbus-sync.md`).

---

## Headers et erreurs communes

- Toutes les requêtes utilisent l'helper Nuxt `$api` (ajoute `Authorization: Bearer <jwt>`, `Accept-Language: fr`, `X-CSRF-Token` quand applicable).
- 401 → toast « Session expirée » + redirection `/login`.
- 403 → toast « Action non autorisée ».
- 404 / 422 → message contextualisé dans le composant (drawer ou page).
- 5xx → toast « Erreur serveur » + bouton « Réessayer ».
