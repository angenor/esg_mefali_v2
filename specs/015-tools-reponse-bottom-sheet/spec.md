# Feature Specification: Tools de Réponse en Bottom Sheet (F15)

**Feature Branch**: `015-tools-reponse-bottom-sheet`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Tools ask_*, show_form, show_summary_card pour réponses guidées en bottom sheet (F13/F14)"

## User Scenarios & Testing *(mandatory)*

Les user stories sont indépendamment testables : chacune peut être livrée seule comme MVP partiel (un tool ⇒ une UX guidée).

### User Story 1 — ask_qcu : Choix unique (P1)

Quand le LLM doit poser une question fermée à choix unique (ex. "Quelle est votre forme juridique ?"), il invoque le tool `ask_qcu`. La question reste affichée dans la bulle LLM (haut), un bottom sheet apparaît en bas avec radios et bouton Valider.

**Why this priority** : Cas le plus fréquent en onboarding/diagnostic. Élimine les fautes de frappe et standardise les valeurs collectées.

**Independent Test** : Invoquer `ask_qcu(question, options[2-7], multi=False)` ; cliquer une option active Valider ; cliquer Valider injecte un message utilisateur "✓ SARL" dans le thread, persisté avec `payload_json={tool:"ask_qcu", value:"SARL", label:"SARL"}`.

**Acceptance Scenarios** :

1. **Given** un thread chat ouvert, **When** le LLM invoque `ask_qcu` avec 4 options, **Then** le bottom sheet s'affiche avec 4 radios, l'input texte est masqué/désactivé, le bouton Valider est désactivé tant qu'aucune option n'est sélectionnée.
2. **Given** une option sélectionnée, **When** l'utilisateur clique Valider, **Then** un message utilisateur "✓ <label>" est créé avec `payload_json` structuré, le bottom sheet se ferme, l'input texte réapparaît.

---

### User Story 2 — ask_qcm : Choix multiples (P1)

Le LLM invoque `ask_qcm` (ex. "Quels piliers ESG vous concernent ?"). Bottom sheet avec checkboxes + bornes min/max.

**Why this priority** : Multi-sélection structurée nécessaire pour piliers ESG, secteurs, types de financement.

**Independent Test** : `ask_qcm(question, options, min_select=1, max_select=3)` ; sélection au-delà des bornes désactive Valider.

**Acceptance Scenarios** :

1. **Given** `min_select=1`, **When** aucune case cochée, **Then** Valider est désactivé.
2. **Given** validation, **Then** `payload_json={tool:"ask_qcm", values:["E","S"], labels:["Environnement","Social"]}`.

---

### User Story 3 — ask_yes_no : Confirmation binaire (P1)

Confirmation Oui/Non avec variantes (Confirmer/Annuler, Continuer/Plus tard).

**Why this priority** : Critique pour actions destructives F17.

**Independent Test** : Invoquer avec `yes_label="Confirmer"` ; deux boutons distincts.

**Acceptance Scenarios** :

1. **Given** confirmation, **Then** `payload_json={tool:"ask_yes_no", value:true, label:"Confirmer"}`.

---

### User Story 4 — ask_select : Liste longue avec recherche (P1)

Pour pays / secteur / fonds / intermédiaire / source, bottom sheet avec input de recherche et options inline ou via endpoint.

**Why this priority** : Évite les listes ingérables ; permet la réutilisation des catalogues F08/F09.

**Independent Test** : `ask_select(question, options_endpoint="/me/catalog/secteurs")` charge 100+ options paginées avec recherche fonctionnelle.

**Acceptance Scenarios** :

1. **Given** `options_endpoint`, **When** l'utilisateur tape "agro", **Then** la liste filtre côté serveur ou client selon la taille.
2. **Given** sélection, **Then** `payload_json` contient l'identifiant et le libellé.

---

### User Story 5 — ask_number : Saisie numérique typée (P1)

Input numérique avec unité, min/max, step. Pour les Money, conversion FCFA↔EUR live.

**Why this priority** : Garantit la qualité des données chiffrées (CA, effectifs, tCO2e, montants).

**Independent Test** : `ask_number(question, unit="t CO2e", min=0, max=1e6, step=0.1)` ; saisie hors bornes refusée.

**Acceptance Scenarios** :

1. **Given** `money={currency:"XOF"}`, **When** l'utilisateur saisit 1 000 000 XOF, **Then** la conversion EUR s'affiche en live (cohérent F05).
2. **Given** valeur valide, **Then** `payload_json={tool:"ask_number", value:1000000, unit:"XOF"}`.

---

### User Story 6 — ask_date / ask_date_range (P2)

Sélecteur de date ou plage avec bornes optionnelles.

