# F56 — Sourçage cite_source enforcement (P1 strict)

**Phase** : H — Agent Hardening
**Modules brainstorm** : 0.1 (Sourçage anti-hallucination), 10.4 (Eval continue post-process)
**Dépendances** : F03 (Source entity), F07 (Sources management admin), F35 (eval LLM postprocess), F53 (LangGraph core), F55 (dispatch)
**Estimation** : 4 jours

## Contexte et objectif

P1 de la constitution est **non-négociable** : *"Toute affirmation factuelle (chiffre, critère, formule, seuil, facteur d'émission, document requis) DOIT pointer vers une `Source` `verified`."* C'est l'avantage compétitif majeur de la plateforme — un fund officer doit pouvoir cliquer et vérifier chaque chiffre.

Aujourd'hui, le LLM brut (et même demain l'agent F53) **peut hallucider** sans contrainte structurelle. F56 livre les **trois lignes de défense** :

1. **Avant** (system prompt) — instruction explicite + exemples (déjà prévu F54).
2. **Pendant** (tool exposure) — le tool `cite_source(source_id)` est **toujours** dans le set des tools disponibles ; le LLM est entraîné à l'invoquer.
3. **Après** (post-processing) — un **détecteur de claims factuels** scanne la réponse texte de l'agent ; si un chiffre/critère/seuil/formule apparaît sans appel `cite_source` correspondant, la réponse est :
   - **Rejetée** (retry avec instruction explicite) en mode strict, OU
   - **Annotée** d'un bandeau "non sourcé" + invite à compléter, en mode permissif.

F56 livre aussi le tool `flag_unsourced(claim, reason)` que le LLM invoque quand il sait qu'il ne peut pas sourcer (transparence > omission).

## User Stories

### US1 — Tool `cite_source(source_id)` toujours disponible (P1)

**En tant que** dev,
**je veux** que `cite_source` soit forcément inclus dans `state.available_tools` à chaque tour, indépendamment du sélecteur F14,
**afin que** le LLM ait toujours la possibilité de citer.

Implementation : `tool_selector.select_tools(...)` ajoute `cite_source`, `search_source`, `flag_unsourced` en post-processing si absents. Ces 3 tools ne comptent pas dans la limite des 10.

### US2 — Tool `search_source(query)` indexé pgvector (P1)

**En tant que** dev,
**je veux** que `search_source(query)` retourne les **5 meilleures sources** vérifiées dont le contenu (titre + section + extrait) matche sémantiquement la query (embedding via Voyage `voyage-3.5`),
**afin que** le LLM puisse découvrir des sources pertinentes en cours de conversation.

Index pgvector sur `source.embedding` (1024 dim) — créé en F03/F07 si pas déjà fait, sinon migration ici.

### US3 — Tool `flag_unsourced(claim, reason)` (P1)

**En tant que** dev,
**je veux** que `flag_unsourced` enregistre une ligne dans `unsourced_flag` (`account_id, thread_id, message_id, claim, reason, created_at`) ET émette un event SSE `unsourced_claim` qui fait afficher un badge rouge sur la portion de texte concernée,
**afin que** la transparence soit visible et que le backlog des claims non sourcés alimente F07 admin.

### US4 — Détecteur de claims factuels (P1)

**En tant que** dev,
**je veux** un module `app/agent/sourcing_detector.py` qui scanne le texte assistant final et détecte les **claims factuels** :
- Chiffres avec unités (`%, °C, tCO2e, FCFA, EUR, USD, kWh, m², kg, t`)
- Pourcentages, ratios, fractions (`60%`, `2/3`)
- Plages de valeurs (`entre 10 et 50 millions`)
- Mots-clés référentiels (`GCF`, `BOAD`, `IFC PS`, `GRI`, `ODD 7`, `UEMOA Reg.`, `taxonomie verte`)
- Patterns de seuils (`au moins`, `minimum`, `maximum`, `seuil de`, `plafond de`)
- Patterns de formules (`= …`, `* … =`, `/`)

**afin de** flagger toute affirmation qui devrait être sourcée.

Implémentation MVP : regex + keyword matching. Optionnel post-MVP : LLM-judge.

### US5 — Cross-référence claim ↔ cite_source (P1)

**En tant que** dev,
**je veux** que pour chaque claim détecté (US4), le module vérifie qu'il existe un `cite_source` invoqué :
- Dans la même phrase (paragraphe), OU
- Dans un appel parent (la réponse complète a au moins une citation par paragraphe contenant un claim).

**afin de** détecter les sourcings absents.

### US6 — Mode strict vs permissif (P1)

**En tant que** ops,
**je veux** une variable `LLM_AGENT_SOURCING_MODE ∈ {strict, permissive, off}` :
- `strict` (défaut prod) : un claim sans cite_source → retry agent (max 1 retry sourcing) avec message tool système ("Tu as affirmé X sans citer de source. Utilise `cite_source` ou `flag_unsourced` ou reformule sans affirmer."). Si le retry échoue → rejeter le message, fallback texte sobre "Je ne dispose pas de source vérifiée pour cette information."
- `permissive` (staging/dev) : annoter la portion de texte sans bloquer, bandeau "⚠️ portion non sourcée", `unsourced_flag` créé.
- `off` (CI tests) : aucun contrôle.

