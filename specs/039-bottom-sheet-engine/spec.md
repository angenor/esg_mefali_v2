# Feature Specification: Bottom Sheet Engine (UI des tools `ask_*`)

**Feature Branch**: `039-bottom-sheet-engine`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F39 — Bottom Sheet Engine, UI front-end pour les tools LLM ask_qcu, ask_qcm, ask_yes_no, ask_select, ask_number, ask_date, ask_rating, ask_file_upload, show_form, show_summary_card. Concrétise la règle constitutionnelle P10 : tout input interactif vit dans un bottom sheet animé en gsap, jamais inline dans une bulle LLM. Bouton 'Répondre librement' toujours visible."

## Clarifications

### Session 2026-05-03

- Q: Que devient un bottom sheet ouvert si la PME recharge la page, navigue ailleurs ou perd la connexion ? → A: Éphémère côté client ; au retour, le dernier message tool non répondu du thread réaffiche son sheet (reconstitution depuis la DB). Aucune saisie partielle persistée localement.
- Q: Que fait l'action « Corriger » d'un `show_summary_card` ? → A: Correction libre : ferme le sheet et bascule en saisie texte libre (équivalent fonctionnel de « Répondre librement »), avec un événement structuré `{action: "correct"}` pour signaler au LLM que c'est une correction du récap (et non une nouvelle question). La PME formule la correction en langage naturel ; le LLM décide ensuite quel(s) tool(s) relancer.
- Q: Quelles devises l'UI `ask_number` (mode `money`) doit-elle gérer au MVP ? → A: MVP = XOF (FCFA) ↔ EUR uniquement, avec conversion live au peg fixe sourcé `655.957`. Autres devises (USD, etc.) acceptées en saisie sans conversion affichée — déléguées au backend. USD avec `fx_rate` = post-MVP.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Orchestrateur de bottom sheet (Priority: P1)

Quand le LLM décide d'appeler un tool d'interaction (par ex. `ask_qcu`), le frontend reçoit une instruction `{tool, payload}` et doit présenter à la PME un panneau de saisie ad hoc, animé, qui remplace temporairement la barre de saisie texte. La PME peut soit répondre via les contrôles (radios, checkboxes, sélecteur, etc.), soit basculer en réponse libre via un bouton sticky « Répondre librement ». À la soumission, la valeur structurée est renvoyée au backend, et le bottom sheet se ferme avec une animation de sortie.

