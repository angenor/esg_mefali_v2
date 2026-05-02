# F39 — Bottom Sheet Engine (UI de F15)

**Phase** : B — Briques transversales LLM/chat
**Modules brainstorm** : 1.1.1 — implémentation **frontend** des tools `ask_*`, `show_form`, `show_summary_card`
**Dépendances** : F36, F37, F38, F15 (backend tools), F14 (orchestrateur LLM)
**Estimation** : 4 jours

## Contexte et objectif

Concrétise la règle constitutionnelle **P10** : tout input interactif (radios, checkbox, file, slider, date, formulaire) **vit dans un bottom sheet animé en gsap**, jamais inline dans une bulle LLM. Compose les composants F37 dans des wrappers spécialisés `<AskQcu>`, `<AskQcm>`, `<AskYesNo>`, `<AskSelect>`, `<AskNumber>`, `<AskDate>`, `<AskRating>`, `<AskFileUpload>`, `<ShowForm>`, `<ShowSummaryCard>`. Bouton "Répondre librement" toujours visible.

## User Stories

- **US1 ChatBottomSheet orchestrateur (P1)** — composant racine reçoit `{tool, payload}`, monte le composant approprié, anime apparition (gsap, slide-up 200 ms), bloque la barre input texte, expose events `submit` + `dismiss-for-freetext`.
- **US2 AskQcu (P1)** — radios verticaux, "Autre" optionnel ouvre input texte, Valider activé sur sélection.
- **US3 AskQcm (P1)** — checkboxes avec `min/max_select` UI-enforced, compteur "X sur N sélectionnés".
- **US4 AskYesNo (P1)** — 2 boutons larges, surcharge labels possible.
- **US5 AskSelect (P1)** — search input focus auto, virtualisation `vue-virtual-scroller`, source sync OR `options_endpoint` async paginé. Clavier ↑↓ Enter ESC.
- **US6 AskNumber (P1)** — input numérique, unité (`tCO2e`, `FCFA`, `%`), bornes UI-enforced, conversion live FCFA↔EUR (peg 655.957) si `money: {currency}` fourni.
- **US7 AskDate / AskDateRange (P1)** — `<UiDatePicker>` F37, locale FR, semaine lundi.
- **US8 AskRating (P2)** — étoiles 1-5 ou 1-10, clavier 1..0.
- **US9 AskFileUpload (P1)** — `<UiFileUpload>` F37 + endpoint F22 (documents entreprise) ou F12-projet selon `attach_to`. Renvoie `{doc_id, filename, mime, size}`.
- **US10 ShowForm (P2)** — formulaire multi-champs typé, validation zod générée depuis schéma Pydantic.
- **US11 ShowSummaryCard (P1)** — récap `{label, value, source?}`, actions `Valider | Corriger | Annuler`.
- **US12 Bouton "Répondre librement" (P1)** — sticky bottom du sheet, émet `dismiss-for-freetext` ; pipeline F14 reclassifie le prochain texte.
- **US13 Traçabilité payload (P1)** — submit POST `/me/chat/threads/{id}/messages` body `{content: "✓ SARL", payload_json: {tool, value, label}, context_json}`.

## Exigences fonctionnelles

- **FR-001** : `frontend/app/components/chat/bottom-sheet/{ChatBottomSheet,Ask*,ShowForm,ShowSummaryCard}.vue`.
- **FR-002** : Animation gsap `slideUp` 200 ms ease-out entrée, `slideDown` 160 ms ease-in sortie. `useReducedMotion` neutralise.
- **FR-003** : Chaque Ask* a un `.test.ts` vitest (rendu, validation, submit payload, ESC ferme + bascule libre).
- **FR-004** : Schémas zod générés depuis Pydantic (`pnpm gen:tools` lit `/openapi.json`).
- **FR-005** : Composable `useChatBottomSheet()` expose `{open(tool, payload), close, current}`, consommé par F41.
- **FR-006** : Sanitize `label`/`description` des options (DOMPurify) — XSS-proof.
- **FR-007** : Focus trap, ESC ferme + bascule libre, Tab cycle dans le sheet uniquement.

## Exigences non-fonctionnelles

- **NFR-001** : Apparition < 200 ms perçue.
- **NFR-002** : Mobile 70 % hauteur viewport ; desktop fluide max 60 %.
- **NFR-003** : Aucune fuite XSS — test input `<script>alert(1)</script>` doit escape.
- **NFR-004** : Listes virtualisées si > 50 options.

## Success Criteria

- **SC-001** : LLM invoque `ask_qcu` sur 5 cas tests → message structuré en DB, payload conforme F15.
- **SC-002** : Bascule "Répondre librement" → input texte réapparaît, LLM s'adapte (test pipeline F14).
- **SC-003** : `ask_select` charge 200 pays paginés sans lag (60 fps).
- **SC-004** : `show_summary_card` permet valider/corriger un résumé OCR (preview F50).
- **SC-005** : `ask_file_upload` upload 5 MB PDF → doc créé, payload retour avec `doc_id`.

## Hors-scope MVP

- Tools custom par skill → F19/F20.
- Multi-step wizard via tools chaînés → post-MVP.
- Voice input → post-MVP.

## Risques et points de vigilance

- **Cohérence question/réponse** : doublon texte + tool. Gérer via system prompt F14 + eval F35.
- **Conflit input texte** : input désactivé visiblement quand sheet actif ; bascule via bouton uniquement.
- **`ask_file_upload`** : échec proprement, événement structuré au LLM.
- **Listes virtualisées** : tester clavier (↑↓ Enter) hors viewport.
