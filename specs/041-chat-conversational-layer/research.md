# Research — F41 Chat Conversational Layer

Toutes les questions ouvertes du plan sont résolues ici. Aucun marqueur `NEEDS CLARIFICATION` ne subsiste.

## R1. Consommation SSE — `EventSource` vs `fetch` + `ReadableStream`

**Decision** : `fetch` + `ReadableStream` + parsing manuel des frames SSE (`data:` / `event:` / `id:` / lignes vides).

**Rationale** :
- L'endpoint backend `POST /me/chat/threads/{id}/messages` (`backend/app/chat/api.py`) renvoie `media_type="text/event-stream"` mais sur la méthode **POST** (et avec en-têtes `Authorization` + cookies CSRF requis par notre middleware).
- La spec brouillon mentionnait `GET /me/chat/threads/{id}/stream` ; la réalité backend est différente — la requête EST le POST du message. Implémenter `EventSource` (GET only, pas d'en-têtes custom, pas de body) imposerait soit un endpoint GET supplémentaire avec `?content=` (mauvaise idée : taille URL, exposition logs), soit un cookie token (déjà en place via session) mais toujours pas de body.
- `fetch` + `ReadableStream` + `TextDecoderStream` couvre POST + en-têtes + body JSON + streaming. Pattern bien éprouvé (utilisé par les SDK OpenAI/Anthropic côté client).
- Reconnect backoff 1/2/4 s est implémenté manuellement par `useChatStream` ; déduplication via `sequence_id` envoyé dans chaque event `token`.

**Alternatives rejetées** :
- `EventSource` natif → incompatible POST + headers custom.
- WebSocket → complexité backend disproportionnée pour un flux unidirectionnel ; non aligné avec FastAPI actuel.
- Long polling → latence du premier token > 500 ms incompatible avec SC-001.

**Implémentation clé** :
```ts
// useChatStream.ts (squelette pseudo-code)
const reader = (await fetch(url, {method: 'POST', headers, body}))
  .body!.pipeThrough(new TextDecoderStream()).getReader()
let buf = ''
while (true) {
  const { value, done } = await reader.read()
  if (done) break
  buf += value
  for (const frame of extractFrames(buf)) {
    if (seenSeq.has(frame.id)) continue
    seenSeq.add(frame.id); dispatch(frame)
  }
}
```

## R2. Rendu Markdown tolérant aux fragments en streaming

**Decision** : `markdown-it ^14` avec parser appelé sur **chaque token reçu** sur le buffer cumulé, output passé à `DOMPurify.sanitize` avec allow-list serrée avant injection via `v-html`.

**Rationale** :
- `markdown-it` est tolérant aux Markdown malformés : `**bold` non fermé est rendu littéralement (pas de crash), puis correctement formaté quand le `**` de fermeture arrive.
- Re-parser à chaque token est négligeable côté CPU pour des bulles ≤ ~5 KB texte.
- Allow-list DOMPurify : `p, br, strong, em, code, pre, ul, ol, li, h1-h6, table, thead, tbody, tr, th, td, a (href https only, rel=noopener), blockquote, sup, span (class allowlist : citation, mermaid-block)` ; **interdits** : `script, iframe, object, embed, style, form, input, link, meta, on*` attributes, `javascript:` URIs, `data:` URIs (sauf images blanc-listées si jamais — non requis MVP).

**Alternatives rejetées** :
- `marked` : moins permissif sur fragments non clos, requiert mode strict.
- Rendre seulement à la fin du stream : casse l'effet token-by-token attendu (SC-001).

**Tests obligatoires** :
- `<script>alert(1)</script>` doit être strippé.
- `<img src=x onerror=alert(1)>` doit perdre `onerror`.
- `[lien](javascript:alert(1))` doit être strippé du `href`.
- `**bold sans fermeture` doit rendre `**bold sans fermeture` puis se reformer quand `**` arrive.

## R3. EventBus client P8 — éviter les boucles

**Decision** : `mitt` (3 KB, zero-dep) + un wrapper `useChatEventBus` qui :
1. relaie les événements `/me/events` SSE (entité mutée) vers les stores Pinia ouverts via subscribe ;
2. ignore les événements portant `source === 'llm'` côté code de re-classification (les pages profil consomment, mais l'orchestrateur LLM ne se rappelle pas) ;
3. expose un `emit('llm_mutation', payload)` interne pour signaler dans la bulle chat qu'une entité a bougé (indicateur sobre US3 scenario 2).

**Rationale** : `mitt` est minimaliste et déjà éprouvé. Le projet n'a pas encore d'event bus partagé — pas de doublon avec une autre lib. Le filtrage par `source` est l'unique safeguard anti-loop nécessaire car le côté backend tague déjà chaque mutation (`source_of_change` audit P3).

**Alternatives rejetées** :
- Pinia subscribe natif uniquement → ne couvre pas les mutations propagées entre tabs sans un bus dédié.
- BroadcastChannel pour cross-tab → utile en V2 mais pas requis MVP (les événements `/me/events` SSE sont reçus par chaque onglet ouvert indépendamment, ce qui suffit).

## R4. Orchestration front input ↔ sheet ↔ stream — LangGraph ou machine maison ?

**Decision** : **Machine à états maison** dans `useChatStore` + `useChatBottomSheet`, **pas** de `@langchain/langgraph` côté front pour MVP.

**Rationale** :
- Le brouillon mentionne LangGraph côté front mais son apport réel ici est limité : 4 états (`idle` → `streaming` → `awaiting_sheet` → `awaiting_validation` → `idle`), 6 transitions. Une machine à états Pinia explicite (~80 LOC) est plus lisible, testable, et évite d'embarquer un orchestrateur LLM côté navigateur (poids bundle, dépendance forte).
- LangGraph côté backend (F14) reste la source d'orchestration LLM ; le front se contente de réagir aux intentions reçues via SSE (`event: tool_invoke`, `event: token`, `event: message_done`).
- Si la complexité monte (graphe non linéaire, arbitrage multi-tools), on basculera sur LangGraph dans une feature dédiée.

**Alternatives rejetées** :
- `@langchain/langgraph` front : surcoût pour 4 états ; couplage front-back inutile.
- XState : robuste mais alourdit le bundle ; sur-ingénierie pour 4 états.

## R5. Onboarding driver.js — flag persisté

**Decision** : flag persisté côté **backend `account_settings.onboarding_chat_seen` (boolean)** si exposé par F11 (profile entreprise) ; **fallback `localStorage` clé `chat.onboarding.seen.{accountId}`** sinon, documenté comme dette technique à résorber dans F11.

**Rationale** :
- La constitution interdit le stockage navigateur comme source de vérité pour des données métier ; un flag d'onboarding est ambigu (UX, pas métier) — `localStorage` borné par `accountId` est acceptable comme fallback temporaire mais le canonique reste DB pour la cohérence multi-device.
- `driver.js ^1.3` (déjà utilisée par F38 selon le plan général) couvre les 4 étapes : popover sur input texte, attache fichier, sidebar, exemple de bottom sheet pré-ouvert puis fermé.

**Alternatives rejetées** :
- Pure `localStorage` : flag perdu si l'utilisateur change de device.
- Réintroduction d'un onboarding « tour » géré par F38 : F41 a un tour spécifique métier (architecture haut/bas) qui n'a pas sa place dans le shell générique.

## R6. Reconnect SSE et déduplication

**Decision** : backoff exponentiel `1s, 2s, 4s, 8s` (cap 8 s, max 5 essais) ; chaque frame SSE porte un `id:` correspondant au `sequence_id` du backend ; côté client, un `Set<sequence_id>` en mémoire évite les doublons. Le backend est invité (research note F12) à inclure systématiquement ce champ — vérifier dans `llm_stream.py` ; sinon ajouter à F12 lors de la phase d'implémentation comme dépendance assumée.

**Rationale** :
- Backoff exponentiel évite tempête de reconnexions si le backend redémarre.
- `sequence_id` côté backend est plus fiable qu'un compteur côté client (le client ne peut pas savoir où il en était sans hint serveur).

**Alternatives rejetées** :
- Backoff linéaire : ré-essais agressifs en cas de panne longue.
- Pas de dedup : risque de tokens doublés visibles côté UI (rupture de confiance).

## R7. Mobile — clavier virtuel + safe area

**Decision** : `MessageInput` utilise `position: sticky; bottom: 0; padding-bottom: env(safe-area-inset-bottom);` dans une page `min-height: 100dvh` (dynamic viewport height) ; le `ChatHistory` se met à `padding-bottom: <hauteur input>` calculé via `ResizeObserver` sur l'input. Cible iOS 15+ et Android Chrome 90+.

**Rationale** :
- `100dvh` corrige les régressions iOS Safari où `100vh` ne tient pas compte de la barre d'URL animée.
- `env(safe-area-inset-bottom)` gère le notch et le home indicator iOS.
- `ResizeObserver` plutôt que valeur figée parce que l'input passe de 1 à 6 lignes en autoresize.

**Alternatives rejetées** :
- `100vh` simple : régressions iOS connues.
- `position: fixed` : recouvre l'historique au lieu de le pousser.

## R8. Choix du store de threads — Pinia, structure

**Decision** : un seul store `useChatStore` :
```ts
state: {
  threads: ChatThreadSummary[]                    // sidebar
  currentThreadId: string | null
  messagesByThread: Record<string, ChatMessage[]> // cache local par thread
  streaming: { threadId, abortController, seqSeen, partial } | null
  forceFreetextNext: boolean                      // re-classification flag
  errors: Record<messageId, ChatError>
}
```

**Rationale** : un store unique pour la chat domain garde la cohérence (un seul endroit pour observer l'état d'envoi, le streaming en cours, la liste des threads, etc.). Subscribe granulaire via `storeToRefs` côté composants.

**Alternatives rejetées** : 3 stores séparés (threads / messages / streaming) → couplage opaque, plus difficile à tester.

## R9. Versions exactes des dépendances à ajouter

| Paquet | Version cible | Pourquoi |
|--------|---------------|----------|
| `markdown-it` | `^14.1.0` | Stable, syntax CommonMark + GFM tables |
| `mitt` | `^3.0.1` | Bus minimaliste éprouvé |
| `driver.js` | `^1.3.1` | Onboarding tour, alignée sur F38 |

`@langchain/langgraph` n'est **pas** ajouté (cf. R4).

## R10. Sécurité — checklist anti-XSS appliquée à F41

- DOMPurify avec config `{ALLOWED_TAGS: [...allowList], ALLOWED_ATTR: [...], FORBID_ATTR: ['style', 'on*'], ALLOW_DATA_ATTR: false}`.
- `href` filtré : seuls `https:` et `mailto:` autorisés ; ajout systématique de `rel="noopener noreferrer"` et `target="_blank"`.
- Aucune utilisation de `v-html` hors `MessageMarkdown.vue` qui passe d'abord par sanitize.
- Aucun `eval`, `Function()`, ou exécution dynamique côté chat.
- CSP : héritée de `nuxt-security` (déjà en place — ne pas affaiblir).

## Verdict global

Toutes les inconnues du plan sont résolues. Aucune NEEDS CLARIFICATION. La feature est prête pour la phase Design.
