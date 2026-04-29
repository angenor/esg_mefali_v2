# F15 — Tools de Réponse en Bottom Sheet (ask_*, show_form, show_summary_card)

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 1.1.1 (Chat Interactif — Tools de Réponse en Bottom Sheet)
**Dépendances** : F13, F14
**Estimation** : 2.5 jours

## Contexte et objectif

Le chat n'est pas qu'un échange textuel. Quand le LLM doit poser une question fermée (choix unique, multiple, sélection, confirmation, date, etc.), il invoque un **tool dédié de réponse**. La **question** reste affichée normalement dans la bulle du LLM (texte). La **zone de réponse** prend la forme d'un **bottom sheet qui remplace temporairement la barre de saisie** en bas de l'écran.

> **Règle UX critique (du brainstorming)** : "haut = ce que dit l'autre, bas = ce que je dis/choisis". Aucun composant interactif n'est rendu inline dans la bulle du LLM.
> Inspiration : extension Claude Code dans VS Code (réponses guidées par composants), avec séparation stricte question (haut) / réponse (bas).

## User Stories

### US1 — ask_qcu : Question à Choix Unique (P1)
**En tant que** PME interagissant avec le LLM,
**je veux** que quand le LLM me demande "Quelle est votre forme juridique ?", je voie en bas un bottom sheet avec radios (SARL / SA / SAS / Coopérative / Autre) + bouton "Valider",
**afin de** répondre rapidement sans faute de frappe.

**Test indépendant** : invoquer `ask_qcu(question, options[2-7], multi=False)` → l'UI rend le bottom sheet. Cliquer une option → bouton Valider devient actif. Cliquer Valider → message utilisateur "✓ SARL" injecté dans la conversation. Bottom sheet se ferme, input texte réapparaît.

### US2 — ask_qcm : Question à Choix Multiples (P1)
**En tant que** PME,
**je veux** quand le LLM me demande "Quels piliers ESG vous concernent ?", voir un bottom sheet avec checkboxes (Environnement / Social / Gouvernance) + bouton Valider,
**afin de** sélectionner plusieurs réponses.

### US3 — ask_yes_no : Confirmation binaire (P1)
**En tant que** PME,
**je veux** quand le LLM demande confirmation (variantes : Oui/Non, Confirmer/Annuler, Continuer/Plus tard),
**afin de** valider rapidement.

Critique pour les actions destructives de F17 (mutations LLM).

### US4 — ask_select : Sélection dans liste longue avec recherche (P1)
**En tant que** PME,
**je veux** que pour des listes longues (pays, secteur d'activité, fonds, intermédiaire, source), le bottom sheet ait un input de recherche,
**afin de** trouver rapidement.

### US5 — ask_number : Saisie numérique avec unité et bornes (P1)
**En tant que** PME,
**je veux** un input numérique typé (CA, effectifs, montant, tCO2e) avec unité affichée et bornes appliquées,
**afin de** ne pas saisir n'importe quoi.

**Particularité** : pour les Money, le composant affiche aussi la conversion FCFA↔EUR live (cohérent F05).

### US6 — ask_date / ask_date_range (P2)
**En tant que** PME,
**je veux** un sélecteur de date (ou plage) ergonomique,
**afin de** indiquer une échéance ou une période.

### US7 — ask_rating : Échelle 1–5 ou 1–10 (P2)
**En tant que** PME,
**je veux** une échelle pour auto-évaluer mes pratiques,
**afin de** alimenter le diagnostic ESG (Module 5.1 photos / pratiques).

### US8 — ask_file_upload : Bouton d'upload contextualisé (P1)
**En tant que** PME,
**je veux** que le LLM me demande "Pouvez-vous uploader votre business plan ?" avec un bouton dédié dans le bottom sheet,
**afin de** uploader sans quitter la conversation.

L'upload réutilise les endpoints de F12 (DocumentProjet) ou F22 (DocumentEntreprise).

### US9 — show_form : Mini-formulaire multi-champs (P2)
**En tant que** PME,
**je veux** quand le LLM dit "Pour créer le projet en une fois, voici les champs nécessaires", voir un bottom sheet avec plusieurs champs typés (texte, nombre, date, select),
**afin de** créer rapidement un objet en bloc.

### US10 — show_summary_card : Carte récapitulative actionnable (P1)
**En tant que** PME,
**je veux** quand le LLM extrait des infos d'un document, voir une carte "Voici ce que j'ai compris : Nom = X, Effectifs = Y, ..." avec boutons "Valider", "Corriger", "Annuler",
**afin de** confirmer ou corriger l'extraction.

### US11 — Bascule "Répondre librement" (P1)
**En tant que** PME,
**je veux** un bouton toujours visible dans le bottom sheet qui me permet de fermer le widget et revenir à la saisie texte libre,
**afin de** ne jamais être bloquée par un widget.

**Important** : si je bascule en libre, le LLM s'adapte à ma réponse texte (re-classifie l'intention).

### US12 — Traçabilité du payload de réponse (P1)
**En tant que** dev,
**je veux** que le payload structuré de la réponse utilisateur (ex : `{tool:'ask_qcu', value:'SARL'}`) soit conservé en métadonnée du message utilisateur (`chat_message.payload_json`), avec une représentation textuelle lisible (`content="✓ SARL"`),
**afin que** le LLM puisse retraiter la réponse sans réinterpréter du texte.

## Exigences fonctionnelles

- **FR-001** : 10 tools déclarés via le décorateur `@tool` (F14) :
  `ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`, `ask_date_range`, `ask_rating`, `ask_file_upload`, `show_form`, `show_summary_card` (11 en fait — la liste est ouverte).