### US7 — Annotation des chips Source dans le rendu (P1)

**En tant que** utilisateur,
**je veux** que chaque chiffre / mot-clé sourcé soit affiché avec un **superscript cliquable** ouvrant un popover contenant :
- Titre de la source, éditeur, date, version
- Page / section
- URL canonique
- Statut de vérification (verified / pending / outdated)
- Bouton "Ouvrir le PDF",
**afin de** rendre la traçabilité tangible (UX du brainstorming Module 0.1).

Frontend : composant `<VizSourcePin>` (déjà existant F40), backend transmet `source_id` dans la metadata du `text_delta` ou en post-message via `message_done.payload.sources`.

### US8 — Annexe "Sources et références" automatique (P1)

**En tant que** utilisateur,
**je veux** que tout rapport PDF généré (F24, F30, F49) intègre automatiquement à la fin une **annexe Sources et références** listant chaque source citée dans le rapport avec son URL et sa date,
**afin que** l'utilisateur puisse imprimer/exporter le rapport et défendre chaque chiffre.

Implementation : F49 doit consommer la liste des `source_id` cités dans tous les messages assistant inclus dans le rapport.

### US9 — Métriques de compliance sourçage (P2)

**En tant que** admin,
**je veux** un endpoint `GET /admin/agent/metrics/sourcing` retournant :
- Taux de réponses contenant ≥ 1 cite_source (cible : > 80%)
- Taux de réponses avec ≥ 1 claim détecté SANS cite_source (cible : < 5%)
- Taux de retry sourcing (cible : < 10%)
- Top 20 des sources les plus citées (alimente F07 priorisation)
- Top 20 des claims non sourcés récurrents (signaux pour ajouter des sources),
**afin de** piloter la qualité de sourçage de la plateforme.

### US10 — Liste blanche de claims génériques (P2)

**En tant que** dev,
**je veux** une liste de patterns "non factuels" qui ne déclenchent pas de retry (ex. `"En général, les PME africaines…"`, `"Cela dépend de votre secteur…"`),
**afin de** ne pas paralyser l'agent sur des phrases génériques pédagogiques.

Liste maintenue dans `app/agent/sourcing_whitelist.py`, versionée, testable.

## Exigences fonctionnelles

- **FR-001** : Module `backend/app/agent/sourcing_detector.py` exposant `detect_claims(text: str) -> list[Claim]` où `Claim = {span: tuple[int, int], kind: ClaimKind, raw: str}`.
- **FR-002** : Module `backend/app/agent/sourcing_validator.py` exposant `validate_response(response_text: str, tool_calls: list[ValidatedToolCall]) -> SourcingValidationResult` qui croise claims détectés ↔ cite_source invoqués.
- **FR-003** : Tool `cite_source(source_id: UUID)` enregistré dans `tool_registry`. Schéma : `{source_id: UUID}`. Handler : vérifie que la source est `verified` (sinon `tool_call_log.status='source_unverified'` + erreur structurée).
- **FR-004** : Tool `search_source(query: str, limit: int = 5)` enregistré. Handler : embedding Voyage de query → cosine search sur `source.embedding`. Filtrer `verification_status = 'verified'`. Retourner liste avec `id, title, publisher, url, page, section, snippet`.
- **FR-005** : Tool `flag_unsourced(claim: str, reason: str)` enregistré. Handler : INSERT dans `unsourced_flag` + publish event SSE.
- **FR-006** : Table `unsourced_flag` : `id, account_id, thread_id, message_id, claim TEXT, reason TEXT, created_at, resolved_at NULLABLE, resolved_by NULLABLE`. Index `(account_id, created_at DESC)`.
- **FR-007** : Variable d'env `LLM_AGENT_SOURCING_MODE: Literal["strict", "permissive", "off"]`, défaut `strict`.
- **FR-008** : Modification du nœud `compose_response` (F53) : si `SOURCING_MODE = strict` et `validate_response` retourne `unsourced_claims_count > 0`, déclencher un **retry sourcing** unique avec un message tool système expliquant le problème.
- **FR-009** : Si retry sourcing échoue → tronquer le message à la dernière phrase sourcée (ou substituer par fallback "Je ne dispose pas de source vérifiée…") + marquer `agent_run.sourcing_status = 'failed'`.
- **FR-010** : Le `message_done.payload` SSE inclut un champ `sources: list[SourceRef]` agrégeant tous les `cite_source` invoqués pour ce message.
- **FR-011** : Frontend (extension F41) lit `payload.sources` et rend les `<VizSourcePin>` (F40) inline.
- **FR-012** : Endpoint `GET /admin/agent/metrics/sourcing?period=7d|30d|all` (gardé admin) retournant les KPIs US9.
- **FR-013** : Liste blanche `app/agent/sourcing_whitelist.py` : 20-30 patterns initiaux, testée.
- **FR-014** : Test golden : 50 paires (réponse, label sourcing-correct/incorrect) dans `tests/golden/sourcing.jsonl`. CI bloque si précision < 90%.
- **FR-015** : Logger structuré `sourcing_check` : `agent_run_id, claims_detected, citations_found, missing, mode, retried`.