**Why this priority**: C'est l'ossature commune à tous les tools `ask_*` et `show_*`. Sans cet orchestrateur, aucun tool d'interaction du F15 ne peut s'afficher côté PME, et la règle constitutionnelle P10 (jamais d'input inline) ne peut être respectée. Toutes les autres User Stories en dépendent.

**Independent Test**: Mocker un appel `{tool: "ask_yes_no", payload: {question: "Êtes-vous une SARL ?"}}` côté chat, observer l'apparition animée du bottom sheet sous 200 ms perçues, valider qu'un clic « Oui » émet l'événement `submit` avec un payload conforme et ferme le panneau, qu'une touche `ESC` ou un clic « Répondre librement » bascule l'utilisateur vers l'input texte libre, et que la barre de saisie texte est désactivée tant que le sheet est ouvert.

**Acceptance Scenarios**:

1. **Given** la PME est dans un thread de chat avec barre de saisie texte active, **When** le LLM émet une instruction de tool d'interaction, **Then** un bottom sheet apparaît animé (slide-up ~200 ms, ease-out), la barre de saisie texte se grise/désactive, et le focus clavier passe dans le sheet.
2. **Given** un bottom sheet est ouvert, **When** la PME appuie sur `ESC` ou clique « Répondre librement », **Then** le sheet se ferme animé (slide-down ~160 ms, ease-in), la barre de saisie texte redevient active et focusée, et un événement `dismiss-for-freetext` est émis pour que l'orchestrateur LLM (F14) reclassifie le prochain message texte.
3. **Given** un bottom sheet est ouvert et la PME complète sa saisie, **When** elle clique « Valider », **Then** un message structuré est posté côté backend avec un récap textuel humain (ex. « ✓ Oui ») et le payload typé `{tool, value, label}`, le sheet se ferme, et la barre de saisie redevient active.
4. **Given** la préférence utilisateur ou système est « reduced motion », **When** un bottom sheet doit s'ouvrir, **Then** les animations sont neutralisées et le sheet apparaît sans transition perceptible (mais reste fonctionnel et focusable).

---

### User Story 2 — Wrappers de saisie courants (QCU, QCM, Oui/Non, Select, Number, Date, FileUpload) (Priority: P1)

Pour chaque tool de saisie standard du F15, un wrapper UI dédié compose les primitives F37 dans le bottom sheet et applique les contraintes du payload backend (bornes numériques, `min/max_select`, options synchrones ou paginées, locale FR pour dates, unités monétaires avec peg FCFA-EUR fixe, upload de fichier rattaché à entreprise ou projet).

**Why this priority**: Ces wrappers couvrent ~95 % des interactions LLM du MVP (collecte de profil entreprise, projet, données ESG, OCR de pièces, scoring). Sans eux, le LLM ne peut pas mener un dialogue structuré.

**Independent Test**: Pour chaque wrapper, écrire un test d'unité front qui (a) rend le composant à partir d'un payload type, (b) interagit (clic radio, cocher case, taper un nombre, choisir une date, uploader un fichier mocké), (c) tente une soumission invalide et vérifie que « Valider » est bloqué avec un message clair, (d) soumet une valeur valide et vérifie le payload émis.

**Acceptance Scenarios**:

1. **Given** un payload `ask_qcu` avec 4 options et une option « Autre », **When** la PME sélectionne « Autre », **Then** un input texte additionnel apparaît, le bouton « Valider » reste bloqué tant qu'aucun texte n'est saisi, et la soumission renvoie `{value: "autre", label: "<texte saisi>"}`.
2. **Given** un payload `ask_qcm` avec `min_select=2, max_select=3`, **When** la PME coche 1 ou 4 options, **Then** « Valider » est désactivé et un compteur « X sur N sélectionnés (min 2, max 3) » s'affiche ; à 2 ou 3 options cochées, « Valider » s'active.
3. **Given** un payload `ask_select` avec une source de 200 pays paginés, **When** le sheet s'ouvre, **Then** une zone de recherche reçoit le focus, la liste est virtualisée (60 fps en scroll), les flèches `↑/↓` naviguent et `Entrée` valide la sélection courante, `ESC` ferme le sheet.
4. **Given** un payload `ask_number` avec unité `FCFA` et `money: {currency: "XOF"}`, **When** la PME saisit un montant, **Then** la conversion live FCFA↔EUR s'affiche au peg fixe sourcé `655.957`, les bornes `min/max` du payload sont appliquées par l'UI (saisie hors-bornes refusée).
5. **Given** un payload `ask_date` ou `ask_date_range`, **When** la PME ouvre le calendrier, **Then** la locale est française avec semaine commençant le lundi et noms de mois/jours en français.
6. **Given** un payload `ask_file_upload` avec `attach_to: "entreprise"` (ou `"projet"`), **When** la PME dépose un PDF de 5 Mo, **Then** le fichier est uploadé sur l'endpoint correspondant (F22 documents entreprise ou F12 projet), un état de progression visible, et la soumission renvoie `{doc_id, filename, mime, size}`.

---

### User Story 3 — Récap structuré et rendu de formulaire (`show_summary_card`, `show_form`) (Priority: P2)

Le LLM peut présenter un récapitulatif valider/corriger/annuler (par ex. après OCR d'un Kbis, ou avant de figer une candidature), ou un formulaire multi-champs typé dont la validation est dérivée du schéma Pydantic backend.

**Why this priority**: Indispensable pour les flux où le LLM consolide plusieurs données avant écriture, mais arrive après les saisies atomiques. `show_summary_card` est P1 fonctionnel mais ne bloque pas l'usage des Ask\*, donc P2 ici en priorité d'implémentation.

**Independent Test**: Mocker un payload `show_summary_card` avec 5 champs `{label, value, source?}` ; vérifier que les 3 actions « Valider | Corriger | Annuler » émettent des événements distincts ; vérifier qu'un payload `show_form` avec 4 champs typés (texte, nombre, date, select) génère un schéma de validation équivalent au schéma Pydantic et bloque la soumission tant qu'un champ requis est invalide.

**Acceptance Scenarios**:

1. **Given** un `show_summary_card` avec 5 lignes dont 2 portent une référence de source, **When** le sheet s'affiche, **Then** chaque source apparaît visuellement attachée à sa valeur (lien/badge non interactif côté MVP) et l'utilisateur peut « Valider » (clôt le récap), « Corriger » (ferme le sheet et bascule en saisie texte libre avec `{action: "correct"}`) ou « Annuler ».
2. **Given** un `show_form` multi-champs, **When** la PME soumet, **Then** la validation côté UI est conforme au schéma Pydantic généré, les erreurs s'affichent par champ en français, et la soumission n'a lieu qu'une fois tous les champs valides.

---

### User Story 4 — Notation 1-5 ou 1-10 (`ask_rating`) (Priority: P3)

Pour les questions d'auto-évaluation (par ex. « Sur une échelle de 1 à 5, quelle est votre maturité ESG ? »), un wrapper d'étoiles ou d'échelle numérique apparaît dans le sheet, navigable au clavier (touches `1` à `0`).

**Why this priority**: Faible volume d'usage attendu en MVP (auto-évaluation maturité, satisfaction). Implémentable après les Ask\* prioritaires.

**Independent Test**: Rendre un `ask_rating` `{scale: 5}`, valider que les touches `1`–`5` sélectionnent la note correspondante, que `Entrée` soumet, et que la soumission renvoie `{value: <int>}`.

**Acceptance Scenarios**:

1. **Given** un `ask_rating` `{scale: 10}`, **When** la PME appuie sur `0`, **Then** la note 10 est sélectionnée (convention MVP), affichée visuellement, et « Valider » s'active.

---

### Edge Cases

- **Désactivation visuelle de la barre texte** : le visuel doit clairement indiquer qu'elle est inactive (couleur, opacité, curseur), pour éviter que la PME tape dans le vide.
- **Conflit de focus** : un focus trap est en place ; `Tab` ne sort pas du sheet tant qu'il est ouvert ; le focus retourne au déclencheur logique (barre de saisie) à la fermeture.
- **XSS sur `label`/`description`** : tout texte d'option ou de description venant du backend (donc potentiellement issu d'une source externe en aval) est sanitizé avant rendu HTML — un payload contenant `<script>alert(1)</script>` ne déclenche aucun script et s'affiche échappé.
- **Échec d'upload (`ask_file_upload`)** : timeout réseau, fichier trop gros, MIME refusé → l'utilisateur voit un message d'erreur en français, le sheet reste ouvert pour réessayer, et un événement structuré (`{tool: "ask_file_upload", error: <code>}`) est renvoyé au LLM si la PME annule pour qu'il puisse adapter sa réponse.
- **Double soumission** : `Valider` se désactive immédiatement à la première soumission jusqu'à confirmation backend ; un second `Entrée` ne déclenche pas un second appel.
- **Listes virtualisées hors viewport** : la navigation clavier `↑/↓` doit faire défiler la liste virtualisée pour garder l'item actif visible, même au-delà de la fenêtre de rendu.
- **Reclassification après bascule libre** : la mention « Vous répondez librement » doit indiquer brièvement à la PME que sa prochaine phrase sera ré-interprétée par le LLM, pour éviter qu'elle s'attende à un retour en QCU.
- **Submit pendant fermeture en cours** : si la PME submit alors qu'une animation de fermeture est déjà déclenchée (par ESC + clic rapide), un seul payload est envoyé (déduplication par état interne).
- **Mobile très petit (< 360 px)** : le sheet occupe toute la hauteur utile sans déborder ; les listes longues restent scrollables au doigt sans masquer la zone de saisie ni le bouton « Répondre librement ».

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (P10)** : Tout tool d'interaction LLM (`ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`, `ask_date_range`, `ask_rating`, `ask_file_upload`, `show_form`, `show_summary_card`) MUST se rendre exclusivement dans un bottom sheet et JAMAIS inline dans une bulle de chat.
- **FR-002** : Un orchestrateur unique MUST recevoir une instruction `{tool, payload}` et monter dynamiquement le wrapper correspondant ; un seul sheet peut être ouvert à la fois.
- **FR-003** : Tant qu'un sheet est ouvert, la barre de saisie texte du chat MUST être désactivée visuellement et fonctionnellement.
- **FR-004** : Un bouton « Répondre librement » MUST être visible et atteignable à tout moment dans le sheet, et MUST émettre un événement permettant au pipeline d'orchestration LLM de reclassifier la prochaine entrée texte.
- **FR-005** : `ESC` MUST fermer le sheet et basculer en saisie libre, équivalent au bouton « Répondre librement ».
- **FR-006** : Chaque wrapper MUST appliquer côté UI les contraintes du payload (bornes numériques, `min_select`/`max_select`, options exclusives/multiples, formats de date, MIME et taille de fichier).
- **FR-007** : `ask_qcu` MUST supporter une option « Autre » optionnelle qui ouvre un champ texte libre additionnel, requis si « Autre » est sélectionnée.
- **FR-008** : `ask_select` MUST supporter une source d'options synchrone OU asynchrone paginée, avec recherche en focus auto, virtualisation des listes longues, et navigation clavier (`↑`/`↓`/`Entrée`/`ESC`).
- **FR-009** : `ask_number` MUST afficher l'unité (`tCO2e`, `FCFA`, `XOF`, `EUR`, `%`, etc.). Lorsque le payload spécifie `money: {currency: "XOF"}` ou `money: {currency: "EUR"}`, l'UI MUST afficher la conversion live XOF↔EUR au peg fixe sourcé `655.957` (constante backend, P1/P5). Pour toute autre devise (USD, etc.) au MVP, la valeur est saisie sans conversion live affichée — la conversion est déléguée au backend. Le support de USD avec `fx_rate` quotidien est hors-scope MVP.
- **FR-010** : `ask_date` et `ask_date_range` MUST utiliser la locale française avec lundi en premier jour de semaine.
- **FR-011** : `ask_file_upload` MUST router l'upload vers l'endpoint correspondant à la cible `attach_to` (entreprise ou projet) et restituer `{doc_id, filename, mime, size}` à la soumission.
- **FR-012** : À la soumission, le sheet MUST poster côté backend un message de chat dont le contenu textuel est un récap humain (ex. « ✓ SARL », « ✓ 2 options », « ✓ Document chargé »), accompagné d'un payload structuré `{tool, value, label}` et d'un contexte (id du tool d'origine, thread).
- **FR-013** : `show_summary_card` MUST exposer trois actions distinctes émettant chacune un événement explicite et fermant le sheet :
  - **Valider** → `{action: "validate"}` ; la barre de saisie texte se réactive, le LLM enchaîne.
  - **Corriger** → `{action: "correct"}` ; le sheet se ferme et la PME bascule en saisie texte libre (même comportement que « Répondre librement ») pour formuler la correction en langage naturel ; le LLM est responsable de reclassifier la prochaine entrée comme correction du récap et de relancer le ou les tools pertinents.
  - **Annuler** → `{action: "cancel"}` ; le sheet se ferme, aucune écriture, le LLM décide de la suite.
- **FR-014** : Les schémas de validation des Ask\* et de `show_form` MUST être dérivés du contrat Pydantic backend (génération automatique au build) afin qu'aucune divergence UI/backend ne soit possible.
- **FR-015** : Tout texte exogène (`label`, `description`, options) MUST être sanitizé avant rendu pour empêcher l'injection HTML/JS.
- **FR-016** : Un focus trap MUST être actif tant que le sheet est ouvert ; à la fermeture, le focus MUST revenir à la barre de saisie texte.
- **FR-017** : Les animations d'entrée (~200 ms) et de sortie (~160 ms) MUST être neutralisées si la préférence utilisateur ou système indique « reduced motion ».
- **FR-018** : Une double soumission MUST être impossible : le bouton « Valider » se désactive immédiatement après le premier clic et reste désactivé jusqu'à confirmation ou erreur backend.
- **FR-019** : En cas d'erreur d'upload ou réseau dans `ask_file_upload`, l'UI MUST afficher un message d'erreur clair en français et permettre de réessayer sans rouvrir le sheet ; si la PME annule, un événement structuré est renvoyé au LLM pour qu'il adapte sa réponse.
- **FR-020 (Persistance)** : L'état d'un sheet ouvert MUST être éphémère côté client (aucune saisie partielle persistée en local). Au chargement d'un thread, si le dernier message tool est non répondu, le sheet correspondant MUST être reconstitué automatiquement à partir du payload stocké en base, dans le même état initial qu'à sa première ouverture.

### Non-Functional Requirements

- **NFR-001 (Performance)** : L'apparition d'un sheet MUST être perçue par l'utilisateur en moins de 200 ms après réception de l'instruction du LLM côté frontend.
- **NFR-002 (Layout)** : Sur mobile, le sheet occupe environ 70 % de la hauteur viewport ; sur desktop, il est dimensionné fluide jusqu'à 60 % max.
- **NFR-003 (Sécurité)** : Aucune chaîne contrôlée par le payload ne doit pouvoir exécuter de script (test : `<script>alert(1)</script>` rendu textuellement).
- **NFR-004 (Listes)** : Les listes au-delà de 50 options MUST être virtualisées et conserver une fluidité de défilement perçue à 60 fps.
- **NFR-005 (Accessibilité)** : Focus trap, navigation clavier, ESC, libellés ARIA appropriés sur chaque wrapper, contraste conforme aux exigences du design system.

### Key Entities

- **Instruction de tool LLM** : objet `{tool: string, payload: object, context: object}` reçu côté chat, identifie le wrapper à monter.
- **Payload de saisie** : objet typé propre à chaque tool, dérivé du schéma Pydantic backend (ex. `ask_qcu` → `{question, options[], allow_other}`).
- **Réponse structurée** : objet `{tool, value, label, ...metadata}` posté en réponse, accompagné d'un récap textuel humain pour l'historique du thread.
- **Document uploadé** (issu de `ask_file_upload`) : `{doc_id, filename, mime, size}` rattaché soit à l'entreprise soit au projet selon `attach_to`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur 5 cas tests représentatifs (5 tools `ask_*` distincts), 100 % des invocations LLM aboutissent à un message structuré en base de données conforme au contrat backend, sans intervention manuelle.
- **SC-002** : Sur un échantillon de 10 sessions de test utilisateur, 100 % des PME parviennent à basculer en réponse libre via le bouton dédié et à voir le LLM reclassifier correctement leur message suivant.
- **SC-003** : `ask_select` charge et affiche fluidement (perception 60 fps en scroll/recherche) une liste de 200 pays paginés, avec un temps perçu de premier rendu < 200 ms.
- **SC-004** : `show_summary_card` permet à 95 % des PME testées de valider ou corriger un récap OCR sans assistance, avec un taux de réussite de premier essai mesuré sur le golden set d'éval LLM (F35).
- **SC-005** : `ask_file_upload` traite un PDF de 5 Mo en moins de 5 secondes (réseau standard FR), avec un taux de succès supérieur à 99 % hors panne backend, et restitue un `doc_id` exploitable.
- **SC-006** : Aucun cas d'XSS détecté sur le payload via le test automatisé d'injection (chaîne `<script>alert(1)</script>` injectée dans `label`/`description` de chaque wrapper rendue textuellement, jamais exécutée).
- **SC-007** : 0 cas de double soumission observé sur 1000 cycles de test automatisés combinant clic et touche `Entrée` rapprochés.

## Assumptions

- Les contrats Pydantic des tools `ask_*` / `show_*` sont définis et stabilisés par F15 ; cette feature consomme le contrat via génération de schémas (script de build dédié).
- Le pipeline d'orchestration LLM (F14) est responsable de la reclassification d'un message texte après bascule « Répondre librement » — le sheet émet l'événement et oublie le tool en cours.
- L'upload de fichier (`ask_file_upload`) s'appuie sur les endpoints existants F22 (documents entreprise) et F12 (projets) ; cette feature ne définit pas ces endpoints, elle les consomme.
- Les primitives de design F37 (`UiButton`, `UiInput`, `UiCheckbox`, `UiRadio`, `UiSelect`, `UiDatePicker`, `UiFileUpload`, `UiSlider`) sont disponibles et stables.
- Le shell d'application F38 (chat layout, slot pour bottom sheet, EventBus) est en place.
- Le peg FCFA-EUR fixe (`655.957`) est fourni par le backend comme constante sourcée (P5) et n'est pas dérivé côté frontend.
- La préférence « reduced motion » est lue via `prefers-reduced-motion` côté navigateur.
- Hors-scope MVP : tools custom par skill (F19/F20), wizard multi-étapes via tools chaînés (post-MVP), saisie vocale (post-MVP), édition d'un sheet déjà soumis (un nouveau tour LLM est requis pour corriger), conversion live USD avec `fx_rate` quotidien (post-MVP), persistance locale d'une saisie partielle non soumise.

## Dependencies

- **F15** — Contrats backend des tools `ask_*` / `show_*` (Pydantic, OpenAPI).
- **F14** — Orchestrateur LLM (classification, reclassification après bascule libre).
- **F37** — UI primitives (composants atomiques).
- **F38** — App shell et layout chat.
- **F22** — Endpoint documents entreprise (upload).
- **F12** — Endpoint projet (upload `attach_to: projet`).
- **F36** — Design tokens (animation, espacement, couleurs).
