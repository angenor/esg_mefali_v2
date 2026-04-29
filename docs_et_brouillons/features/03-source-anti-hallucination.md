# F03 — Entité Source & Sourçage Anti-Hallucination

**Phase** : 0 — Fondations transversales
**Modules brainstorm** : 0.1 (Sourçage et Anti-Hallucination — cœur de la crédibilité)
**Dépendances** : F01, F02
**Estimation** : 2–3 jours

## Contexte et objectif

Le sourçage est l'**avantage compétitif décisif** de la plateforme. En finance verte/ESG, une affirmation non sourcée n'a aucune valeur — un fund officer doit pouvoir cliquer sur n'importe quel chiffre et vérifier la source officielle.

Cette feature pose **les rails techniques et applicatifs** qui rendent toute hallucination LLM techniquement impossible :
1. L'entité `Source` est élevée au rang de citoyen de premier ordre.
2. Tout objet du catalogue (Indicateur, Critère, Formule, Seuil, Facteur d'émission, Document requis, Référentiel) référence au moins une `Source` `verified` via FK NOT NULL.
3. Le LLM dispose des tools `cite_source`, `search_source`, `flag_unsourced`.
4. Un middleware backend rejette tout message LLM contenant des assertions ESG/financières non sourcées et déclenche un retry.
5. L'UI affiche un picto cliquable sur **chaque** chiffre, et les rapports PDF embarquent une annexe "Sources et références" auto-générée.

Cette feature ne livre pas encore le LLM lui-même (Phase 3) ni le back-office d'édition (Phase 1) — mais elle livre **le squelette d'API, les contraintes DB, les tools et l'utilitaire d'annexe sources** que ces phases consommeront.

## User Stories

### US1 — L'entité Source existe avec ses champs et son cycle de vie (P1)
**En tant qu'**architecte de la plateforme,
**je veux** une table `source` complète avec workflow `pending → verified` et FK obligatoire depuis tous les objets du catalogue,
**afin de** rendre l'absence de source impossible au niveau base de données.

**Test indépendant** : insérer un `Indicateur` sans `source_id` → INSERT échoue (constraint violation). Insérer un `Indicateur` avec `source_id` pointant vers une source `pending` → l'objet reste en `draft` et n'est pas exposé au LLM.

### US2 — Tools LLM cite_source / search_source / flag_unsourced disponibles côté backend (P1)
**En tant que** dev backend,
**je veux** ces 3 tools déclarés en function-calling OpenRouter et leur logique implémentée,
**afin que** la Phase 3 puisse les exposer au LLM sans plus toucher au backend.

**Test indépendant** : appeler `cite_source(source_id=valid)` renvoie l'objet Source ; `search_source(query="GCF criteria")` renvoie une liste paginée de sources `verified` ; `flag_unsourced(claim="…")` enregistre l'incident en DB pour analyse.

### US3 — Middleware de validation des messages LLM (P1)
**En tant que** garant de l'anti-hallucination,
**je veux** qu'un middleware analyse la sortie LLM avant retour au front et rejette si :
- le message contient des chiffres ESG/financiers (regex + heuristiques) **sans** appel à `cite_source` correspondant,
- ou cite des critères/formules/seuils sans source.

**Et** demande au LLM un retry (max 2) avec un message structuré expliquant l'erreur.
**Afin de** respecter la règle "pas de chiffre, pas de critère, pas de formule sans source vérifiée".

**Scénarios** :
1. LLM répond "Le seuil GCF est de 50 tCO2e" sans `cite_source` → rejeté, retry.
2. LLM répond "Le seuil GCF est de 50 tCO2e [cite_source: id=42]" et la source 42 est `verified` → accepté.
3. LLM répond "Je ne dispose pas de source vérifiée pour ce seuil" → accepté (échappatoire légitime).

### US4 — Picto Source cliquable côté frontend (composant réutilisable) (P2)
**En tant que** PME ou auditeur,
**je veux** voir un picto Source à côté de chaque chiffre/critère/formule affiché et pouvoir cliquer pour ouvrir une modale listant les sources (URL deep-link, version, date capture, statut),
**afin de** vérifier moi-même que la plateforme dit la vérité.

**Test indépendant** : un composant Vue `<SourceCite :source-ids="[…]"/>` rend l'icône, ouvre une modale, déep-linke vers l'URL officielle, affiche un badge `Vérifiée` / `Non vérifiée` / `Obsolète`.

### US5 — Annexe "Sources et références" auto-générée dans les rapports PDF (P2)
**En tant qu'**utilisateur générant un rapport (ESG, candidature, attestation),
**je veux** que toutes les sources mobilisées dans le rapport soient listées en annexe avec URL, titre, publisher, version, date,
**afin que** le rapport ait une qualité scientifique/auditable.

**Test indépendant** : un utilitaire `build_sources_appendix(source_ids: list[int]) -> str` (ou markdown ou HTML) qui dédoublonne, trie et formate les sources. Testable sans rapport réel.

### US6 — `flag_unsourced` log et tableau de bord admin (P3)
**En tant qu'**admin,
**je veux** voir la liste des claims que le LLM a marqués comme non sourçables, avec contexte et fréquence,
**afin de** identifier les sources manquantes du catalogue à ajouter en priorité.

## Exigences fonctionnelles

- **FR-001** : Table `source` : `id, url, title, publisher, version, date_publi, page, section, captured_at, captured_by, verified_by, verification_status ENUM('pending','verified','outdated','rejected'), notes`.
- **FR-002** : Contrainte `NOT NULL` sur `source_id` pour : `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `document_requis`, `referentiel`. (Tables FR-002 dont les colonnes seront ajoutées par migration ; pour les tables qui n'existent pas encore, on prépare la contrainte qui sera appliquée à leur création.)
- **FR-003** : Vue applicative ou query helper qui ne renvoie un objet du catalogue (Indicateur, Référentiel, …) que si `source.verification_status = 'verified'`. Sinon il est `draft` et masqué côté LLM/PME.
- **FR-004** : Endpoint `GET /sources?q=&publisher=&status=` paginé, accessible aux admins. Un endpoint `GET /sources/{id}` exposé en lecture publique (besoins de la page de vérif F30 + du picto source).
- **FR-005** : Tools backend (FastAPI handlers, prêts à être déclarés en function-calling) :
  - `cite_source(source_id) -> Source` (lecture d'une source).
  - `search_source(query, publisher?, k=10) -> list[Source]` (full-text Postgres `tsvector` + recherche vectorielle hybride. Les embeddings des sources `verified` sont calculés via **Voyage AI `voyage-3.5`** (1024 dim, FR-friendly) au moment de la vérification et stockés dans une colonne `source.embedding vector(1024)`).
  - `flag_unsourced(claim, context_json) -> id` (insert dans `unsourced_claim_log` avec `account_id`, `user_id`, `created_at`).
- **FR-006** : Middleware FastAPI `validate_llm_output(message_json) -> ok|reject(reason)` :
  - Détecte présence de chiffres/critères/formules via heuristiques (regex montant/pourcentage/unité, mots-clés "critère", "seuil", "formule").
  - Vérifie qu'**au moins un** `cite_source` est attaché au message si détection.
  - Rejette sinon avec raison structurée pour retry LLM.
- **FR-007** : Composant Vue `<SourceCite :source-ids :inline?>` : badge cliquable, modale au clic, état visuel selon `verification_status`.
- **FR-008** : Utilitaire backend `build_sources_appendix(source_ids) -> markdown` (et helper `to_pdf_section`).
- **FR-009** : Table `unsourced_claim_log` : `id, account_id, user_id, claim_text, context_json, created_at`. Endpoint admin `GET /admin/unsourced-claims` agrégé.
- **FR-010** : Le système prompt LLM (template au moins, pas l'orchestration LangGraph) inclut le bloc d'instructions non-négociable cité dans le brainstorming Module 0.1. Sera réutilisé en Phase 3.

## Exigences non-fonctionnelles

- **NFR-001** : `search_source` doit répondre en < 200ms p95 sur un catalogue de 5000 sources (index full-text sur `title || publisher || notes`).
- **NFR-002** : Le middleware de validation ajoute < 50ms de latence par message.
- **NFR-003** : Aucune source ne peut être supprimée si elle est référencée par un objet `verified` (FK avec ON DELETE RESTRICT). À défaut, elle peut être marquée `outdated`.
- **NFR-004** : Workflow de double-validation : un admin différent du créateur doit valider une source pour la passer `pending → verified`. Tracé dans `audit_log` (F04).

## Entités clés

- **Source** (FR-001) — citoyen de premier rang.
- **UnsourcedClaimLog** (FR-009).
- Champs `source_id NOT NULL` (ou `NOT NULL` après cohérence) sur les entités catalogue.

## Success Criteria

- **SC-001** : 0 objet du catalogue exposé au LLM ou à l'UI sans source `verified` (testé par requête d'audit).
- **SC-002** : 0 message LLM contenant un chiffre ESG/financier sans `cite_source` ne sort de l'API (testé par eval set de 20 cas).
- **SC-003** : `<SourceCite>` affiche correctement les 3 états (verified, pending, outdated) sur Storybook ou page de démo.
- **SC-004** : Annexe Sources rendue dans un rapport PDF d'exemple est lisible, dédoublonnée, datée.

## Hors-scope MVP (post-MVP)

- `archived_url` (snapshot Wayback / archive interne).
- `hash_contenu` pour détecter les changements de la source officielle.
- Cron de revalidation des sources (vérification périodique HEAD → si page change → flag `outdated`).
- Scraper automatique de sites officiels (GCF, BOAD…) pour extraire des sources candidates.
- Workflow de revue communautaire des sources.

## Risques et points de vigilance

- **Heuristiques de détection des chiffres ESG** : trop strict → faux positifs (LLM coincé, expérience cassée) ; trop lâche → faux négatifs (hallucination passe). Itérer avec eval set (F35). Démarrer simple : tout chiffre suivi d'une unité (tCO2e, FCFA, %, kWh) DOIT être sourcé.
- **Performance du middleware** : si chaque message LLM est ré-analysé, attention au coût latence. Cacher la décision en mémoire pour les messages déjà validés.
- **UX du retry** : si on retry 2 fois et que ça échoue, le LLM doit dire "je ne dispose pas de source vérifiée" — pas afficher une erreur technique à la PME.
- **Sources externes en évolution** : la BCEAO peut publier la taxonomie UEMOA v2 demain. Le versioning de F04 (à venir) doit gérer cela proprement (`valid_from/valid_to`).
