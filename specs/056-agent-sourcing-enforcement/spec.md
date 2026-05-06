# Feature Specification: Agent Sourcing Enforcement (F56)

**Feature Branch**: `056-agent-sourcing-enforcement`
**Created**: 2026-05-06
**Status**: Draft
**Phase** : H — Agent Hardening
**Modules brainstorm** : 0.1 (Sourçage anti-hallucination), 10.4 (Eval continue post-process)
**Dépendances** : F03 (Source entity), F07 (Sources management admin), F35 (eval LLM postprocess), F53 (LangGraph core), F54 (context-builder), F55 (dispatch SSE)
**Estimation** : 4 jours
**Input**: User description: F56 — Sourçage cite_source enforcement strict (P1 constitutional invariant non-négociable). Trois lignes de défense : (1) system prompt, (2) tools cite_source/search_source/flag_unsourced toujours disponibles, (3) post-processing détecteur de claims factuels avec retry/fallback.

## Clarifications

### Session 2026-05-06

- Q: How are `unsourced_flag` rows deduplicated for similar claims in a single thread/session? → A: UNIQUE INDEX on `(account_id, thread_id, lower(claim))` WHERE `resolved_at IS NULL`; INSERT uses `ON CONFLICT DO NOTHING` (first writer wins).
- Q: Where is `chat_message.sources: JSONB` added — existing `chat_message` table or new `agent_message` (F53)? → A: Existing `chat_message` table (created F01, enriched F13). No new agent_message table — F53 reuses chat_message.
- Q: When `cite_source` references a source whose status changed to `outdated` between embedding and citation, is the citation still accepted? → A: Only `verification_status='verified'` is acceptable. `pending`, `outdated`, `rejected` → tool_call_log.status='source_unverified', structured error.
- Q: In permissive mode, should `unsourced_flag` auto-creation apply per-claim or per-message? → A: Per-message rollup (1 row per assistant message even if multiple claims); the `claim` field stores the first detected claim, `reason='auto_detected:N_unsourced_claims'` encodes the count.
- Q: Pré-chauffage pgvector au boot (top 1000 sources) : MVP ou post-MVP ? → A: Post-MVP. Documenter dans plan/risques. Pré-chauffer uniquement si NFR-002 échoue en CI.

## Contexte et objectif

P1 de la constitution Module 0 est **non-négociable** : *"Toute affirmation factuelle (chiffre, critère, formule, seuil, facteur d'émission, document requis) DOIT pointer vers une `Source` `verified`."* C'est l'avantage compétitif majeur — un fund officer ou un agent de banque doit pouvoir cliquer chaque chiffre d'un dossier ESG Mefali et atterrir sur le PDF source.

Aujourd'hui :
- F03 a posé la table `Source` avec embeddings 1024-dim (Voyage `voyage-3.5`).
- F07 a mis en place le back-office de gestion des sources.
- F53/F54/F55 ont livré l'agent LangGraph, le context builder, et le dispatcher SSE.
- Le `DispatchCategory.REINVOKE_LLM` est déjà prévu pour `cite_source` / `search_source` (cf. `app/agent/state.py:86`).
- Mais **aucun garde-fou structurel** ne contraint le LLM à citer ses sources — il peut halluciner librement.

F56 livre les **trois lignes de défense** :

1. **Avant** (system prompt) — instruction explicite + exemples sourcés (déjà préparé F54 dans `app/agent/prompts/`).
2. **Pendant** (tool exposure) — les tools `cite_source(source_id)`, `search_source(query)`, `flag_unsourced(claim, reason)` sont **toujours forcés** dans `state.available_tools`, indépendamment du sélecteur de sous-ensemble F14, et **ne comptent pas** dans la limite des 10 tools.
3. **Après** (post-processing) — un détecteur de claims factuels (`sourcing_detector`) scanne le texte assistant final ; un validateur (`sourcing_validator`) croise les claims détectés avec les `cite_source` invoqués ; selon le mode (`strict` | `permissive` | `off`), la réponse est rejetée+retryée, annotée, ou laissée passer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Tools sourcing toujours disponibles (Priority: P1)

En tant que développeur agent, je veux que `cite_source`, `search_source`, et `flag_unsourced` soient inclus dans `state.available_tools` à chaque tour, indépendamment du sélecteur de sous-ensemble (F14), afin que le LLM ait toujours la possibilité de citer une source ou de signaler une affirmation non sourcée.

**Why this priority**: Ces trois tools sont le mécanisme primaire de l'invariant P1 ; sans eux, aucune des deux lignes de défense suivantes ne fonctionne. Bloquant pour toute conversation contenant un claim factuel.

**Independent Test**: Lancer une conversation avec un selector qui retourne 0 tools métier — vérifier que les 3 tools sourcing apparaissent quand même dans `available_tools` côté LLM, et qu'ils ne consomment pas de budget sur la limite des 10 tools métier.

**Acceptance Scenarios**:

