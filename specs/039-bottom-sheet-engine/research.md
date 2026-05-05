# Research — F39 Bottom Sheet Engine

**Date** : 2026-05-03
**Statut** : Aucune `[NEEDS CLARIFICATION]` restante côté plan ; ce document consigne les décisions techniques pour l'implémentation.

## R1 — Animation : GSAP vs alternatives

- **Decision** : utiliser **GSAP 3.12** (déjà dans `frontend/package.json`) pour `slideUp` (200 ms ease-out) à l'entrée et `slideDown` (160 ms ease-in) à la sortie ; les paramètres exacts vivent dans `useBottomSheetAnimation.ts`. Neutralisation via `useReducedMotion` (déjà existant).
- **Rationale** : GSAP offre un timeline contrôlable (utile pour bloquer la double soumission pendant la fermeture, FR-018), gère proprement l'interruption (ESC en plein slideUp), et est déjà la convention du projet (mentionné dans la constitution P10 et CLAUDE.md). Pas de nouvelle dépendance.
- **Alternatives considérées** :
  - Transitions Vue natives + CSS keyframes : suffisant pour un slide, mais moins fin pour interruption et timeline ; nécessite un timing CSS dupliqué.
  - `@vueuse/motion` : abstraction supplémentaire ; n'apporte rien que GSAP ne fasse déjà.

## R2 — Génération des schémas zod depuis Pydantic

- **Decision** : ajouter un script `pnpm gen:tools` (`scripts/gen-tools.mjs`) qui consomme `/openapi.json` exposé par FastAPI, filtre les schémas dont `x-tool` est défini (convention introduite par F15), et produit un fichier TypeScript par tool dans `app/types/tools/` exportant : (a) un type `Payload`, (b) un type `Response`, (c) un schéma `zod` (via `json-schema-to-zod` ou réécriture manuelle si la lib échoue sur les enums fermés). Le script tourne en pré-build CI et localement avant chaque feature impactant les tools.
- **Rationale** : FR-014 impose la dérivation depuis Pydantic. Le backend FastAPI expose déjà l'OpenAPI complet sur `/openapi.json` ; partir de là évite toute duplication manuelle des contrats et aligne immédiatement le front sur tout changement backend (P9). `json-schema-to-zod` est maintenu, supporte enum/min/max, et restitue un schéma zod runtime utilisable par vee-validate.
- **Alternatives considérées** :
  - Maintenir manuellement les zod côté front : violerait FR-014 (divergence garantie à la première évolution backend).
  - Utiliser un format intermédiaire (TS interfaces seules sans validation runtime) : insuffisant car la validation doit tourner avant `submit` (FR-002, FR-006).
  - `openapi-zod-client` : génère un client complet, plus large que nécessaire ; on préfère un script ciblé.

## R3 — Virtualisation des longues listes (`ask_select`)

- **Decision** : adopter **`vue-virtual-scroller`** (RecycleScroller) pour toute liste > 50 options (NFR-004). Ajouter en dépendance `frontend/package.json` (≈ 30 ko gzip). Une recherche à focus auto filtre la liste avant virtualisation ; clavier ↑/↓ scrolle l'item actif dans la fenêtre visible.
- **Rationale** : NFR-004 et SC-003 requièrent 60 fps sur 200 pays. Sans virtualisation, 200 `<li>` rendus + DOMPurify sur les labels dégradent le scroll mobile. `vue-virtual-scroller` est mature, supporte la hauteur dynamique, et est compatible Vue 3.
- **Alternatives considérées** :
  - Pas de virtualisation < 200 items : risqué, car certaines listes (codes NAF, communes) dépassent et la limite (50) est dépassée fréquemment.
  - `@tanstack/vue-virtual` : excellent mais ajoute du boilerplate ; `vue-virtual-scroller` est plus directement plug-and-play.

## R4 — Sanitize XSS (FR-015, NFR-003)

- **Decision** : utiliser **DOMPurify 3.1** (déjà dépendance) pour tout texte payload rendu, via un util `utils/sanitize.ts`. Deux modes : `text(s)` (escape complet, défaut) et `safeHtml(s)` (autorise `<b>`, `<i>`, `<a href>` avec rel=noopener). Tous les wrappers utilisent `text` par défaut ; `show_summary_card` peut utiliser `safeHtml` pour des badges de source.
- **Rationale** : SC-006 exige zéro XSS détecté ; un util centralisé facilite l'audit et les tests.
- **Alternatives considérées** :
  - `v-text` natif Vue : protège du HTML mais empêche tout balisage (sources cliquables) ; trop restrictif pour `show_summary_card`.
  - sanitize manuel par regex : interdit (impossible à prouver sans faille).

## R5 — Reconstitution depuis le thread (Q1)

- **Decision** : la reconstitution s'appuie sur l'API existante `/me/chat/threads/{id}/messages` (F14). Au mount du chat ou au load d'un thread, le store `chatBottomSheet` lit le dernier message dont `role = "assistant"` ET `tool_call` non répondu (un message tool « pending »), et appelle `useChatBottomSheet().open(tool, payload, context)`. À la soumission, l'écriture du message PME résout le pending. Aucune saisie partielle n'est conservée localement.
- **Rationale** : Q1 a tranché pour l'option B. La DB reste source de vérité (P8), le state local est minimaliste, et le comportement est identique sur tous les devices/onglets.
- **Alternatives considérées** : voir spec § Clarifications Q1.

