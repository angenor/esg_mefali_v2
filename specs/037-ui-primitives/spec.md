# Feature Specification: UI Primitives Library (F37)

**Feature Branch**: `037-ui-primitives`
**Created**: 2026-05-02
**Status**: Draft
**Input**: User description: "@docs_et_brouillons/features/37-ui-primitives.md"

## User Scenarios & Testing *(mandatory)*

Cette feature livre une bibliothèque d'**atomes UI maison** (≈27 composants) consommée par toutes les autres features (chat bottom-sheets F15, formulaires candidatures F26, dashboards F32, back-office F06+F20, extension F33–F34, attestations publiques F30…). Les utilisateurs finaux (PME et Admin) n'interagissent pas directement avec la « library » — ils en bénéficient via chaque page qui l'utilise. Les user stories ci-dessous sont donc cadrées **du point de vue des deux personas qui en dépendent** :

- **Développeur produit ESG Mefali** (interne, premier consommateur) : compose les primitives pour construire les pages des autres features sans réinventer un atome ni dépendre d'une lib UI tierce.
- **Utilisateur final PME / Admin** : reçoit une expérience cohérente (mêmes états, même focus, mêmes tap targets, même comportement clavier) quelle que soit la page.

### User Story 1 — Saisir un formulaire candidature accessible et sans friction (Priority: P1)

Une PME remplit un dossier de candidature à un appel de financement. Le formulaire enchaîne champs texte, sélecteurs, dates, multi-sélection de référentiels, upload de pièces. Chaque champ doit montrer son état (vide, focus, erreur, désactivé), garder une cible tactile confortable au mobile, et rester pilotable au clavier ou au lecteur d'écran sans surprise.

**Why this priority** : F37 n'a de valeur que si les primitives suffisent à monter une page complexe et critique de bout en bout. La candidature est le parcours le plus dense (texte + sélection + date + upload + soumission) — si elle passe, la quasi-totalité des autres écrans passe aussi. C'est la seule story qui valide *à elle seule* la maturité de la lib.

**Independent Test** : construire une page formulaire candidature de démonstration utilisant uniquement les primitives F37 + tokens F36. Un utilisateur clavier-uniquement et un utilisateur lecteur d'écran (VoiceOver/NVDA) doivent pouvoir parcourir, remplir, corriger une erreur et soumettre, sans aide souris et sans piège de focus. Un test mobile (375 px) doit montrer toutes les cibles tactiles ≥ 44 × 44 px.

**Acceptance Scenarios** :

1. **Given** un champ texte obligatoire vide, **When** la PME tente de soumettre, **Then** le champ affiche un message d'erreur lisible, le focus se positionne sur le premier champ en erreur, et le lecteur d'écran annonce l'erreur (`aria-invalid` + `aria-describedby`).
2. **Given** un sélecteur de référentiels avec 100+ options, **When** la PME tape 3 caractères, **Then** la liste se filtre, navigable au clavier (↑↓ Enter Esc), avec virtualisation pour rester fluide.
3. **Given** une zone d'upload, **When** la PME glisse 3 PDF + 1 fichier au format interdit, **Then** les 3 PDF montrent une progression individuelle avec retry possible, et le 4ᵉ est rejeté avec un message clair sans bloquer les autres.
4. **Given** un sélecteur de date, **When** la PME ouvre le picker au clavier, **Then** la navigation flèches/Enter fonctionne, locale FR (lundi en premier, format jj/mm/aaaa), et la fermeture par Esc rend le focus au champ.
5. **Given** un utilisateur ayant activé « réduire les animations », **When** une modal s'ouvre, **Then** la transition est instantanée (pas d'animation gsap) tout en conservant le piège de focus.

---

### User Story 2 — Construire la couche bottom-sheet du chat sans réinventer les atomes (Priority: P1)

