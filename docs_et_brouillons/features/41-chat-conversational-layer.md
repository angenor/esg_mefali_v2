# F41 — Chat Conversational Layer (UI de F12/F13)

**Phase** : B — Briques transversales LLM/chat
**Modules brainstorm** : 1.0–1.2 — couche **frontend** du chat (shell, bubbles, input, EventBus, langgraph)
**Dépendances** : F36, F37, F38, F39 (bottom sheet), F40 (viz), F13 (backend chat), F14 (orchestrator), F18 (memory)
**Estimation** : 5 jours

## Contexte et objectif

Cœur produit : la page chat où la PME interagit avec le LLM. Architecture "haut/bas" stricte (P10) : haut = bulles LLM + utilisateur, bas = input texte OU bottom sheet F39 OU viz F40. EventBus client-side propage les mutations LLM vers stores Pinia → pages profil ouvertes (P8 sync bidirectionnel).

Style : épuré, calme, focus lecture. Bulles asymétriques (LLM gauche, user droite). Pas de pictogrammes "✨". Avatar LLM minimal (carré arrondi avec logo).

## User Stories

- **US1 ChatLayout (P1)** — `/chat` plein écran, header sticky simple, bulles scroll, input bottom sticky, max-width contenu 720 px.
- **US2 MessageBubble user (P1)** — bulle droite, fond brand-50, timestamp hover.
- **US3 MessageBubble LLM (P1)** — bulle gauche, fond neutral-50, **Markdown sanitize**, citations P1 inline en superscript cliquable (popover via `<VizSourcePin>` F40).
- **US4 MessageBubble viz (P1)** — bulle gauche large, embed `<VizKPICard / LineChart / Mermaid / DataTable>` selon `payload_json.tool`.
- **US5 Typing indicator (P1)** — 3 dots animés gsap pendant rédaction LLM.
- **US6 Streaming token-by-token (P1)** — Markdown rendu progressif (parser tolère partial), curseur clignotant fin de stream.
- **US7 Input bar (P1)** — `<UiTextarea>` autoresize 1-6 lignes, bouton envoyer, attache fichier rapide, Cmd/Ctrl+Enter envoie.
- **US8 BottomSheet integration (P1)** — `payload_json.tool` ∈ {`ask_*`, `show_*`} → `useChatBottomSheet().open` (F39) cache input, ouvre sheet.
- **US9 ThreadList sidebar (P1)** — conversations passées (titre auto, date, icône), bouton "Nouveau chat".
- **US10 EventBus sync (P1)** — `useChatEventBus()` propage `entity_updated` aux stores → pages ouvertes refresh.
- **US11 Re-classification freetext (P1)** — clic "Répondre librement" → input texte revient, prochain envoi reclassifié par F14.
- **US12 Erreurs LLM (P1)** — pipeline F14 fail (validation, timeout) → bulle erreur sobre + bouton "Réessayer".
- **US13 Suggestions / quick replies (P2)** — sous dernière bulle LLM, 2-3 chips "Continuer", "Reformuler".
- **US14 Memory context indicator (P2)** — badge top-bar `memory_size` (F18), cliquable → modal détail.
- **US15 Onboarding tour (P1)** — driver.js 4 étapes au 1er chat (input, fichier, sidebar, sheet exemple).

## Exigences fonctionnelles

- **FR-001** : `pages/chat/index.vue` + `pages/chat/[thread_id].vue`.
- **FR-002** : `components/chat/{ChatLayout,MessageBubble,MessageInput,TypingIndicator,ThreadList,QuickReplies}.vue`.
- **FR-003** : Pinia `useChatStore` (threads, messages, current_thread, streaming_state).
- **FR-004** : SSE `GET /me/chat/threads/{id}/stream` via `EventSource`, reconnect backoff 1/2/4 s.
- **FR-005** : Markdown via `markdown-it` + DOMPurify : titres, listes, code, tables, mermaid blocks (déclenche F40).
- **FR-006** : `useChatEventBus()` (mitt + Pinia subscribe) propage `{event_type, entity_type, entity_id, fields_updated[]}`.
- **FR-007** : Memory snapshot on-demand `GET /me/chat/threads/{id}/memory` (F18).
- **FR-008** : LangGraph front (`@langchain/langgraph` F01) orchestre sheet ↔ input ↔ SSE.
- **FR-009** : Sanitize strict tout contenu LLM (pas scripts/iframes).

## Exigences non-fonctionnelles

- **NFR-001** : Premier token < 500 ms après envoi user.
- **NFR-002** : Scroll auto sauf si user scrollé up (préserve position).
- **NFR-003** : Reconnexion SSE sans dupliquer tokens (sequence_id).
- **NFR-004** : Mobile input bottom sticky safe area iOS.

## Success Criteria

- **SC-001** : Envoyer message → streaming token-by-token, bulle complète < 5 s.
- **SC-002** : LLM invoque `ask_qcu` → sheet ouvert (F39), Valider → message structuré en DB.
- **SC-003** : LLM invoque `update_entreprise` (F17) → EventBus → page profil refresh.
- **SC-004** : Sidebar threads, click ancien thread → contenu rechargé.
- **SC-005** : Tour driver.js sans bug.

## Hors-scope MVP

- Voice in/out → post-MVP.
- Multi-utilisateur même thread → post-MVP.
- Recherche messages → post-MVP.
- Export thread PDF → post-MVP.

## Risques et points de vigilance

- SSE + reconnect : tester réseau intermittent, backoff exponentiel, dedup.
- Markdown partial : `**bold` non fermé pendant streaming ne crash pas.
- EventBus loop : éviter re-déclencher LLM sur mutation UI (P8).
- Mermaid 100 nœuds : ne pas freeze, async ou limiter.
- Mobile keyboard : input non recouvert (safe area).