## Exigences non-fonctionnelles

- **NFR-001** : Latence du détecteur < 50 ms pour un message de 2 000 caractères.
- **NFR-002** : Latence d'un `search_source` (Voyage embedding + pgvector cosine 1M lignes) < 500 ms p95.
- **NFR-003** : Précision détecteur claims (sur le golden set) : recall ≥ 90 %, precision ≥ 85 %. À mesurer en CI.
- **NFR-004** : Aucun faux-rejet permanent sur des phrases génériques pédagogiques (whitelist).
- **NFR-005** : Le détecteur ne doit pas dépendre du LLM (synchrone, pas d'appel externe). Optionnel post-MVP : LLM-judge pour cas ambigus.

## Entités clés

- **UnsourcedFlag** (FR-006).
- `agent_run.sourcing_status: Literal['ok', 'retried_ok', 'failed'] | None` ajouté.
- `chat_message.sources: JSONB` (liste des source_id cités) ajouté pour requête rapide.

## Success Criteria

- **SC-001** : Le LLM affirme "Le seuil GCF pour les PME est de 50 M USD" sans cite_source. Mode strict → retry → soit le LLM ajoute `cite_source(...)` du document GCF, soit fallback "Je ne dispose pas de source vérifiée pour ce seuil — voulez-vous que je recherche?".
- **SC-002** : Le LLM affirme "L'ADEME estime à 6.0 kg CO2/litre le diesel". Mode strict → si `cite_source(ADEME-base-carbone-2024)` est dans les tool_calls → réponse acceptée. Sinon retry.
- **SC-003** : Phrase générique "Les PME africaines investissent peu dans la formation" (whitelist hit) → pas de retry, pas de bandeau.
- **SC-004** : Annotation visuelle : "Le facteur ADEME^[¹] est de 6.0 kg CO2/litre^[¹]." Frontend rend les superscripts cliquables → popover source.
- **SC-005** : `flag_unsourced(claim="Le BOAD acceptera mon dossier en 8 semaines", reason="aucun document public confirmant ce délai")` → INSERT en `unsourced_flag`, badge dans le chat, ligne visible dans `/admin/sources/unsourced-backlog`.
- **SC-006** : Rapport PDF F49 généré → annexe "Sources et références" auto-listée avec 12 sources, chaque chiffre du rapport pointe vers une source.
- **SC-007** : `GET /admin/agent/metrics/sourcing?period=7d` retourne {compliance_rate: 0.87, retry_rate: 0.06, ...}.
- **SC-008** : Mode `permissive` → claim non sourcé → bandeau visible mais réponse non bloquée. Utile en staging/dev pour ne pas freiner l'itération.

## Hors-scope MVP (post-MVP)

- LLM-judge pour détection de claims (claim ambigu) — MVP : regex + keywords.
- Multilingue (anglais) sur le détecteur — MVP : FR uniquement.
- Score de confiance par citation (la source est-elle "récente, exacte, autoritaire?") — post-MVP.
- Suggestion automatique de sources à ajouter (le LLM propose une URL externe à valider par admin) — post-MVP.
- Vérification cross-source (deux sources se contredisent) — post-MVP.

## Risques et points de vigilance

- **Trop strict = paralysie** : si tout claim doit être sourcé, l'agent passe son temps en retry. Calibrer la whitelist + tester sur golden set. Métrique `retry_rate` cible < 10%.
- **Faux positifs** : "Je vois que vous avez 3 projets actifs" ne doit pas déclencher (`3 projets` n'est pas un claim factuel ESG, c'est de la lecture DB). Le détecteur doit ignorer les chiffres venant des `tool_message` du tour. Stratégie : tagger les chiffres "produits par tool" vs "écrits par LLM".
- **Sources verifiées limitées** : si la base ne contient pas une source pour un sujet, l'agent ne peut pas répondre. Solution : `flag_unsourced` honnête + transmission à F07 admin pour priorisation. Mesure : `top_unsourced_topics` indique où ajouter.
- **Hallucination de source_id** : le LLM peut inventer un UUID qui n'existe pas en DB. Le handler `cite_source` valide l'existence (sinon erreur). Ajouter retry avec message "le source_id X n'existe pas, utilise `search_source` pour trouver une source réelle".
- **Performance pgvector cold cache** : la première recherche après boot est lente. Pré-chauffer en background au boot (charger top 1000 sources). Documenter.
- **Voyage API down** : `search_source` échoue. Fallback : keyword search SQL (`ILIKE`) sur title + extract. Documenter.
- **Whitelist trop large** : un pattern "En général" peut whitelister un vrai claim. Tester sur golden set, raffiner.
- **Annexe PDF lourde** : 100 sources citées = annexe de 5 pages. Acceptable, mais à vérifier en F49.

## Spec-Kit hooks

```bash
/speckit.specify "$(cat docs_et_brouillons/features/56-agent-sourcing-enforcement.md)"
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```