Le chat IA (F15) impose que **toute saisie interactive** (radios, checkboxes, sliders, datepicker, upload, formulaires) se fasse dans une bottom-sheet animée — jamais dans la bulle LLM. Les développeurs produit doivent assembler ces sheets en composant les primitives F37, sans coder un input à la main et sans installer de lib UI tierce.

**Why this priority** : c'est le point de friction le plus visible de la plateforme — un atome manquant ou cassé bloque immédiatement F15, qui bloque F25–F29. La bottom-sheet elle-même appartient à F39, mais son **contenu** vient d'ici.

**Independent Test** : monter une fausse sheet « Renseigner votre chiffre d'affaires » combinant `Number` (FCFA + masque), `Select` (devise), `RadioGroup` (régime fiscal), `FormField` (label/helper/erreur), bouton de validation `loading`. La sheet doit fonctionner au clavier de bout en bout, valider via VeeValidate + zod, et exposer les events `update:modelValue` / `submit` attendus par F15.

**Acceptance Scenarios** :

1. **Given** un input numérique avec masque FCFA, **When** la PME tape « 1500000 », **Then** l'affichage devient « 1 500 000 FCFA » avec `font-variant-numeric: tabular-nums`, et la valeur exposée reste un nombre exploitable.
2. **Given** un bouton de soumission, **When** l'action est en cours, **Then** le bouton passe en état `loading` (spinner visible, libellé conservé pour les lecteurs d'écran, désactivation des clics répétés), sans changer de taille.
3. **Given** un `RadioGroup`, **When** on navigue au clavier, **Then** Tab entre/sort du groupe, ↑↓ change la sélection, et un seul élément est `tabindex=0` à la fois (pattern ARIA radiogroup).

---

### User Story 3 — Garder une expérience cohérente entre toutes les pages produit (Priority: P2)

Un utilisateur PME passe en quelques minutes du chat (F15) au dashboard (F32) à un dossier de candidature (F26) à une attestation publique (F30). Il s'attend à ce que les boutons, badges, tooltips, cartes, états de chargement, toasts se comportent et se ressemblent partout.

**Why this priority** : la cohérence renforce la confiance perçue. Sans lib unifiée, chaque feature dérive et la marque s'effrite. Cette story se vérifie une fois les autres features câblées, donc P2.

**Independent Test** : page `/dev/components` (DEV only) qui rend les 27 atomes dans toutes leurs variantes et tous leurs états (default / hover / focus / active / disabled / loading / error). Capture visuelle de référence + audit axe-core ⇒ 0 violation critique. Un développeur ouvre n'importe quelle page produit et reconnaît les mêmes composants au pixel près.

**Acceptance Scenarios** :

1. **Given** la page showcase, **When** elle est rendue, **Then** chaque atome apparaît au moins en variantes `size sm/md/lg` et en états `disabled`, `loading`, `error` quand applicables, sans erreur console.
2. **Given** un toast déclenché depuis n'importe quelle page, **When** plusieurs toasts s'empilent, **Then** ils respectent une file (max visible borné), s'auto-ferment après 5 s, et se ferment au swipe sur mobile.
3. **Given** un `Tooltip` ou `Popover`, **When** il s'ouvre près du bord d'écran, **Then** son placement est recalculé pour rester visible (logique de positionnement déléguée à la lib de positionnement, pas codée à la main).

---

### Edge Cases