**Independent Test** : `ask_date(min_date, max_date)` ; sélection respecte les bornes.

**Acceptance Scenarios** :

1. **Given** plage `[2025-01-01, 2026-12-31]`, **Then** dates hors plage non sélectionnables.

---

### User Story 7 — ask_rating : Échelle 1-5 / 1-10 (P2)

Auto-évaluation Module 5.1 (photos / pratiques ESG).

**Independent Test** : `ask_rating(scale="1-5")` rend 5 boutons.

**Acceptance Scenarios** :

1. **Given** `scale="1-10"`, **Then** 10 boutons rendus, valeur cliquée envoyée en `payload_json`.

---

### User Story 8 — ask_file_upload : Upload contextualisé (P1)

Bouton d'upload dédié relié à F12 (DocumentProjet) ou F22 (DocumentEntreprise).

**Why this priority** : Ouverture du flux documentaire sans quitter la conversation.

**Independent Test** : `ask_file_upload(attach_to={entity_type:"projet", entity_id:"<uuid>"}, accepted_mime=["application/pdf"], max_size_mb=10)`.

**Acceptance Scenarios** :

1. **Given** un fichier accepté, **When** l'upload réussit, **Then** `payload_json={tool:"ask_file_upload", document_id:"<uuid>", filename:"...", size, mime}`.
2. **Given** un fichier > 10 Mo, **Then** erreur affichée et événement structuré envoyé au LLM.

---

### User Story 9 — show_form : Mini-formulaire multi-champs (P2)

Plusieurs champs typés (texte, nombre, date, select) en un seul bottom sheet.

**Independent Test** : `show_form(title, fields:[...])` rend tous les champs ; submit envoie `{tool:"show_form", values:{...}}`.

**Acceptance Scenarios** :

1. **Given** champs `name`+`type`+`label` valides, **When** soumis, **Then** payload structuré stocké.

---

### User Story 10 — show_summary_card : Récap actionnable (P1)

Carte récapitulative avec champs (label/value/source) et actions (Valider / Corriger / Annuler).

**Why this priority** : Indispensable pour confirmer les extractions LLM (OCR, parsing documents) avant écriture en base.

**Independent Test** : `show_summary_card(title, fields, actions)` ; clic action → message utilisateur structuré.

**Acceptance Scenarios** :

1. **Given** action `confirm`, **Then** `payload_json={tool:"show_summary_card", action:"confirm", fields:[...]}`.
2. **Given** action `edit`, **Then** payload `action:"edit"` permet au LLM de relancer un sous-formulaire.

---

### User Story 11 — Bascule "Répondre librement" (P1)

Un bouton toujours visible dans le bottom sheet permet de fermer le widget et revenir à la saisie texte libre.

**Why this priority** : Garantit que l'utilisateur n'est jamais bloqué par un widget.

**Independent Test** : Cliquer "Répondre librement" ferme le widget, l'input texte réapparaît, un événement `bottom_sheet_dismissed_for_freetext` est émis ; le pipeline F14 traite le prochain message comme texte libre et re-classifie l'intention.

**Acceptance Scenarios** :

1. **Given** un bottom sheet actif, **When** l'utilisateur appuie ESC ou clique le bouton dédié, **Then** widget fermé, input réactivé.

---

### User Story 12 — Traçabilité du payload (P1)

Le payload structuré de chaque réponse est conservé en `chat_message.payload_json` ; le `content` reste lisible (ex. "✓ SARL").

**Why this priority** : Le LLM doit pouvoir retraiter sans réinterpréter du texte ; la base sert de source de vérité auditable.

**Independent Test** : POST `/me/chat/threads/{id}/messages` avec `payload_json` structuré ; relecture du thread retourne le payload.

**Acceptance Scenarios** :

1. **Given** un message utilisateur issu d'un tool, **When** relu via l'API, **Then** `payload_json` est intact et le LLM le reçoit normalisé.

---

### Edge Cases

