# Contract — Sync EventBus chat ↔ dashboard F44

**Date** : 2026-05-03
**Status** : Phase 1.

## Vue d'ensemble

Le dashboard est **consommateur** d'évènements émis par le chat conversationnel (F41) lors de mutations LLM. Il est aussi **producteur** d'un seul évènement (`action_step:completed`) quand l'utilisatrice coche une étape de plan d'action depuis la carte. La transport est l'`useChatEventBus` existant (mémoire JS in-tab), pas une SSE serveur.

## C-EVT-1 — Évènements consommés (chat → dashboard)

| Event name | Payload (forme) | Bloc invalidé | Action |
|------------|------------------|--------------|--------|
| `scoring:computed` | `{ referentielCode: string, scoreGlobal: string }` | `scores` | `store.invalidate('scores'); store.fetchSummary({ scope: ['scores'] })` |
| `carbon:computed` | `{ year: number, totalTco2e: string }` | `carbon` | idem |
| `credit:computed` | `{ combine: number }` | `credit_score` | idem |
| `candidature:created` | `{ id: string, projetId: string, offreId: string }` | `candidatures` | idem |
| `candidature:status_changed` | `{ id: string, statut: string }` | `candidatures` | idem |
| `rapport:generated` | `{ id: string, entityType: string }` | `rapports` | idem |
| `attestation:emitted` | `{ id: string, publicId: string }` | `attestations` | idem (le bloc 'rapports' VM lit aussi `attestations`, donc on invalide les deux) |
| `action_step:created` | `{ id: string }` | `next_actions` | idem |
| `action_step:completed` | `{ id: string }` | `next_actions` | **ignoré si origine locale** (corrélation par id en mémoire pendant 5 s) ; sinon idem |

**Règle de tolérance** : un event inconnu de cette table est **silencieusement ignoré** (log debug, pas d'erreur). Cela autorise l'ajout d'events futurs sans casser le dashboard.

## C-EVT-2 — Évènement produit (dashboard → chat)

| Event name | Émis par | Payload | Effet attendu côté chat |
|------------|----------|---------|-------------------------|
| `action_step:completed` | `CardActionPlan` après PATCH réussi | `{ id: string, source: 'dashboard' }` | Le chat ouvert (s'il y en a un) invalide son contexte plan d'action pour le prochain tour LLM. La cascade backend (P8 — invalidation côté F31) reste la source de vérité. |

## C-EVT-3 — Garde-fou : pas de re-fetch en boucle

Si une mutation locale déclenche immédiatement un PATCH backend qui (à son tour) émet l'event chat correspondant via SSE, le dashboard pourrait se retrouver à fetcher deux fois (optimistic + event). Pour éviter cela :

1. `useChatEventBus` permet d'attacher une **propriété `source: 'dashboard' | 'chat' | 'backend'`** sur chaque event.
2. `useDashboardSummary` ignore les events portant `source === 'dashboard'` quand le payload `id` correspond à une mutation locale tracée dans une `Set<string>` à TTL 5 s.
3. Si l'event vient du backend (via SSE F41 hypothétique) ou d'un autre onglet/chat, il sera bien consommé.

## C-EVT-4 — Détachement / cleanup

`useDashboardSummary` :
- enregistre des handlers via `bus.on(eventName, handler)` au mount,
- détache via `bus.off(eventName, handler)` à l'unmount,
- ce contrat évite les fuites mémoire en cas de navigation rapide entre `/dashboard` et `/chat`.

## C-EVT-5 — Test contractuel

Le test unitaire `useDashboardSummary.test.ts` doit vérifier :

1. À l'émission de `scoring:computed`, `store.fetchSummary` est appelé exactement 1 fois avec `scope: ['scores']`.
2. À l'émission de `attestation:emitted`, `store.fetchSummary` est appelé avec `scope: ['rapports', 'attestations']` (les deux, car la carte rapports affiche aussi les attestations).
3. À l'émission d'un event inconnu, `store.fetchSummary` n'est pas appelé.
4. Aux events avec `source: 'dashboard'` et id local, le re-fetch est sauté.

Le test E2E `dashboard-chat-sync.spec.ts` doit :

1. Ouvrir `/dashboard`, valider la valeur de la carte ESG (ex. 60).
2. Simuler dans le même onglet (via window event de test) un `scoring:computed` avec `scoreGlobal: '75'`.
3. Mocker `/me/dashboard/summary` pour renvoyer `score_global: '75'` au prochain appel.
4. Vérifier que la carte ESG affiche 75 en moins de 2 s.