- **Combobox vide** : aucune option ne match — afficher un état vide explicite (« Aucun résultat ») et garder le focus dans l'input.
- **File upload — réseau coupé en cours** : la barre de progression s'arrête, un bouton « Réessayer » apparaît par fichier, les autres fichiers réussis ne sont pas perdus.
- **Modal imbriquée** : ouvrir une modal depuis une modal doit empiler correctement le piège de focus et restaurer le focus à la modal parente à la fermeture.
- **Toast pendant Modal ouverte** : le toast reste visible (au-dessus de l'overlay) sans casser le focus trap de la modal.
- **DatePicker locale FR + valeur invalide saisie au clavier** : afficher une erreur sans modifier le `modelValue` jusqu'à correction.
- **RTL / locale future** : les composants doivent ne pas faire d'hypothèse `direction: ltr` codée en dur (préparation, pas livraison RTL en MVP).
- **`v-html` accidentel** : interdit sauf via une fonction de sanitization centralisée — toute PR introduisant un `v-html` brut doit échouer la revue.
- **Bundle bloat** : importer une primitive ne doit pas tirer toute la lib (auto-imports tree-shakable côté Nuxt 4).
- **Réduction des animations système** : tous les composants animés (modal, toast, popover, skeleton shimmer) doivent court-circuiter gsap si l'utilisateur a activé `prefers-reduced-motion`.
- **Composant en train de fetch** : interdit — un atome qui fait un appel réseau à l'intérieur de son template doit être refusé (les données viennent toujours du parent).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : La bibliothèque DOIT fournir 27 atomes UI couvrant : action (`Button`), saisie texte/nombre (`Input`, `Textarea`, `Number`), sélection (`Select`, `Combobox`, `MultiSelect`, `RadioGroup`, `CheckboxGroup`, `Switch`), dates (`DatePicker`, `DateRangePicker`), valeur continue (`Slider`), surfaces et overlays (`Modal`, `Tooltip`, `Popover`, `Toast`), affichage (`Card`, `Badge`, `Tag`, `Avatar`, `EmptyState`), feedback (`Skeleton`, `Spinner`, `Progress`), composition de formulaire (`FormField`), upload (`FileUpload`).
- **FR-002** : Chaque atome DOIT être disponible en auto-import sous un préfixe `Ui` unique (`UiButton`, `UiInput`, …) sans configuration manuelle par feature.
- **FR-003** : Les atomes ayant une notion de taille DOIVENT exposer un contrat `size` à trois valeurs (`sm`, `md`, `lg`), avec `md` comme défaut.
- **FR-004** : Les atomes ayant un état désactivé/lecture seule DOIVENT exposer `disabled` et, le cas échéant, `readonly` ; le rendu visuel et le comportement clavier/AT DOIVENT refléter ces états.
- **FR-005** : Les atomes émettant une valeur DOIVENT utiliser des events nommés explicitement (`update:modelValue`, `submit`, `change`, `select`, `dismiss`). Aucun event opaque (`@input` brut sans sémantique) accepté.
- **FR-006** : Aucun atome NE DOIT effectuer d'appel réseau ; toutes les données (options, async loaders, fichiers à valider) DOIVENT être fournies par le parent via props ou composables.
- **FR-007** : Tous les atomes DOIVENT supporter le `ref` forwarding pour autoriser un focus programmatique depuis le parent (notamment pour la gestion des erreurs de formulaire).
- **FR-008** : Une page interne `/dev/components`, accessible uniquement en environnement DEV, DOIT afficher chaque atome dans ses variantes et ses états (default / hover / focus / disabled / loading / error), avec contrôles permettant de modifier les props.
- **FR-009** : `Button` DOIT supporter les variantes `primary`, `secondary`, `ghost`, `danger`, `link`, un état `loading` (avec spinner et préservation du libellé pour les lecteurs d'écran) et un slot icône.
- **FR-010** : `Input` / `Textarea` / `Number` DOIVENT supporter label flottant, message d'aide (helper), état d'erreur, et compteur de caractères optionnel ; `Number` DOIT utiliser `font-variant-numeric: tabular-nums` et accepter un slot d'unité ainsi qu'un masque optionnel pour FCFA et EUR.
- **FR-011** : `Combobox` DOIT supporter une recherche locale, un mode async paginé (compatible avec les `options_endpoint` standardisés du back-office), et virtualiser le rendu au-delà de 100 options.
- **FR-012** : `MultiSelect` DOIT afficher la sélection sous forme de chips supprimables et exposer un raccourci clavier de suppression (Backspace sur input vide).
- **FR-013** : `RadioGroup`, `CheckboxGroup`, `Switch` DOIVENT respecter une cible tactile minimale de 44 × 44 px en viewport mobile et un focus visible conforme au niveau d'accessibilité visé (cf. NFR/SC dédiés).
- **FR-014** : `DatePicker` DOIT s'appuyer en priorité sur l'input natif, avec fallback custom pour `DateRangePicker` ; locale FR par défaut (semaine commençant lundi, format jj/mm/aaaa).
- **FR-015** : `Modal` DOIT implémenter un piège de focus, fermeture ESC, fermeture par clic sur overlay (configurable), restauration du focus à l'élément déclencheur, et gérer correctement l'empilement de modales imbriquées.
- **FR-016** : `Tooltip` et `Popover` DOIVENT recalculer leur placement pour rester visibles dans le viewport (utilisation d'une lib de positionnement standard, pas de calcul custom).
- **FR-017** : `Toast` DOIT supporter une file empilable bornée, auto-dismiss configurable (défaut 5 s), fermeture manuelle, fermeture au swipe sur mobile, et rester visible au-dessus d'une `Modal` ouverte sans casser son piège de focus.
- **FR-018** : `FormField` DOIT composer label + input + helper + erreur autour d'un atome de saisie, propager `aria-invalid`, `aria-describedby`, et permettre la validation déclarative côté parent (compatible VeeValidate + zod).
- **FR-019** : `FileUpload` DOIT supporter drag & drop et clic, multi-fichier, prévisualisation miniature pour les images, progression par fichier, retry par fichier en cas d'échec, whitelist MIME et taille maximale paramétrables, et émettre des events explicites `add`, `remove`, `progress`, `success`, `error` par fichier.
- **FR-020** : Aucune primitive NE DOIT utiliser `v-html` sauf à passer par une fonction de sanitization centralisée du projet ; les exceptions DOIVENT être documentées au cas par cas.
- **FR-021** : Toutes les animations (modal, toast, popover, skeleton shimmer, transitions stylisées) DOIVENT court-circuiter ou se réduire à un état statique lorsque `prefers-reduced-motion` est actif.
- **FR-022** : Les libellés et messages par défaut (placeholders, « Aucun résultat », « Réessayer », « Fichier trop volumineux », etc.) DOIVENT être en français, et chaque atome DOIT permettre l'override via props/slots pour rester traduisible.
- **FR-023** : Les primitives DOIVENT consommer exclusivement les tokens de design issus de F36 (couleurs, espacements, typographie, rayons, ombres) — aucune valeur magique en dur dans les composants.
- **FR-024** : Les noms de props publiques de chaque atome DOIVENT être figés avant toute consommation par plus d'une feature aval (verrouillage du contrat d'API pour éviter une cascade de refactos).

### Key Entities

Cette feature ne crée pas d'entités métier. Elle introduit des **contrats de composants** stables :

- **Atome UI** : composant Vue auto-importé sous le préfixe `Ui`, contrat composé de `props` (typées), `events` (nommés), `slots` (nommés), exposition de `ref` ; aucune dépendance directe à une donnée métier.
- **FormField** : enveloppe d'un atome de saisie qui porte la sémantique d'erreur/aide/label et la liaison validation.
- **Toast queue** : registre runtime, partagé à l'échelle de l'app, qui ordonne et borne les toasts affichés.
- **Showcase `/dev/components`** : surface DEV-only qui inventorie les atomes et leurs états ; sert de référence visuelle et de support de tests d'accessibilité automatisés.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une page formulaire représentative (cf. User Story 1) est entièrement construite avec les primitives F37, sans aucune lib UI tierce ni atome local ad hoc.
- **SC-002** : Sur la page showcase `/dev/components`, un audit d'accessibilité automatisé renvoie **zéro violation de niveau critique ou sérieux**.
- **SC-003** : Sur la page showcase, un parcours clavier complet (Tab, Shift+Tab, Enter, Esc, ↑↓) atteint et active **100 %** des contrôles interactifs sans piège de focus.
- **SC-004** : Sur viewport mobile (largeur ≤ 375 px), **100 %** des contrôles interactifs (boutons, radios, checkboxes, switches, items de combobox) ont une cible tactile ≥ 44 × 44 px mesurée.
- **SC-005** : La couverture de tests unitaires sur les fichiers d'atomes UI atteint **≥ 80 %** lignes/branches, et les tests couvrent au minimum : rendu par défaut, chaque variante de prop, chaque event émis, attributs ARIA pertinents.
- **SC-006** : La page de connexion (`/login`), une fois rebâtie sur les primitives effectivement utilisées, conserve un poids JavaScript **< 60 kB gzippés** pour la part imputable aux primitives.
- **SC-007** : Les 27 atomes annoncés sont rendus simultanément sur la page showcase **sans aucune erreur ni warning console** (Vue, accessibilité, hydratation Nuxt).
- **SC-008** : Un développeur produit qui adopte la lib peut composer une nouvelle page de saisie de bout en bout (champs, validation, submit, feedback) **sans introduire de nouveau composant UI hors du dossier des primitives** — vérifié par revue de code sur les premières features consommatrices.
- **SC-009** : Un test manuel sur lecteur d'écran (VoiceOver macOS ou NVDA Windows) couvrant Modal et Combobox confirme une expérience vocale cohérente : ouverture annoncée, options annoncées, fermeture annoncée, retour de focus correct.

## Assumptions

- **Dépendance F36** : les tokens de design (couleurs, typographie, espacements, rayons, ombres, breakpoints) issus de F36 sont disponibles et stables au moment d'attaquer F37. Aucune valeur de design n'est hardcodée dans les primitives.
- **Pas de bottom-sheet ici** : le composant `BottomSheet` lui-même est livré par F39. F37 fournit uniquement les atomes que la sheet contiendra.
- **Pas de charts ni de chat** : les composants `Chart` (F40) et `Chat` (F41) sont hors scope.
- **Pas de drag-reorder ni de TanStack Table** : explicitement post-MVP, exclus de F37.
- **Validation déclarative déléguée** : la validation des formulaires repose sur la pile standard du projet (VeeValidate + zod) ; F37 fournit les hooks de présentation (états `error`, `aria-invalid`, `aria-describedby`) et **n'embarque pas** sa propre logique de validation.
- **Positionnement délégué** : le placement de `Tooltip` et `Popover` repose sur une lib de positionnement standard (Floating UI ou équivalent), pas sur du code custom — réduit le risque d'instabilité visuelle.
- **Animation library** : les animations s'appuient sur la lib d'animation déjà adoptée par le projet (gsap), avec respect strict de `prefers-reduced-motion` via un composable partagé (`useReducedMotion`, déjà présent).
- **Sanitization** : un utilitaire de sanitization centralisé (DOMPurify ou équivalent déjà adopté) existe ou sera ajouté en parallèle pour couvrir le seul usage `v-html` autorisé.
- **Locale par défaut FR** : tous les libellés par défaut sont en français ; l'i18n complète (Wolof, Bambara…) est post-MVP, mais les atomes ne câblent rien en dur qui empêche un override de libellé.
- **Public cible des tests d'accessibilité** : conformité visée niveau AA (focus ring, contraste, ARIA), validée par un audit automatisé + un passage manuel lecteur d'écran sur Modal et Combobox.
- **Stabilité d'API** : le contrat de props/events des atomes est gelé avant qu'une feature aval ne dépende massivement d'eux ; tout changement passe par une procédure de versionnage interne.
- **Référence inspiration** : le modèle `shadcn/ui` côté Vue inspire l'approche « on possède le code des atomes » — pas de wrapping d'une lib tierce.