1. **Given** un agent run avec un sélecteur F14 retournant 7 tools métier, **When** le nœud `select_tools` s'exécute, **Then** `state.available_tools` contient 7 + 3 = 10 tools, dont les 3 tools sourcing en injection forcée.
2. **Given** un agent run avec un sélecteur retournant 10 tools métier (cap atteint), **When** `select_tools` s'exécute, **Then** les 3 tools sourcing sont ajoutés au-delà du cap (13 total exposés au LLM) ET le cap matériel applicatif `HARD_TOOL_CALLS_CAP` continue de protéger l'exécution.
3. **Given** mode `LLM_AGENT_SOURCING_MODE = off`, **When** `select_tools` s'exécute, **Then** les tools sourcing sont **présents** mais non forcés (comportement F14 inchangé) et le validateur ne s'exécute pas.

---

### User Story 2 — Tool `cite_source(source_id)` validé contre la base (Priority: P1)

En tant qu'agent IA, je veux que l'invocation `cite_source(source_id=UUID)` vérifie l'existence de la source en DB et son statut `verified` avant d'enregistrer la citation, afin que le LLM ne puisse pas inventer un UUID inexistant.

**Why this priority**: Sans validation, le LLM peut halluciner un UUID — un fund officer cliquerait sur un lien mort, briser la promesse de traçabilité.

**Independent Test**: Invoquer manuellement `cite_source(source_id=<UUID inconnu>)` → handler retourne erreur structurée `source_not_found`. Invoquer avec un UUID de source `pending` → erreur `source_unverified`. Invoquer avec un UUID `verified` → succès, ToolMessage retournée avec metadata source.

**Acceptance Scenarios**:

1. **Given** une source `verified` existe en DB avec id X, **When** le LLM invoque `cite_source(source_id=X)`, **Then** le handler enregistre `tool_call_log(status='ok', dispatch_result_kind='tool_message', output={source: {id, title, publisher, url, page, section, version}})` et l'agent continue.
2. **Given** un source_id qui n'existe pas en DB, **When** le LLM invoque `cite_source`, **Then** le handler retourne erreur structurée `source_not_found` (re-injectée en ToolMessage), et le LLM peut retry avec un message tool système suggérant `search_source`.
3. **Given** une source en statut `pending` ou `outdated`, **When** le LLM invoque `cite_source`, **Then** `tool_call_log.status='source_unverified'` ET retour erreur structurée bloquant la citation.

---

### User Story 3 — Tool `search_source(query)` avec recherche sémantique pgvector (Priority: P1)

En tant qu'agent IA, je veux invoquer `search_source(query, limit=5)` pour découvrir les sources verifiées dont le contenu (titre + section + extrait) match sémantiquement la query, afin de citer dynamiquement la bonne source en cours de conversation.

**Why this priority**: Sans `search_source`, le LLM doit connaître par cœur les `source_id` du référentiel — impossible à l'échelle de 1000+ sources. C'est le pont entre une intention LLM et une source citée.

**Independent Test**: Invoquer `search_source(query="facteur émission diesel ADEME", limit=5)` sur une base contenant 100 sources dont 1 ADEME — vérifier que cette source ressort en top 1 ; latence <500ms p95.

**Acceptance Scenarios**:

1. **Given** un index pgvector existe sur `source.embedding` et 50 sources verifiées sont indexées, **When** l'agent invoque `search_source(query="seuil GCF PME 50 millions USD", limit=5)`, **Then** la liste retournée contient les 5 sources les plus pertinentes par cosine similarity, filtrées sur `verification_status='verified'`, avec `id, title, publisher, url, page, section, snippet`.
2. **Given** Voyage AI est indisponible, **When** `search_source` est invoqué, **Then** un fallback `ILIKE` sur `title` + `section` est utilisé et le résultat est marqué `degraded=true` dans la réponse.
3. **Given** la base contient 0 sources verifiées sur la query, **When** `search_source` est invoqué, **Then** la réponse est une liste vide avec un hint "no_match — consider flag_unsourced".

---

### User Story 4 — Tool `flag_unsourced(claim, reason)` (Priority: P1)

En tant qu'agent IA honnête, je veux pouvoir invoquer `flag_unsourced(claim, reason)` quand je sais que je ne peux pas sourcer une affirmation, afin que la transparence soit préférée à l'omission ou à l'hallucination, et que le backlog des claims non sourcés alimente la priorisation admin (F07).

**Why this priority**: Sans cette soupape, le LLM en mode strict serait paralysé par des sujets sans source en base. `flag_unsourced` permet de répondre honnêtement et de boucler avec l'admin pour ajouter des sources.

**Independent Test**: Invoquer `flag_unsourced(claim="Le BOAD acceptera mon dossier en 8 semaines", reason="aucun document public confirmant ce délai")` → ligne créée dans `unsourced_flag` avec account_id, thread_id, message_id ; event SSE `unsourced_claim` émis ; visible dans `/admin/sources/unsourced-backlog`.

**Acceptance Scenarios**:

1. **Given** un agent run actif, **When** l'agent invoque `flag_unsourced(claim, reason)`, **Then** une ligne est insérée dans `unsourced_flag(account_id, thread_id, message_id, claim, reason, created_at)` sous RLS de l'account.
2. **Given** une ligne `unsourced_flag` insérée, **When** le frontend chat est connecté en SSE, **Then** un event `unsourced_claim` (avec span span+claim+reason) est émis et le frontend affiche un bandeau jaune sur la portion concernée.
3. **Given** des `unsourced_flag` accumulés, **When** l'admin consulte `/admin/sources/unsourced-backlog`, **Then** la liste paginée affiche les top 20 claims non sourcés agrégés (alimente F07 priorisation).

---

### User Story 5 — Détecteur de claims factuels (Priority: P1)

En tant que développeur de la pipeline post-processing, je veux un module `sourcing_detector.detect_claims(text)` qui scanne le texte assistant final et retourne la liste des claims factuels (chiffre+unité, pourcentage, plage, mot-clé référentiel, seuil, formule), afin de pouvoir les croiser avec les `cite_source` invoqués.

**Why this priority**: Pierre angulaire du contrôle "Après". Sans détecteur fiable, le mode strict bloque tout ou rien à zéro.

**Independent Test**: Sur un golden set de 50 paires (texte, claims labellés), recall ≥ 90% et precision ≥ 85%, latence < 50ms pour 2000 caractères.

**Acceptance Scenarios**:

1. **Given** le texte "Le facteur ADEME est de 6.0 kg CO2/litre pour le diesel", **When** `detect_claims` s'exécute, **Then** elle retourne au moins 1 claim de kind=`number_with_unit` (raw="6.0 kg CO2/litre", span couvrant le chiffre et l'unité) ET 1 claim de kind=`reference_keyword` (raw="ADEME").
2. **Given** le texte "Vous avez 3 projets actifs" (chiffre venant d'un tool_message DB du tour), **When** le détecteur s'exécute avec le contexte des tool_messages du tour, **Then** ce chiffre est marqué `from_tool=true` et n'est pas comptabilisé comme claim LLM.
3. **Given** une phrase générique "En général, les PME africaines investissent peu dans la formation" (pattern whitelist), **When** le détecteur s'exécute, **Then** elle retourne une liste vide (whitelist hit).
4. **Given** le détecteur exécuté sur un message de 2000 caractères, **When** mesuré, **Then** la latence est < 50ms p95 (NFR-001).

---

### User Story 6 — Validateur de sourçage avec retry strict/permissif (Priority: P1)

En tant que pipeline orchestrateur, je veux que `sourcing_validator.validate_response(response_text, tool_calls)` croise les claims détectés avec les `cite_source` invoqués et applique la politique du mode (`strict` | `permissive` | `off`), afin de garantir l'invariant P1 selon l'environnement.

**Why this priority**: Sans validateur, les deux lignes de défense (1 prompt + 2 tools) restent au bon vouloir du LLM. Le validateur est le gatekeeper.

**Independent Test**: Avec mode `strict`, soumettre une réponse contenant un claim sans `cite_source` correspondant → 1 retry sourcing ; si retry échoue → fallback texte ; `agent_run.sourcing_status='failed'`.

**Acceptance Scenarios**:

1. **Given** mode `strict` ET la réponse "L'ADEME estime à 6.0 kg CO2/litre" avec dans les `tool_calls` un `cite_source(ADEME-base-carbone-2024)`, **When** le validateur s'exécute, **Then** la validation passe (`unsourced_claims_count=0`) et la réponse est livrée.
2. **Given** mode `strict` ET un claim sans cite_source associé, **When** le validateur s'exécute, **Then** un retry sourcing unique est déclenché avec un ToolMessage système expliquant le problème ; le LLM peut ajouter `cite_source` ou `flag_unsourced` ou reformuler.
3. **Given** mode `strict` ET retry sourcing échoué (le LLM persiste sans cite_source), **When** le validateur réévalue, **Then** la portion non sourcée est tronquée (à la dernière phrase sourcée) ou substituée par "Je ne dispose pas de source vérifiée pour cette information." et `agent_run.sourcing_status='failed'`.
4. **Given** mode `permissive`, **When** un claim sans cite_source est détecté, **Then** la réponse n'est PAS bloquée, un bandeau "portion non sourcée" est annoté, et un `unsourced_flag` est créé automatiquement avec `reason='auto_detected_no_citation'`.
5. **Given** mode `off`, **When** la réponse est composée, **Then** aucune validation sourcing n'est exécutée (ni détecteur, ni validateur, ni retry).

---

### User Story 7 — Annotation visuelle des chips Source dans le chat (Priority: P1)

En tant qu'utilisateur PME (ou fund officer), je veux que chaque chiffre / mot-clé sourcé soit affiché avec un superscript cliquable ouvrant un popover montrant le titre, l'éditeur, la date, l'URL canonique, et le statut de vérification de la source, afin de pouvoir vérifier instantanément la traçabilité.

**Why this priority**: Sans rendu visuel, l'invariant P1 reste invisible côté utilisateur. C'est l'UX de la promesse "vous pouvez cliquer chaque chiffre".

**Independent Test**: Côté frontend, chargement d'un message assistant avec `payload.sources=[{source_id, span, ...}]` → rendu de superscripts numériques cliquables ouvrant le popover `<VizSourcePin>` (composant F40 existant).

**Acceptance Scenarios**:

1. **Given** un message assistant avec un cite_source effectif et un span de claim, **When** l'événement SSE `message_done` est reçu, **Then** son `payload.sources` agrège la liste des SourceRef cités dans le message, avec span+source_id+title+publisher+url+page+section+verification_status.
2. **Given** le frontend affiche le message, **When** l'utilisateur survole/clique le superscript, **Then** un popover apparaît avec le détail source et un bouton "Ouvrir le PDF" (URL canonique).
3. **Given** une source `outdated`, **When** l'utilisateur ouvre le popover, **Then** un badge orange "Source obsolète" est affiché.

---

### User Story 8 — Annexe "Sources et références" dans les rapports PDF (Priority: P1)

En tant qu'utilisateur PME, je veux que tout rapport PDF généré (F24 Conformité, F30 Attestation, F49 Rapports/Attestations UI) intègre automatiquement à la fin une annexe "Sources et références" listant chaque source citée avec titre, éditeur, URL, date, afin que je puisse imprimer ou exporter le rapport et défendre chaque chiffre devant un fund officer.

**Why this priority**: La promesse P1 ne s'arrête pas au chat ; elle doit suivre l'utilisateur dans tous les artefacts exportés.

**Independent Test**: Générer un rapport PDF F49 contenant 3 chiffres ESG avec `cite_source` distincts → l'annexe finale contient 3 lignes triées par numéro d'apparition, format "[1] Titre — Éditeur — URL — Date".

**Acceptance Scenarios**:

1. **Given** un rapport PDF F49 contient des messages assistant avec des `cite_source` agrégés dans `chat_message.sources`, **When** le rapport est généré, **Then** l'annexe finale liste chaque source unique avec son numéro de référence (renvoyant aux superscripts du corps du rapport).
2. **Given** 100 sources distinctes citées dans un rapport, **When** l'annexe est générée, **Then** elle reste lisible (pagination dédiée si > 5 pages).

---

### User Story 9 — Métriques admin de compliance sourçage (Priority: P2)

En tant qu'admin plateforme, je veux un endpoint `GET /admin/agent/metrics/sourcing?period=7d|30d|all` retournant les KPIs de compliance sourçage (taux réponses ≥1 cite_source, taux claims sans cite, taux retry, top 20 sources citées, top 20 claims non sourcés), afin de piloter la qualité de sourçage et de prioriser les sources à ajouter (F07).

**Why this priority**: Pilotage qualité, indispensable pour l'amélioration continue, mais pas bloquant pour le run de l'agent.

**Independent Test**: Après 100 réponses agent simulées, l'endpoint retourne `compliance_rate`, `unsourced_rate`, `retry_rate`, `top_sources`, `top_unsourced_topics` — chaque valeur calculable à partir des tables `agent_run`, `tool_call_log`, `unsourced_flag`, `chat_message`.

**Acceptance Scenarios**:

1. **Given** 100 agent_run avec 87 contenant ≥1 cite_source, **When** l'admin appelle l'endpoint avec period=7d, **Then** `compliance_rate=0.87`.
2. **Given** 6 agent_run avec retry sourcing, **When** appelé, **Then** `retry_rate=0.06`.
3. **Given** la sécurité, **When** un user PME tente l'endpoint, **Then** 403 Forbidden (gardé admin).

---

### User Story 10 — Liste blanche de claims génériques (Priority: P2)

En tant que développeur agent, je veux une liste blanche `sourcing_whitelist.py` (20-30 patterns initiaux) versionée et testée, listant les patterns "non factuels" (ex: "En général", "Cela dépend de", "Typiquement"), afin que des phrases pédagogiques ou contextuelles ne déclenchent pas de retry sourcing.

**Why this priority**: Sans whitelist, le mode strict génère des faux-rejets sur des phrases naturelles non-affirmatives. Bloquant pour l'UX agent.

**Independent Test**: Sur le golden set, vérifier que 100% des phrases whitelistées (20+ exemples) ne déclenchent pas de retry, et que 0% des claims réels labellés en golden ne sont whitelistés à tort.

**Acceptance Scenarios**:

1. **Given** la phrase "En général, les PME africaines investissent peu dans la formation", **When** le détecteur s'exécute, **Then** elle est filtrée par la whitelist (kind=`generic_pedagogic`) et n'apparaît pas dans la liste de claims.
2. **Given** un claim réel "Le seuil GCF est de 50 M USD", **When** confronté à la whitelist, **Then** il n'est PAS filtré (le pattern "Le seuil de" doit être plus spécifique).

---

### Edge Cases

- **Hallucination de source_id** : LLM invente un UUID. Le handler `cite_source` valide en DB ; sur erreur, retourne ToolMessage `source_not_found` ; le LLM peut retry avec `search_source`.
- **Voyage API down** : `search_source` échoue → fallback `ILIKE` sur `title`+`section` ; `degraded=true` dans la réponse.
- **Performance pgvector cold cache** : première recherche après boot lente. Pré-chauffage (lazy) au boot — top 1000 sources.
- **Cap de tools métier atteint (10) + 3 sourcing forcés = 13 tools exposés** : acceptable car LLM ne fait jamais 13 calls dans un tour ; cap matériel `HARD_TOOL_CALLS_CAP` reste à 10.
- **Tronquage de réponse** : la fallback "Je ne dispose pas de source vérifiée…" remplace TOUT le message si aucune phrase n'est sourcée ; sinon tronque à la dernière phrase sourcée.
- **Claim détecté venant d'un tool DB** (ex. "vous avez 3 projets") : marqué `from_tool=true`, exclu du contrôle sourcing. Le détecteur reçoit la liste des chiffres "produits par tool" du tour (extraits des ToolMessage des handlers READ).
- **Annexe PDF lourde** : 100+ sources citées → pagination dédiée, jamais bloquée.
- **Whitelist trop large** : pattern "En général" peut whitelister un vrai claim. Mitigation : priorité aux claims (claim détecté gagne sur whitelist générique) + tests golden set.
- **Mode `off` en prod** : interdit (config). Le démarrage backend doit refuser `LLM_AGENT_SOURCING_MODE=off` quand `ENVIRONMENT=production`.
- **Latence dépassée** : si détecteur > 50ms, log warning + on continue (pas de blocage). Métrique surveillée.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST exposer un module `app/agent/sourcing/detector.py` avec `detect_claims(text: str, *, tool_outputs: list[str] = []) -> list[Claim]` où `Claim` a `span: tuple[int, int]`, `kind: ClaimKind ∈ {number_with_unit, percentage, ratio, range, reference_keyword, threshold, formula}`, `raw: str`, `from_tool: bool`.
- **FR-002**: Le système MUST exposer un module `app/agent/sourcing/validator.py` avec `validate_response(response_text: str, tool_calls: list[ValidatedToolCall], *, tool_outputs: list[str] = [], mode: SourcingMode) -> SourcingValidationResult` où le résultat a `claims_detected, citations_found, unsourced_claims, mode, decision ∈ {accept, retry, fallback, annotate}`.
- **FR-003**: Le système MUST enregistrer un tool `cite_source` dans `TOOL_REGISTRY` (catégorie `READ` → `REINVOKE_LLM`) avec schéma Pydantic strict `{source_id: UUID}`. Le handler MUST vérifier en DB que `Source.id = source_id AND verification_status = 'verified'` (strict, cf. clarification Q3 — `pending`, `outdated`, `rejected` sont **toujours** rejetés) ; sinon retourne erreur structurée `{error: 'source_not_found' | 'source_unverified', source_id, current_status, hint: 'use search_source'}` ET `tool_call_log.status='source_unverified'`.
- **FR-004**: Le système MUST enregistrer un tool `search_source` (READ→REINVOKE_LLM) avec schéma `{query: str (1..500), limit: int (1..10, default=5)}`. Le handler MUST embedder la query via Voyage `voyage-3.5` (1024 dim), exécuter une cosine search SQL `pgvector` sur `source.embedding` filtrée `verification_status='verified'`, retourner liste `[{id, title, publisher, url, page, section, snippet, score}]`. Sur échec Voyage, fallback `ILIKE %query%` sur `title`+`section` avec `degraded=true`.
- **FR-005**: Le système MUST enregistrer un tool `flag_unsourced` (catégorie `MUTATION` → `DB_MUTATION`) avec schéma `{claim: str (1..1000), reason: str (1..500)}`. Le handler MUST insérer une ligne dans `unsourced_flag` sous RLS `account_id` (avec `INSERT ... ON CONFLICT DO NOTHING` pour la dédup, voir FR-006) ET émettre un event SSE `unsourced_claim` (best-effort).
- **FR-006**: Le système MUST créer la table `unsourced_flag` avec colonnes `id UUID PK, account_id UUID NOT NULL FK account, user_id UUID NOT NULL FK account_user, agent_run_id UUID NULL FK agent_run, thread_id UUID NULL, message_id UUID NULL, claim TEXT NOT NULL, reason TEXT NOT NULL, source_of_change source_of_change_t NOT NULL DEFAULT 'llm', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolved_at TIMESTAMPTZ NULL, resolved_by UUID NULL FK account_user, version BIGINT NOT NULL DEFAULT 1`. Index `(account_id, created_at DESC)`. **Index UNIQUE** partiel `(account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL` pour la dédup intra-thread (cf. clarification Q1). RLS policy `USING (account_id = current_setting('app.current_account_id')::uuid)`. Audit append-only (UPDATE/DELETE révoqués sur le rôle applicatif ; resolved_at/resolved_by mis à jour via rôle admin uniquement).
- **FR-006a**: Auto-création en mode `permissive` (cf. clarification Q4) : 1 row par message_id (pas 1 row par claim). Le champ `claim` reçoit le premier claim détecté ; `reason = 'auto_detected:{N}_unsourced_claims'`. Si une row existe déjà pour `(account_id, thread_id, claim)` non résolue, l'INSERT est silencieusement ignoré (ON CONFLICT DO NOTHING).
- **FR-007**: Le système MUST exposer une variable d'environnement `LLM_AGENT_SOURCING_MODE: Literal["strict", "permissive", "off"]` avec défaut `strict`. Le démarrage MUST refuser (fail-fast) `mode=off` quand `ENVIRONMENT=production`.
- **FR-008**: Le système MUST modifier le sélecteur de tools (F14, ou son équivalent injecté en F53) pour **forcer** la présence des 3 tools sourcing dans `state.available_tools` à chaque tour quand `mode != off`. Ces 3 tools sont injectés en post-processing si absents et **ne sont pas comptabilisés** dans la limite de 10 tools métier.
- **FR-009**: Le système MUST modifier le nœud `compose_response` (F53) en ajoutant une étape post-LLM : si `mode = strict` ET `validate_response.decision = retry` ET `state.sourcing_retry_count == 0`, ré-aiguiller vers `call_llm` avec un nouveau ToolMessage système (instruction explicite + spans des claims non sourcés) et incrémenter `state.sourcing_retry_count`. Maximum 1 retry sourcing par turn.
- **FR-010**: Le système MUST, si `state.sourcing_retry_count == 1` et que le retry sourcing échoue (LLM persiste sans cite_source), tronquer la réponse à la dernière phrase sourcée OU substituer par fallback "Je ne dispose pas de source vérifiée pour cette information.", marquer `agent_run.sourcing_status = 'failed'`, et émettre l'event `message_done` avec `payload.degraded=true`.
- **FR-011**: Le système MUST émettre l'event SSE `message_done` avec un `payload.sources: list[SourceRef]` agrégeant tous les `cite_source` invoqués pour ce message, avec `{source_id, title, publisher, url, page, section, verification_status, span: tuple[int,int] | null, citation_index: int}`.
- **FR-012**: Le frontend (chat F41 + extension sidepanel F52) MUST consommer `payload.sources` pour rendre les superscripts cliquables via le composant `<VizSourcePin>` (F40).
- **FR-013**: Le système MUST exposer l'endpoint `GET /admin/agent/metrics/sourcing?period=7d|30d|all` (gardé admin) retournant `{compliance_rate, unsourced_rate, retry_rate, fallback_rate, top_sources, top_unsourced_topics, period}`.
- **FR-014**: Le système MUST inclure une whitelist `app/agent/sourcing/whitelist.py` avec ≥ 20 patterns initiaux (regex insensitives), exposant `is_whitelisted(text: str) -> bool` et la liste `WHITELIST_PATTERNS: tuple[str, ...]`.
- **FR-015**: Le système MUST inclure un golden set `tests/golden/sourcing.jsonl` avec ≥ 50 paires `{text, expected_claims, expected_decision, mode}`. La CI MUST échouer si `precision < 0.85` OU `recall < 0.90` sur ce golden.
- **FR-016**: Le système MUST émettre un log structuré `sourcing_check` avec `{agent_run_id, claims_detected, citations_found, unsourced_count, mode, retried, decision, duration_ms}`.
- **FR-017**: Le système MUST ajouter une colonne `agent_run.sourcing_status: ENUM('ok','retried_ok','failed') NULL` (alembic migration 0035).
- **FR-018**: Le système MUST ajouter une colonne `chat_message.sources: JSONB NULL` (alembic migration 0035) pour requête rapide des sources d'un message.
- **FR-019**: Le système MUST garantir l'idempotence du retry sourcing : `state.sourcing_retry_count` est tracé dans le state LangGraph (champ Annotated `int` avec reducer `max`), persisté via le checkpointer F53.
- **FR-020**: Le système MUST inclure un test E2E pytest qui couvre les 3 modes (strict/permissive/off) sur un agent run réel (mocké LLM + mocké Voyage), avec des assertions sur `agent_run.sourcing_status`, `unsourced_flag`, `chat_message.sources`, et `tool_call_log` correspondant.
- **FR-021**: Le système MUST inclure un test E2E Playwright qui charge un message assistant avec sources dans le chat F41 et vérifie le rendu des superscripts + popover.

### Non-Functional Requirements

- **NFR-001**: Latence du détecteur < 50 ms p95 pour un message de 2000 caractères (mesurée en CI).
- **NFR-002**: Latence d'un `search_source` (Voyage embedding + pgvector cosine) < 500 ms p95 sur 1M lignes (mesurée en CI avec dataset de fixture 10k).
- **NFR-003**: Précision détecteur sur golden set : recall ≥ 90 %, precision ≥ 85 %. Bloque la CI sinon.
- **NFR-004**: Aucun faux-rejet permanent sur les patterns whitelist (testé golden, 0 faux-rejet attendu).
- **NFR-005**: Le détecteur ne doit pas dépendre du LLM (synchrone, pas d'appel externe). Voyage est uniquement utilisé pour `search_source`, pas pour le détecteur.
- **NFR-006**: La migration alembic 0035 MUST être idempotente et réversible (down).
- **NFR-007**: Coverage de la pipeline sourcing ≥ 80% (pyproject `fail_under=80`).
- **NFR-008**: Le validateur ajoute < 100 ms p95 au cycle complet d'un tour agent (mesuré en CI).

### Key Entities

- **UnsourcedFlag** : Trace persistante d'un claim non sourcé (par `flag_unsourced` ou auto-detection en mode permissive). Sous RLS `account_id`. Champs : id, account_id, user_id, agent_run_id, thread_id, message_id, claim, reason, source_of_change, created_at, resolved_at, resolved_by.
- **Claim** (in-memory dataclass) : Span détecté dans un texte assistant. Champs : `span: tuple[int,int]`, `kind: ClaimKind`, `raw: str`, `from_tool: bool`.
- **SourcingValidationResult** (Pydantic) : Résultat du validateur. Champs : `claims_detected: list[Claim]`, `citations_found: list[CitationRef]`, `unsourced_claims: list[Claim]`, `mode: SourcingMode`, `decision: Literal['accept','retry','fallback','annotate']`.
- **SourceRef** (Pydantic) : Référence source agrégée dans `chat_message.sources` et `payload.sources` SSE. Champs : `source_id, title, publisher, url, page, section, verification_status, citation_index, span: tuple[int,int] | null`.
- **agent_run.sourcing_status** : Enum `'ok'|'retried_ok'|'failed'|null`. Marque si le run a passé le contrôle sourcing avec ou sans retry, ou a fini en fallback.
- **chat_message.sources** : JSONB liste de `SourceRef` cités dans le message. Permet la consommation rapide en F49 (annexe PDF) et FR-013 (métriques).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Le LLM affirme "Le seuil GCF pour les PME est de 50 M USD" sans cite_source en mode strict → 1 retry sourcing avec instruction explicite ; soit le LLM ajoute `cite_source(...)` du document GCF, soit fallback "Je ne dispose pas de source vérifiée pour ce seuil — voulez-vous que je recherche?".
- **SC-002**: Le LLM affirme "L'ADEME estime à 6.0 kg CO2/litre le diesel" en mode strict → si `cite_source(ADEME-base-carbone-2024)` est dans les `tool_calls` → réponse acceptée ; sinon retry.
- **SC-003**: Phrase générique "Les PME africaines investissent peu dans la formation" (whitelist hit) → pas de retry, pas de bandeau, pas de unsourced_flag.
- **SC-004**: Annotation visuelle : "Le facteur ADEME^[¹] est de 6.0 kg CO2/litre^[¹]." Frontend rend les superscripts cliquables → popover source avec titre, éditeur, URL, statut.
- **SC-005**: `flag_unsourced(claim="Le BOAD acceptera mon dossier en 8 semaines", reason="aucun document public confirmant ce délai")` → INSERT en `unsourced_flag`, badge dans le chat, ligne visible dans `/admin/sources/unsourced-backlog`.
- **SC-006**: Rapport PDF F49 généré → annexe "Sources et références" auto-listée avec ≥ 12 sources, chaque chiffre du rapport pointe vers une source.
- **SC-007**: `GET /admin/agent/metrics/sourcing?period=7d` retourne `{compliance_rate ≥ 0.80, retry_rate ≤ 0.10, ...}` après 100 runs simulés.
- **SC-008**: Mode `permissive` → claim non sourcé → bandeau visible mais réponse non bloquée + `unsourced_flag` créé. Utile en staging/dev.
- **SC-009**: Mode `off` → aucune validation ; les 3 tools sourcing restent disponibles mais non forcés. Utilisé en CI pour les tests qui ne mesurent pas le sourcing.
- **SC-010**: Sur le golden set 50 paires : recall ≥ 0.90, precision ≥ 0.85 — sinon CI échoue.
- **SC-011**: `cite_source(source_id=<UUID inconnu>)` retourne une erreur structurée `source_not_found` ; le LLM peut alors invoquer `search_source` pour trouver une source réelle.
- **SC-012**: Performance : détecteur < 50ms p95 (2000 chars), `search_source` < 500ms p95 (10k sources fixture), validateur < 100ms p95.

## Hors-scope MVP (post-MVP)

- LLM-judge pour détection de claims ambigus — MVP : regex + keywords uniquement.
- Multilingue (anglais) du détecteur — MVP : FR uniquement (l'agent est FR par défaut, EN seulement pour dossiers offre `accepted_languages = ['en']`).
- Score de confiance par citation (la source est-elle "récente, exacte, autoritaire?") — post-MVP F58 (guardrails-eval).
- Suggestion automatique de sources externes à valider par admin — post-MVP.
- Vérification cross-source (deux sources se contredisent) — post-MVP.
- **Pré-chauffage pgvector au boot** (top 1000 sources) — post-MVP (cf. clarification Q5). Pré-chauffer uniquement si NFR-002 échoue en CI.

## Risques et points de vigilance

- **Trop strict = paralysie agent** : si tout claim doit être sourcé, l'agent passe son temps en retry. Mitigation : whitelist robuste + métrique `retry_rate < 10%`.
- **Faux positifs sur tool outputs** : "vous avez 3 projets" issu d'un tool DB ne doit pas déclencher. Mitigation : flag `from_tool=true` propagé par le contexte des ToolMessage du tour.
- **Sources verifiées limitées** : si la base ne contient pas de source pour un sujet, l'agent ne peut pas répondre. Solution : `flag_unsourced` honnête + `top_unsourced_topics` admin (FR-013).
- **Hallucination de source_id** : handler `cite_source` valide en DB. Sur erreur, retry possible avec `search_source`.
- **Performance pgvector cold cache** : première recherche lente. Pré-chauffage lazy au démarrage backend.
- **Voyage API down** : fallback `ILIKE`. Documenté + flag `degraded`.
- **Whitelist faux-positif** : "En général" peut whitelister un vrai claim. Mitigation : priorité aux claims forts (kind=number_with_unit) ; whitelist secondaire ; tests golden.
- **Annexe PDF lourde** : 100+ sources → pagination dédiée. À tester en F49.
- **Latence détecteur dépassée** : log warning, pas de blocage. Métrique surveillée.

## Assumptions

- L'agent F53 est en place (LangGraph core mergé PR #37).
- Le context builder F54 fournit le system prompt avec instruction explicite "cite tes sources" (à vérifier en plan).
- Le dispatcher F55 est en place avec catégorie `REINVOKE_LLM` pour les tools READ ; le stub `cite_source` mentionné dans `app/agent/dispatcher.py:322` sera remplacé.
- F03 a fourni la table `Source` avec colonne `embedding Vector(1024)` ; F07 maintient les sources verifiées.
- F40 (visualization library) fournit le composant frontend `<VizSourcePin>`.
- F49 (rapports/attestations UI) consommera `chat_message.sources` pour générer l'annexe PDF.
- Voyage AI client est déjà câblé via `app/embeddings_client.py` (modèle `voyage-3.5`, 1024 dim).
- Le SSE bridge F55 (`app/agent/sse_bridge.py`) supporte l'émission d'events custom via `state.events` ; ajouter `unsourced_claim` y est trivial.
- La migration alembic est sur la chaîne unique (head = 0034 F55) ; F56 = 0035.
- L'invariant constitutionnel P1 prévaut sur la fluidité conversationnelle : un claim sans source EST bloquant en prod.

## Dependencies

- **Spec dependencies**: F03 Source entity (table + embedding), F07 Sources management admin (UI back-office), F35 eval LLM postprocess (pipeline), F53 LangGraph core (graph + state), F54 context-builder (system prompt sourcing instructions), F55 dispatch SSE (REINVOKE_LLM category, sse_bridge).
- **External services**: Voyage AI (`voyage-3.5`) pour `search_source` ; PostgreSQL + pgvector pour cosine search ; OpenRouter (`minimax-m2.7`) pour le LLM agent.
- **Code zones modifiées (F56)** : `backend/app/agent/sourcing/*` (nouveau), `backend/app/agent/handlers/cite_source.py` + `search_source.py` + `flag_unsourced.py` (nouveaux), `backend/app/agent/nodes/select_tools.py` (forcing 3 tools), `backend/app/agent/nodes/compose_response.py` (validation post-LLM + retry sourcing), `backend/app/agent/state.py` (champs sourcing_retry_count + sourcing_status local), `backend/app/orchestrator/tool_registry.py` (registration 3 tools), `backend/alembic/versions/0035_*.py` (unsourced_flag + agent_run.sourcing_status + chat_message.sources), `backend/app/admin/agent_metrics.py` (endpoint), `backend/app/main.py` (router), `backend/pyproject.toml` (deps si besoin), `backend/tests/test_sourcing_*` + `frontend/tests/e2e/*`.
- **Code zones partagées (F57 en parallèle, NE PAS toucher)** : `backend/app/agent/nodes/recall_memory.py`, `backend/app/agent/context/loader.py`, `backend/app/embeddings/*`, nouvelle table `message_embeddings`.

## Notes

Cette feature consacre l'invariant constitutionnel P1 ("Toute affirmation factuelle pointe vers une Source verified") en mécanisme structurel non contournable. Elle s'aligne sur les principes Module 0 :
- **P1** : sourcing strict (cœur de F56).
- **P2 RLS** : `unsourced_flag` est `account_id` scoped.
- **P3 Audit append-only** : `unsourced_flag` ne peut pas être UPDATE/DELETE depuis le rôle applicatif.
- **P9 Tool-use Pydantic strict** : les 3 tools ont des schémas Pydantic v2 `extra='forbid'`.
- **P10 UI bottom sheet** : non applicable directement (F56 est backend + post-processing) ; les chips visuels (US7) sont du rendu inline non interactif → conforme.
