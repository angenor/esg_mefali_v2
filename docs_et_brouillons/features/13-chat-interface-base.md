# F13 — Interface Chat Multimodale & Contexte de Page

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 1.1 (Interface de Chat Multimodale) — partie UI/persistance/contexte
**Dépendances** : F02, F04
**Estimation** : 2 jours

## Contexte et objectif

Le chat est **la porte d'entrée principale** de la plateforme : pas de formulaires complexes, tout se fait conversationnellement. Cette feature pose le **chat flottant accessible depuis toutes les pages**, l'historique persistant, le contexte de page, et la **réactivité temps réel** (quand le LLM modifie une donnée affichée, l'UI se met à jour sans reload).

F13 ne livre **pas** les tools (réponse, visualisation, mutation, mémoire) — ceux-ci viendront en F14, F15, F16, F17, F18. F13 livre la coquille conversationnelle robuste sur laquelle les autres briques se brancheront.

## User Stories

### US1 — Chat flottant accessible depuis toutes les pages (P1)
**En tant que** PME,
**je veux** un bouton flottant en bas à droite (cohérent design system) qui ouvre une fenêtre de chat persistante au-dessus du contenu,
**afin de** pouvoir poser une question à n'importe quel moment.

**Test indépendant** : naviguer entre 3 pages (`/profil/entreprise`, `/profil/projets`, `/`) → le chat reste accessible, l'état (ouvert/fermé) est persisté en localStorage, l'historique est conservé.

### US2 — Historique de conversation persistant (P1)
**En tant que** PME,
**je veux** que mes échanges avec le LLM soient sauvegardés en base de données et rechargeables à chaque connexion,
**afin de** ne rien perdre.

**Scénarios** :
1. Première session : conversation vide.
2. Session suivante (même user, même PME) : reprise de la conversation précédente avec scroll en bas.
3. Bouton "Nouvelle conversation" : démarre un nouveau thread (l'ancien reste consultable dans la liste des threads).

### US3 — Le LLM connaît la page courante (P1)
**En tant que** PME,
**je veux** que quand je suis sur `/profil/projets/[id]` et que je dis "ajoute un indicateur d'impact", le LLM comprenne implicitement que je parle DE CE projet,
**afin de** ne pas avoir à toujours préciser le contexte.

**Mécanisme** : le frontend envoie à chaque message un objet `{page: '/profil/projets', entity_type: 'projet', entity_id: 'xxx', selection?: 'champ_indicateurs_impact'}`. Le backend l'injecte dans le contexte LLM (via F18/F14). Cette feature livre **l'envoi du contexte**, pas son traitement par LangGraph (F14).

### US4 — Mise à jour réactive temps réel (P1)
**En tant que** PME,
**je veux** que si le LLM modifie un champ via un tool de mutation (F17), je voie le changement à l'écran immédiatement (pas après reload),
**afin de** que la conversation et l'UI restent synchronisées.

**Mécanisme MVP simple** : EventBus côté front (e.g. mitt) — quand un tool de mutation termine, le backend renvoie un événement `entity_updated` que le front écoute et qui déclenche le rechargement de la zone concernée. Alternative : SSE/WebSocket dédié.

### US5 — Bulle LLM vs zone d'input (P1 — contrainte UX critique)
**En tant que** PME,
**je veux** que :
- ce que dit le LLM apparaît **dans la conversation** (bulles haut),
- ce que je dis (texte libre OU choix structuré via tools de réponse de F15) apparaît **dans la conversation** comme message utilisateur,
- la **zone de saisie** est en bas et peut basculer entre input texte libre et bottom sheet de tool de réponse (F15).

**Règle stricte** : les composants interactifs de réponse (radio, checkboxes, sélecteur) **ne sont jamais rendus inline dans la bulle du LLM**. Ils sont toujours en bas, à la place de l'input. F13 livre **le squelette** de cette UX (zone bulle, zone input, slot pour bottom sheet) ; F15 livrera les composants interactifs.

### US6 — Liste des threads et navigation (P2)
**En tant que** PME,
**je veux** voir une liste de mes threads de conversation (chacun nommé automatiquement par le LLM ou par défaut "Conversation du DD/MM/YYYY"), pouvoir basculer entre eux et en supprimer,
**afin de** organiser mes échanges.

### US7 — Indicateur de chargement + animations (P2)
**En tant que** PME,
**je veux** voir clairement quand le LLM réfléchit (indicateur "..." animé, barre de progression sur les longues actions),
**afin de** comprendre que ça mouline.

GSAP pour les transitions (déjà installé en F01).

### US8 — Liens cliquables entre conversation et UI (P3)
**En tant que** PME,
**je veux** qu'un message du LLM mentionnant un projet (ex : "votre projet panneaux solaires") contienne un lien cliquable qui me ramène sur la page `/profil/projets/{id}`,
**afin de** naviguer fluidement.

## Exigences fonctionnelles

- **FR-001** : Table `chat_thread` : `id, account_id, user_id, title, created_at, updated_at, archived BOOL`.
- **FR-002** : Table `chat_message` (déjà créée en F01) enrichie : `id, thread_id, role ENUM('user','assistant','system','tool'), content TEXT, payload_json JSONB NULL (pour structured tool invocations / responses), embedding vector(1024), context_json JSONB NULL (page, entity_type, entity_id à l'envoi), created_at`.
- **FR-003** : Endpoints REST :
  - `GET /me/chat/threads` (liste des threads),
  - `POST /me/chat/threads` (créer un thread),
  - `GET /me/chat/threads/{id}/messages?after_id=` (paginé),
  - `POST /me/chat/threads/{id}/messages` (envoyer un message + retourner la réponse LLM),
  - `DELETE /me/chat/threads/{id}` (archive).
- **FR-004** : Le `POST /messages` accepte un body `{content, payload_json?, context_json}` et retourne `{messages:[...]}` (potentiellement plusieurs messages d'assistant + tool calls — la structure complète sera précisée par F14/F15/F16/F17).
- **FR-005** : Composant Vue `<ChatFloating>` placé dans le layout `default.vue` (inclut le bouton flottant + la fenêtre).
- **FR-006** : Composable `useChatContext()` qui expose la page courante, l'entité courante, la sélection courante (basé sur `useRoute()` + Pinia store).
- **FR-007** : Composant `<ChatMessageRenderer :message>` qui rend une bulle. Pour cette feature, supporte uniquement les messages texte simples — les tools (F15/F16/F17) brancheront leurs renderers dessus via un switch sur `payload.type`.
- **FR-008** : Mécanisme de mise à jour réactive : un EventBus Pinia ou un canal SSE `/me/events` qui pousse `{type:'entity_updated', entity_type, entity_id}` à chaque mutation. Les composants intéressés s'abonnent (page Profil, page Projet, etc.).
- **FR-009** : Sauvegarde du message utilisateur ET de la (des) réponse(s) LLM dans `chat_message` à chaque tour, avec `embedding` calculé via Voyage AI (F03 client) post-tour pour alimenter le RAG (F18).
- **FR-010** : Le contexte de page est envoyé à chaque message (FR-004 `context_json`). Le backend ne le traite pas encore en F13 — juste le stocke.

## Exigences non-fonctionnelles

- **NFR-001** : La fenêtre de chat ne bloque pas l'accès au contenu de la page (toggle compact/expanded). Sur mobile, plein écran.
- **NFR-002** : Latence d'affichage du message utilisateur (echo) < 100ms après Enter (UX optimiste).
- **NFR-003** : Le streaming de la réponse LLM est supporté (Server-Sent Events ou chunked HTTP) — l'utilisateur voit les tokens arriver progressivement.
- **NFR-004** : Persistance localStorage de l'état UI (ouvert/fermé/compact) pour ne pas réagacer à chaque navigation.
- **NFR-005** : Accessibilité : focus trap dans la fenêtre quand ouverte, ESC ferme, ARIA roles `dialog` / `log` corrects.
- **NFR-006** : Aucun message système contenant des secrets (clés API, prompt expert) n'est exposé côté client.

## Entités clés

- **ChatThread** (FR-001).
- **ChatMessage** (FR-002, enrichi).

## Success Criteria

- **SC-001** : Conversation simple "bonjour" → "bonjour, comment puis-je vous aider ?" fonctionne end-to-end (F13 + LLM client F01).
- **SC-002** : Naviguer entre 3 pages → conversation persiste, position scroll préservée.
- **SC-003** : Streaming SSE actif et lisible (tokens apparaissent progressivement).
- **SC-004** : `context_json` stocké correctement pour 100% des messages.
- **SC-005** : EventBus déclenche le rechargement d'un champ Profil quand un tool de mutation termine (testé dès que F17 sera livré).

## Hors-scope MVP (livré dans d'autres features)

- Tools de réponse en bottom sheet → **F15**.
- Tools de visualisation inline → **F16**.
- Tools de mutation et leurs garde-fous → **F17**.
- LangGraph routing, validation Pydantic, retry → **F14**.
- Mémoire contextuelle, RAG, recall_history → **F18**.
- Skills (playbooks métier) → **F19/F20/F21**.
- Voix / audio in / audio out → post-MVP (Replicate Whisper réservé F22 docs).

## Risques et points de vigilance

- **Streaming + tool calls** : combiner streaming token et tool calls structurés est non trivial avec OpenRouter. Pattern recommandé : un message peut contenir plusieurs "events" (tool_call_started, tool_call_completed, text_delta, message_done). Le frontend renderer doit comprendre. À clarifier en `/speckit.clarify`.
- **Contexte de page sensible** : ne JAMAIS envoyer dans le contexte LLM des champs sensibles (mot de passe, JWT, refresh token). Whitelist explicite.
- **Storage des messages volumineux** : si un payload de visualisation (F16) fait 100 KB, ne pas le stocker en clair dans `payload_json` à chaque message — versionner par référence si possible (mais MVP : on l'accepte).
- **Réactivité** : si l'EventBus est mal géré, on peut avoir des fuites d'events entre comptes (cross-tenant). Toujours filtrer par `account_id` côté serveur SSE.
- **Mobile UX** : prévoir le clavier virtuel qui déforme la fenêtre — utiliser `dvh` plutôt que `vh`.