- **FR-002** : Schémas Pydantic stricts par tool (cf. brainstorming Module 1.1.1) :
  - `ask_qcu`: `{question:str, options:[{value, label, description?}], allow_other?:bool}`.
  - `ask_qcm`: `{question:str, options:[...], min_select?, max_select?}`.
  - `ask_yes_no`: `{question:str, yes_label?, no_label?}`.
  - `ask_select`: `{question:str, options_endpoint:str|options:[], multi?:bool}`.
  - `ask_number`: `{question:str, unit:str, min?, max?, step?, money?:{currency}}`.
  - `ask_date(_range)`: `{question:str, min_date?, max_date?, default?}`.
  - `ask_rating`: `{question:str, scale:'1-5'|'1-10'}`.
  - `ask_file_upload`: `{question:str, attach_to:{entity_type, entity_id?}, accepted_mime:[], max_size_mb}`.
  - `show_form`: `{title:str, fields:[{name, type, label, ...}], submit_label?}`.
  - `show_summary_card`: `{title:str, fields:[{label, value, source?}], actions:[{label, kind:'confirm|edit|cancel'}]}`.
- **FR-003** : Composants Vue par tool (`<AskQcu>`, `<AskQcm>`, `<AskYesNo>`, `<AskSelect>`, `<AskNumber>`, `<AskDate>`, `<AskRating>`, `<AskFileUpload>`, `<ShowForm>`, `<ShowSummaryCard>`).
- **FR-004** : Composant orchestrateur `<ChatBottomSheet>` qui :
  - Affiche le composant du tool actif,
  - Anime l'apparition/disparition (gsap),
  - Cache la barre d'input texte standard pendant qu'il est actif,
  - Affiche en permanence le bouton "Répondre librement" (US11).
- **FR-005** : Lors du Valider, le frontend POST `/me/chat/threads/{id}/messages` avec `{content: "✓ SARL", payload_json: {tool: 'ask_qcu', value: 'SARL', label: 'SARL'}, context_json}`.
- **FR-006** : Le pipeline F14 reconnaît un payload de réponse structuré et l'injecte au LLM avec un format normalisé (pas de réinterprétation texte).
- **FR-007** : Bascule "Répondre librement" : émet un événement `bottom_sheet_dismissed_for_freetext` ; le pipeline F14 traite le prochain message comme un message texte libre.
- **FR-008** : Validation côté client identique aux schémas Pydantic (générée depuis OpenAPI ou rédigée en parallèle avec zod/valibot).
- **FR-009** : Helper `<AskSelect>` peut charger les options depuis un endpoint (`options_endpoint`) — utile pour Pays / Secteur / Fonds / Intermédiaire (consommation des endpoints F08/F09).
- **FR-010** : Pour `ask_file_upload`, l'upload appelle l'endpoint approprié (F12 documents projet, ou F22 documents entreprise) et le résultat (doc_id) est inclus dans le payload utilisateur retour.

## Exigences non-fonctionnelles

- **NFR-001** : Animation d'apparition/disparition du bottom sheet < 200ms (gsap).
- **NFR-002** : Bottom sheet responsive : sur mobile, occupe 70% de la hauteur ; desktop, hauteur fluide selon contenu.
- **NFR-003** : Accessibilité : ARIA `role="dialog"` ou `role="form"`, focus trap, ESC ferme et bascule en libre.
- **NFR-004** : Aucune fuite XSS dans `label`/`description` des options — sanitize systématique.

## Entités clés

- Aucune nouvelle table — `chat_message.payload_json` stocke les payloads (cohérent F13).

## Success Criteria

- **SC-001** : LLM invoque `ask_qcu` → user clique → message utilisateur structuré en DB. Vérifié sur 5 cas tests.
- **SC-002** : Bascule "Répondre librement" → input texte réapparaît, LLM s'adapte. Vérifié.
- **SC-003** : `ask_select` avec `options_endpoint` charge correctement 100 options paginées avec recherche.
- **SC-004** : `show_summary_card` permet de valider/corriger un résumé d'extraction OCR (preview F22).

## Hors-scope MVP

- Tools de visualisation → **F16**.
- Tools de mutation → **F17**.
- Voice input → post-MVP.
- Tools custom par skill (chaque skill définit ses propres tools) → **F19/F20**.
- Multi-step wizard via tools chaînés (post-MVP).

## Risques et points de vigilance

- **Cohérence question/réponse** : si le LLM dit "Quel est votre secteur ?" en texte ET invoque `ask_qcu` en parallèle, on a doublon. Le system prompt (F14 US4) doit imposer : "soit tu poses la question en texte avec invocation tool, soit pas du tout en texte". Tester sur eval set F35.
- **Listes très longues** (pays = 200+) : `ask_select` doit virtualiser le rendu.
- **Conflit avec saisie texte** : si l'utilisateur clique sur l'input alors que le bottom sheet est actif, soit l'input est désactivé (clair UX), soit la bascule libre se déclenche automatiquement. Recommandation : input désactivé visiblement, bouton "Répondre librement" obligatoire pour basculer.
- **Skin du bottom sheet** : aligner avec design system Tailwind v4 + composants Pinia ; éviter de réinventer un toolkit. driver.js + gsap (déjà installés F01) suffisent.
- **`ask_file_upload`** : l'upload doit pouvoir échouer proprement (taille, mime invalide) et le LLM doit recevoir un événement structuré pour rebondir.