- Tool inconnu invoqué : le frontend affiche un fallback "input texte" et logue l'erreur.
- Schéma payload invalide (côté backend) : 422 avec message clair, message non persisté.
- Utilisateur clique l'input désactivé : feedback visuel "Utilisez le bouton Répondre librement".
- Perte de connexion pendant un upload : retry une fois, puis erreur structurée.
- Liste très longue (>500 options) : virtualisation côté client, pagination côté serveur.
- Doublon question texte + tool : tester sur eval set F35 ; system prompt F14 US4 doit empêcher.
- ESC alors qu'aucun tool actif : aucun effet.
- Soumission concurrente (double-clic) : Valider désactivé après premier clic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT fournir 11 tools de réponse (`ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`, `ask_date_range`, `ask_rating`, `ask_file_upload`, `show_form`, `show_summary_card`) enregistrés dans le tool_registry F14.
- **FR-002** : Chaque tool DOIT avoir un schéma de payload strict validé côté serveur (rejet 422 sur invalide).
- **FR-003** : Le frontend DOIT fournir un composant Vue dédié par tool, plus un orchestrateur `<ChatBottomSheet>`.
- **FR-004** : `<ChatBottomSheet>` DOIT cacher la barre de saisie texte tant qu'un tool est actif et afficher en permanence le bouton "Répondre librement".
- **FR-005** : La validation utilisateur DOIT POST `/me/chat/threads/{id}/messages` avec `content` lisible et `payload_json` structuré.
- **FR-006** : Le pipeline F14 DOIT reconnaître un payload structuré et l'injecter au LLM dans un format normalisé sans réinterprétation textuelle.
- **FR-007** : La bascule "Répondre librement" DOIT émettre un événement `bottom_sheet_dismissed_for_freetext` ; le prochain message texte DOIT être re-classifié.
- **FR-008** : La validation côté client DOIT être miroir des schémas serveur (échec rapide avant envoi).
- **FR-009** : `ask_select` DOIT supporter `options_endpoint` pour charger des options paginées avec recherche, en consommant les endpoints catalogue F08/F09.
- **FR-010** : `ask_file_upload` DOIT déléguer l'upload aux endpoints existants F12 (documents projet) ou F22 (documents entreprise) et inclure `document_id` dans la réponse.
- **FR-011** : Aucun composant interactif NE DOIT être rendu inline dans la bulle LLM (règle UX : haut = LLM, bas = utilisateur).
- **FR-012** : L'animation d'apparition/disparition du bottom sheet DOIT durer < 200 ms.
- **FR-013** : Le bottom sheet DOIT être responsive : ~70 % de la hauteur sur mobile, hauteur fluide sur desktop.
- **FR-014** : Le bottom sheet DOIT respecter ARIA `role="dialog"` ou `role="form"`, focus trap, ESC ferme et bascule en libre.
- **FR-015** : Tout `label`/`description` issu du LLM DOIT être sanitizé (anti-XSS) avant rendu.
- **FR-016** : Les payloads DOIVENT être journalisés dans le système d'audit F04 (qui invoque, quel tool, quelle réponse).
- **FR-017** : RLS account_id DOIT être appliqué sur tout accès `chat_message` (cohérent F02/F13).

### Key Entities

- **chat_message** (existant F13) : `payload_json` (JSONB) accueille la structure `{tool, value/values, label/labels, ...}`. `content` reste un texte lisible.
- **tool_registry entry** (F14) : chaque tool de F15 enrichit le registre avec son schéma Pydantic, sa catégorie ("response"), et son métadata d'invocation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : 100 % des invocations `ask_qcu` aboutissent à un message utilisateur structuré en base sur 5 cas tests automatisés.
- **SC-002** : Bascule "Répondre librement" disponible dans 100 % des bottom sheets ; après bascule, l'input texte est ré-affiché en < 200 ms.
- **SC-003** : `ask_select` avec `options_endpoint` charge 100 options paginées et la recherche retourne des résultats en < 500 ms perçus.
- **SC-004** : `show_summary_card` permet de valider/corriger une extraction OCR sur 3 documents tests issus de F22.
- **SC-005** : Couverture de tests ≥ 80 % sur le code F15 ajouté (orchestrator/tools + composants Vue).
- **SC-006** : Aucune régression sur F13/F14 (suite tests existante verte).
- **SC-007** : 0 fuite XSS détectée sur un set de 10 payloads malicieux injectés dans `label`/`description`.

## Assumptions

- F13 (chat) et F14 (orchestrator + tool_registry) sont mergés et stables ; le décorateur `@tool` est l'unique point d'enregistrement.
- `chat_message.payload_json` (JSONB) est déjà en place (F13).
- L'endpoint POST `/me/chat/threads/{id}/messages` accepte `payload_json` (sinon, extension mineure dans cette feature).
- Les endpoints documents F12/F22 et catalogue F08/F09 sont opérationnels.
- gsap et Tailwind v4 sont disponibles dans le frontend Nuxt 4 (F01).
- La conversion FCFA↔EUR (Money) est fournie par F05.
- L'audit F04 et le RLS F02 s'appliquent automatiquement sur les nouveaux messages (héritage F13).
- MVP P1 prioritaire : `ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_file_upload`, `show_summary_card`, bascule libre, traçabilité. P2 (`ask_date*`, `ask_rating`, `show_form`) peuvent être livrés partiellement ou différés.
- La virtualisation des listes très longues (>500) peut être livrée en seconde itération si dépassement budget.
