# Quickstart — F39 Bottom Sheet Engine

## Prérequis

- Setup projet déjà fait (`make setup`, `make migrate`, `cp .env.example .env`).
- F37 (UI primitives) et F38 (App shell) mergées sur `main`.
- F15 (backend tools) déployé : `/openapi.json` doit exposer les schémas des tools `ask_*` / `show_*`.

## Démarrer en local (3 terminaux)

```bash
# T1 — Postgres
make db-up

# T2 — Backend FastAPI (port 8010)
make backend

# T3 — Frontend Nuxt (port 3001)
make frontend
```

## Génération des schémas tools

```bash
cd frontend
pnpm gen:tools           # lit http://localhost:8010/openapi.json
                         # produit app/types/tools/*.ts
```

À relancer chaque fois que F15 ajoute/modifie un tool. Le script échoue en CI si le diff sur `types/tools/` n'est pas committé.

## Lancer un sheet manuellement (debug)

Dans la devtools console, sur la page chat :

```js
const { open } = useChatBottomSheet()
await open({
  tool: 'ask_yes_no',
  payload: { question: 'Êtes-vous une SARL ?' },
  context: { thread_id: '<uuid>', message_id: '<uuid>' }
})
```

Le sheet doit apparaître en ~200 ms, la barre input se griser, et `ESC` doit basculer en saisie libre.

## Tester un wrapper

```bash
cd frontend
pnpm vitest run app/components/chat/bottom-sheet/__tests__/AskQcu.test.ts
pnpm vitest run app/components/chat/bottom-sheet/__tests__/   # toute la feature
```

## Vérifier la reconstitution depuis un thread

1. Démarrer le backend (T2).
2. Insérer manuellement un message tool pending dans un thread test :
   ```sql
   INSERT INTO chat_messages (id, thread_id, role, content, payload_json, created_at, account_id)
   VALUES (gen_random_uuid(), '<thread_uuid>', 'assistant',
           'Quelle est la forme juridique ?',
           '{"tool":"ask_qcu","payload":{"question":"Forme juridique","options":[{"value":"sarl","label":"SARL"},{"value":"sa","label":"SA"}]}}',
           NOW(), '<account_uuid>');
   ```
3. Recharger la page chat sur ce thread → le sheet doit s'ouvrir automatiquement.
4. Soumettre une réponse → un nouveau message PME est inséré, le sheet se ferme.

## Vérifier la sanitization XSS

Dans un test ou via debug console :

```js
await open({
  tool: 'ask_qcu',
  payload: {
    question: 'Test',
    options: [{ value: 'a', label: '<script>alert(1)</script>Option A' }]
  },
  context: { thread_id: '...', message_id: '...' }
})
```

Le label doit s'afficher textuellement comme `<script>alert(1)</script>Option A` ; aucun script ne s'exécute. Test automatisé : voir SC-006.

## Vérifier la conversion FCFA↔EUR

```js
await open({
  tool: 'ask_number',
  payload: {
    question: 'Montant du financement',
    money: { currency: 'XOF' }
  },
  context: { thread_id: '...', message_id: '...' }
})
```

Saisir `1500000` → la conversion live affichée doit être `≈ 2 287,06 €` (1500000 ÷ 655.957).

## Reduced motion

```bash
# Forcer en macOS : Préférences → Accessibilité → Diminuer les animations
# OU via DevTools : Rendering panel → Emulate CSS prefers-reduced-motion: reduce
```

Recharger ; le sheet s'ouvre sans animation perceptible mais reste fonctionnel.

## API publique du moteur (Phase 7 — référence)

Trois entrées suffisent pour intégrer F39 dans une page Nuxt :

```ts
import { ChatBottomSheet } from '~/components/chat/bottom-sheet'
import { useChatBottomSheet } from '~/composables/useChatBottomSheet'
import type { ToolInstruction } from '~/types/tools/contracts'
```

- **`<ChatBottomSheet />`** — composant orchestrateur. Le monter une seule fois dans le shell chat. Lit l'instruction courante du store et résout dynamiquement le wrapper (`AskYesNo`, `AskQcu`, …, `ShowSummaryCard`).
- **`useChatBottomSheet()`** — API publique :
  - `open(instruction)` — valide via `toolInstructionSchema` puis ouvre. Refuse silencieusement si un sheet est déjà ouvert (FR-002).
  - `close('freetext' | 'cancel')` — émet `chat:bottom-sheet:dismiss-for-freetext` côté `window` ; basculer l'input chat sur saisie libre.
  - `rebuildFromThread(threadId)` — au reload, interroge `/me/chat/threads/{id}/pending-tool` (F14/F15) et rouvre le bon sheet (Q1).
  - `current` (Readonly Ref) / `isOpen` (ComputedRef) — lecture seule.
- **`useBottomSheetSubmit()`** — POST `/me/chat/threads/{thread_id}/messages` avec body strict `{ content, payload_json, context_json }`. Garantit `inFlight` (un seul POST en vol — SC-007) et mappe les codes 4xx/5xx vers des messages FR.

### Flux reconstitution (Q1)

```
[reload page] → onMounted hook chat → useChatBottomSheet().rebuildFromThread(threadId)
                                       │
                                       ▼
              GET /me/chat/threads/{id}/pending-tool  (204 si rien en pending)
                                       │
                                       ▼
              parse zod via toolInstructionSchema → store.setCurrent(instruction)
                                       │
                                       ▼
              <ChatBottomSheet /> rend le wrapper, anime le slide-up
```

### Sécurité & a11y (cross-cutting)

- Tout texte issu du backend (`question`, `label`, `description`, `source_label`, `unit`) passe par `sanitizeText()` (DOMPurify, ALLOWED_TAGS=[]). Voir `__tests__/xss.security.test.ts`.
- Aucune double-soumission : flag `inFlight` dans `useBottomSheetSubmit`. Voir `__tests__/double-submit.security.test.ts`.
- Audit `axe-core` sans violation `serious`/`critical` sur les 7 wrappers principaux (`__tests__/a11y.axe.test.ts`).
- Caps de hauteur viewport (NFR-002) : 70vh mobile / 60vh ≥ 768px — gardés par `__tests__/viewport.test.ts`.

## Critères de done

- [ ] Tous les wrappers ont un test vitest passant les 5 cas (rendu, valid, invalid, ESC, XSS).
- [ ] `pnpm vitest run` global passe avec coverage ≥ 80 %.
- [ ] Lint propre : `pnpm lint` sur `app/components/chat/bottom-sheet/` et `app/composables/useChatBottomSheet.ts`.
- [ ] `pnpm gen:tools` produit un diff vide après build CI (= types committés à jour).
- [ ] Reconstitution depuis le thread vérifiée à la main sur 3 tools (`ask_qcu`, `ask_number`, `show_summary_card`).
- [ ] SC-001 à SC-007 vérifiés (cf. `spec.md`).
