# Quickstart — F41 Chat Conversational Layer

## Prérequis

- F12, F14, F18, F36, F37, F38, F39, F40 implémentées (ou stubs minimaux disponibles).
- Backend lancé (`make backend`, port 8010) avec un compte PME et au moins une `Source` `verified` en base.
- Frontend lancé (`make frontend`, port 3001).

## Lancer la feature en local

```bash
# Terminal 1 — Postgres
make db-up

# Terminal 2 — Backend
make backend
# → http://localhost:8010/health doit répondre {"status":"ok"}

# Terminal 3 — Frontend
make frontend
# → http://localhost:3001
```

Connectez-vous comme PME (`/login`), puis ouvrez `http://localhost:3001/chat`.

## Vérifications de base (golden path)

1. **Liste des threads** : la sidebar gauche liste les threads existants (ou est vide). Cliquer « Nouveau chat » crée un thread vide.
2. **Envoi + streaming** : taper « Bonjour, peux-tu m'expliquer le scope 1 du carbone ? » + `Cmd/Ctrl + Enter`. Vérifier :
   - Bulle utilisateur droite (fond `brand-50`).
   - Indicateur 3 dots gsap pendant < 500 ms.
   - Premier token affiché en bulle gauche dans la fenêtre 200–500 ms.
   - Curseur clignotant en fin pendant le stream.
   - Bulle finalisée < 5 s.
3. **Sources P1** : si la réponse contient des citations, vérifier le superscript cliquable qui ouvre un popover `<VizSourcePin>` (F40).
4. **Bottom sheet** : poser une question structurée (ex. demander un onboarding entreprise). Vérifier que l'input texte se masque, qu'un bottom sheet s'ouvre (F39), que le bouton « Répondre librement » ferme le sheet et restaure l'input.
5. **EventBus** : ouvrir `/profil` dans un autre onglet, demander au LLM « Mon entreprise a 12 salariés ». Vérifier que le profil reflète l'effectif sans rechargement (< 1 s).
6. **Erreur + retry** : simuler une erreur backend (couper temporairement le backend, envoyer un message, redémarrer). Bulle d'erreur sobre + bouton « Réessayer » fonctionnel.
7. **Scroll-pinning** : envoyer un long message, scroller vers le haut pendant le stream, vérifier que l'autoscroll est suspendu, puis scroller en bas, vérifier qu'il reprend.
8. **Onboarding** : se connecter avec un nouveau compte PME (ou vider `localStorage` clé `chat.onboarding.seen.{accountId}`), ouvrir `/chat`, suivre les 4 étapes driver.js, fermer, vérifier qu'au prochain accès le tour ne se relance pas.
9. **Mobile** : DevTools responsive iPhone 14, ouvrir clavier virtuel (focus textarea) — vérifier que l'input reste visible (safe-area).

## Tests automatisés

```bash
cd frontend
pnpm vitest run tests/chat
# - tests/chat/MessageMarkdown.spec.ts (XSS payloads, partial Markdown)
# - tests/chat/useChatStream.spec.ts (SSE simulé, dedup, reconnect)
# - tests/chat/useChatEventBus.spec.ts (no-loop guard)
# - tests/chat/ChatHistory.spec.ts (scroll-pinning)

# A11y :
pnpm test:a11y -- /chat
```

## Variables d'environnement

Aucune nouvelle variable côté F41. La feature consomme `NUXT_PUBLIC_API_BASE` (déjà en place).

## Smoke checklist (PR-ready)

- [ ] Aucun warning Vue console au chargement de `/chat`.
- [ ] `pnpm typecheck` vert.
- [ ] `pnpm lint` vert.
- [ ] Coverage chat ≥ 80 %.
- [ ] Tests XSS verts (DOMPurify allow-list active).
- [ ] Aucun fetch direct depuis un composant — toujours via `useChatStore`.
- [ ] Aucun `<input>` / `<button type="submit">` à l'intérieur d'un `<MessageBubbleAssistant>`.
- [ ] Mobile iOS Safari + Android Chrome : input non-recouvert clavier.
- [ ] Reconnexion réseau de < 10 s sans tokens dupliqués.