## R6 — Détection « tool en cours » côté thread

- **Decision** : le contrat F14/F15 (à confirmer dans `contracts/tool-payloads.md`) est : un message assistant avec `payload_json.tool` non NULL et **aucun message PME ultérieur dans le thread** est considéré « pending ». Le frontend reconstitue le sheet à partir de ce message. Le backend marque la résolution implicitement par l'`INSERT` du message PME suivant.
- **Rationale** : aucune nouvelle colonne ni état additionnel ; tout repose sur l'ordre des messages, déjà indexé.
- **Alternatives considérées** : ajouter une colonne `resolved_at` sur le message tool — plus explicite mais hors scope F39 (changement backend non justifié pour MVP).

## R7 — Soumission, déduplication et gestion d'erreurs

- **Decision** : un composable `useBottomSheetSubmit` encapsule l'appel POST. Un `inFlight` ref bloque toute deuxième invocation tant que la précédente n'a pas répondu (FR-018). En cas d'erreur HTTP non-2xx : afficher un toast (`UiToast`/`useToast` existant) et garder le sheet ouvert. En cas d'erreur réseau (offline) : message inline + retry manuel ; pas de retry automatique pour éviter les soumissions silencieuses.
- **Rationale** : SC-007 (zéro double soumission) exige un verrou local. La séparation submit/animation évite que le `slideDown` annule la requête en vol.
- **Alternatives considérées** : retry exponentiel automatique — rejeté car peut produire des doublons côté DB si la première requête a réussi mais la réponse a été perdue.

## R8 — Locale et formats date (FR-010)

- **Decision** : configurer `UiDatePicker` / `UiDateRangePicker` (F37) avec `locale="fr"` et `firstDayOfWeek=1` (lundi). Les libellés viennent de `Intl.DateTimeFormat('fr-FR')`. Aucune lib externe nouvelle.
- **Rationale** : conforme à la règle « FR par défaut » (CLAUDE.md). Les anglais éventuels (offres `accepted_languages='en'`) sont hors scope F39 (Assumption).
- **Alternatives considérées** : `dayjs` avec locale FR — ajoute du poids, sans bénéfice par rapport à `Intl`.

## R9 — Conversion FCFA↔EUR (FR-009)

- **Decision** : le peg `655.957` est exposé par le backend dans `/v1/config/peg-fcfa-eur` (endpoint à confirmer auprès de F15) ou, à défaut, codé en constante front avec attribution de source en commentaire pointant la migration backend qui le définit (P5 / source verified). Aucune dérivation client de taux. La conversion live se fait par `Decimal` (lib `decimal.js` si non encore présente — à valider) plutôt qu'en `number` IEEE-754.
- **Rationale** : P5 interdit `float` pour des montants. Le peg étant fixe, la précision suffit avec une multiplication entière + arrondi à 2 décimales pour l'affichage. Si `decimal.js` n'est pas dans le bundle, on peut implémenter une mini-fonction `xofToEur(amountString)` à base de `BigInt` pour garder la précision (préféré au MVP).
- **Alternatives considérées** : `bignumber.js` — surpoids ; `Number` — interdit par P5.

## R10 — Upload (`ask_file_upload`) routing

- **Decision** : `attach_to ∈ {"entreprise", "projet"}` route l'upload sur l'endpoint correspondant (F22 pour entreprise, F12 pour projet), via un mapping local `attachToEndpoint`. La progression utilise `XMLHttpRequest` (`progress` events) — `fetch` n'expose pas la progression d'upload de façon portable. À la réponse, on émet `{doc_id, filename, mime, size}`.
- **Rationale** : FR-011, SC-005. Routing local évite tout couplage du LLM avec la cible exacte.
- **Alternatives considérées** : utiliser `fetch` + `ReadableStream` pour la progression : non supporté de façon stable sur Safari mobile au moment de l'écriture.

## R11 — Focus trap et accessibilité

- **Decision** : utiliser le composable existant `useFocusTrap` (déjà présent) appliqué au root du sheet. À l'ouverture, focus sur le premier élément interactif ; à la fermeture, retour à la barre de saisie texte (réf récupérée via `useChatBottomSheet`). ARIA : `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (titre), `aria-describedby` si description.
- **Rationale** : NFR-005 + FR-016 + accessibilité.
- **Alternatives considérées** : `focus-trap` standalone — déjà capté par `useFocusTrap`.

## R12 — Tests : stratégie et couverture

- **Decision** : un test unitaire vitest **par wrapper** couvrant : (a) rendu initial avec un payload type, (b) interaction valide → `submit` payload conforme, (c) interaction invalide → `submit` bloqué, (d) ESC ferme + bascule libre, (e) injection `<script>alert(1)</script>` dans `label` → rendue textuellement. Un test d'intégration sur l'orchestrateur valide la reconstitution depuis un mock de thread + désactivation de la barre input. Cible coverage ≥ 80 % (cohérent avec la règle projet `fail_under = 80` côté backend, alignée côté front).
- **Rationale** : SC-001/002/006/007 nécessitent une preuve testable.
- **Alternatives considérées** : tests Playwright pour le rendu animé : rejeté en MVP (coût d'infra E2E pour une feature unitaire), reporté à F35 (eval LLM) ou aux suites E2E globales.
