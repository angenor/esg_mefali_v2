# Phase 0 — Research (F16 Tools de Visualisation Inline)

## R1 — Validation Mermaid côté backend (P2)

- **Decision** : whitelist regex Python (MVP) sur (a) le mot-clé du diagramme (`flowchart`, `sequenceDiagram`, `stateDiagram`, `gantt`, `classDiagram`, `erDiagram`), (b) absence de `click ... href "http..."` (URL externe), (c) longueur max 4 KB, (d) absence de `%%{init...}%%` contenant `<script>`.
- **Rationale** : pas de parser AST Mermaid stable en Python ; appeler le binaire mermaid-cli en Node sortirait du sandbox `.venv`. La whitelist regex couvre les vecteurs d'injection (FR-020) et reste rapide. Si le LLM produit du Mermaid invalide, la boucle retry F14 corrige.
- **Alternatives** : grammar `lark/pyparsing` (effort > 1j MVP) ; service Node externe (dépendance opérationnelle hors scope) ; valider seulement côté front (casse FR-006).

## R2 — Sérialisation Decimal en JSON

- **Decision** : `Decimal` Pydantic v2 avec `model_config = ConfigDict(json_encoders={Decimal: str})` ; sortie JSON en string. Front (Vue/chart.js) convertit via `Number(payload.value)`.
- **Rationale** : préserve la précision (P5 Money typé). JSON natif n'a pas de Decimal. Cohérent avec F11/F12 et F15.
- **Alternatives** : `float` (perte précision, interdit P5) ; tout en string sans typage (casse validation Pydantic).

## R3 — Lazy import chart.js, leaflet, mermaid (Nuxt 4)

- **Decision** : composable `_useChartJs.ts` qui fait `await import('chart.js/auto')` dans `onMounted`. Idem leaflet, mermaid.
- **Rationale** : Vite/Nuxt code-split automatiquement les `import()` dynamiques. Respecte SC-005 (bundle initial < 500 KB).
- **Alternatives** : `defineAsyncComponent` (équivalent, moins explicite) ; eager (casse SC-005).

## R4 — Réutilisation `_common.py` F15

- **Decision** : import direct de `no_html` depuis `app.orchestrator.tools._common` ; nouveau fichier `_viz_common.py` à côté pour les helpers F16 (`SourceRequiredMixin`, `AltTextMixin`, `ensure_internal_link`, `DecimalValue`).
- **Rationale** : zéro modif de `_common.py` (zone partagée F15). Localisation des helpers F16 = lecture + tests faciles.
- **Alternatives** : étendre `_common.py` (risque régression F15) ; inliner par tool (duplication).

## R5 — `register_visualisation_tools()` agrégé

- **Decision** : un seul registrar `register_visualisation_tools()` dans `app/orchestrator/tools/__init__.py` qui appelle les `register()` individuels des tools P1 (puis P2 si livrés). Démarrage app : `register_response_tools()` + `register_visualisation_tools()`.
- **Rationale** : reflète exactement le pattern F15.
- **Alternatives** : registrars indépendants (casse la convention F15).

## R6 — Anti-XSS sur les champs texte

- **Decision** : `no_html` (F15) sur tous les champs texte exposés : `label`, `title`, `unit`, `period`, `name`, `x_label`, `y_label`, `alt_text`, valeurs textuelles dans `rows[].values` (comparison_table).
- **Rationale** : defense-in-depth. Bloquer le storage de payloads malveillants dans `chat_message.payload_json` (qui pourraient être exportés en PDF F24/F30 ailleurs).
- **Alternatives** : confiance front-only (contrevient à defense-in-depth).

## R7 — `show_pie` vs `show_donut` : deux tools

- **Decision** : DEUX tools séparés avec schémas Pydantic identiques sauf `type`. Côté frontend, mutualisation via wrapper interne `variant: "pie" | "donut"`.
- **Rationale** : signaux explicites au LLM (P9). Spec FR-001 liste 12 tools nommés.
- **Alternatives** : un seul tool + champ `variant` (moins explicite pour LLM).

## R8 — Réactivité historique (US13, P2)

- **Decision** : badge "données obsolètes — recalculer ?" déclenché côté Vue par comparaison `payload.rendered_at < entity.updated_at`. `payload.rendered_at` est ajouté automatiquement par le pipeline F13.
- **Rationale** : recalculer côté serveur exigerait de stocker les inputs originaux du LLM, hors scope F16.
- **Alternatives** : recalcul serveur (hors scope).

## R9 — Tests TDD : structure et couverture cible

- **Decision** : pour chaque tool P1, 1 fichier `test_show_<tool>.py` avec :
  1. test positif (payload valide) ;
  2. test rejet `source_ids` manquant (sauf timeline / map) ;
  3. test rejet HTML injection ;
  4. test rejet contraintes spécifiques (radar longueurs, comparison_table > 5x5, match_card score hors [0,100], pie/donut slice négative) ;
  5. test sérialisation Decimal.
  Total ≈ 5 × 10 = 50 tests minimum. `test_register_visualisation_tools.py` : 3 tests (idempotence, présence, schémas non vides).
- **Rationale** : > 80 % du code F16 ajouté avec overhead raisonnable.

## R10 — Lien interne `show_match_card.link`

- **Decision** : validator Pydantic refuse tout `link` ne commençant pas par `/`. Pas d'URL externe.
- **Rationale** : P7 (plateforme fermée). Empêcher le LLM d'envoyer l'utilisateur vers un site externe.
- **Alternatives** : whitelist de chemins (trop rigide pour MVP) ; aucune validation (risque P7).
