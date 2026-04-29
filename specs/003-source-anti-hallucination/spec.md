# Feature Specification: Source & Sourçage Anti-Hallucination

**Feature Branch**: `003-source-anti-hallucination`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: F03 — Entité Source & Sourçage Anti-Hallucination (Phase 0 — Fondations transversales, Module 0.1)

## Clarifications

### Session 2026-04-29

- Q: Stratégie d'invalidation du cache mémoire des décisions du middleware d'anti-hallucination ? → A: TTL court (5 minutes) ET invalidation immédiate déclenchée par tout changement de statut d'une source citée (cache key = hash(message) + version du statut des sources citées).
- Q: Format syntaxique des appels `cite_source` dans la sortie LLM analysée par le middleware ? → A: Tool-calls JSON natifs OpenRouter (function-calling structuré), pas de parsing de balises `[cite_source: id=N]` en clair dans le texte.
- Q: Stratégie d'indexation pour la recherche hybride `search_source` (full-text + vectoriel) ? → A: Index GIN sur `tsvector(title || publisher || notes)` pour le full-text + index IVFFlat sur `embedding vector(1024)` pour le vectoriel ; agrégation des deux scores côté requête.
- Q: Où est appliqué le filtre "exposer uniquement les objets catalogue dont la Source est `verified`" ? → A: Vues SQL dédiées `v_<entity>_verified` filtrant sur `source.verification_status = 'verified'`, consommées par le LLM et l'UI ; les tables brutes restent accessibles aux admins via RLS.
- Q: Comportement de `flag_unsourced` quand le LLM n'a pas de `user_id` explicite (appel système) ? → A: `account_id` lu depuis le contexte de requête actif (middleware `SET LOCAL app.account_id` de F02), `user_id` autorisé NULL et tracé comme appel système ; trace dans le journal d'audit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entité Source de premier rang avec FK obligatoire (Priority: P1)

En tant qu'architecte de la plateforme, je veux une entité Source persistée avec workflow `pending → verified → outdated/rejected` et une référence obligatoire (FK NOT NULL) depuis tous les objets du catalogue ESG (Indicateur, Critère, Formule, Seuil, Facteur d'émission, Document requis, Référentiel), afin de rendre l'absence de source impossible au niveau base de données.

**Why this priority**: Sans cette fondation, aucune autre garantie anti-hallucination n'a de valeur. C'est la couche structurelle qui rend l'invariant Module 0 (sourcing obligatoire) techniquement non-contournable.

**Independent Test**: Insérer un objet de catalogue sans `source_id` doit échouer (violation de contrainte). Insérer un objet de catalogue avec un `source_id` pointant sur une source `pending` doit produire un objet `draft` invisible au LLM et à l'UI PME.

**Acceptance Scenarios**:

1. **Given** la table `source` existe et la table `indicateur` a `source_id NOT NULL`, **When** un admin tente d'insérer un Indicateur sans `source_id`, **Then** l'insertion échoue avec une erreur de contrainte explicite.
2. **Given** une source en statut `pending`, **When** un admin lie un Indicateur à cette source, **Then** l'Indicateur reçoit le statut `draft` et n'apparaît dans aucune lecture exposée au LLM ou à la PME.
3. **Given** une source `verified` référencée par au moins un objet `verified`, **When** un admin tente de la supprimer, **Then** la suppression est rejetée (ON DELETE RESTRICT) et l'admin peut au plus la marquer `outdated`.
4. **Given** une source `pending` créée par admin A, **When** admin A tente de la passer `verified`, **Then** la transition est refusée — un admin différent (B) doit valider, et l'événement est tracé pour audit ultérieur.

---

### User Story 2 - Tools backend cite_source / search_source / flag_unsourced (Priority: P1)

En tant que dev backend (et future Phase 3 LLM), je veux trois opérations backend déclarées prêtes à être exposées en function-calling au LLM : `cite_source(source_id)`, `search_source(query, publisher?, k)`, `flag_unsourced(claim, context_json)`, afin que la couche LLM (Phase 3) puisse les consommer sans modification du backend.

**Why this priority**: Ces tools sont l'interface contractuelle entre LLM et catalogue. Sans eux, le middleware d'anti-hallucination (US3) n'a rien à valider et la chaîne entière s'effondre.

**Independent Test**: Appeler `cite_source` avec un id valide retourne l'enregistrement Source complet ; `search_source` retourne uniquement des sources `verified` triées par pertinence (full-text + similarité vectorielle) ; `flag_unsourced` enregistre l'incident dans une table dédiée et retourne un identifiant.

**Acceptance Scenarios**:

1. **Given** une source `verified` d'id 42, **When** `cite_source(42)` est appelé, **Then** la source 42 est retournée avec tous ses champs (url, title, publisher, version, date_publi, page, section).
2. **Given** une source d'id 42 en statut `pending`, **When** `cite_source(42)` est appelé, **Then** un refus structuré est retourné indiquant que la source n'est pas vérifiée.
3. **Given** un catalogue de sources `verified`, **When** `search_source(query="critères GCF")` est appelé, **Then** une liste paginée (k=10 par défaut) de sources `verified` est retournée, classée par score hybride full-text + vectoriel.
4. **Given** un utilisateur PME authentifié dans son tenant, **When** `flag_unsourced(claim, context_json)` est appelé, **Then** un enregistrement est créé avec `account_id`, `user_id`, horodatage, et l'identifiant créé est retourné.

---

### User Story 3 - Middleware d'anti-hallucination des messages LLM (Priority: P1)

En tant que garant de l'anti-hallucination, je veux qu'un middleware analyse chaque message produit par le LLM avant son retour au front et rejette tout message contenant un chiffre ESG/financier, un critère, un seuil ou une formule sans appel `cite_source` correspondant à une source `verified`. Le rejet doit déclencher un retry du LLM (max 2) avec une raison structurée. Au-delà, le LLM doit produire un message d'échappatoire légitime.

**Why this priority**: C'est la garde finale qui rend la promesse "pas de chiffre sans source vérifiée" tenable côté production. Sans elle, US1+US2 ne sont que des potentialités.

**Independent Test**: Soumettre une sortie LLM simulée "Le seuil GCF est de 50 tCO2e" sans `cite_source` est rejeté ; la même phrase avec `[cite_source: id=42]` pointant sur une source `verified` est acceptée ; "Je ne dispose pas de source vérifiée pour ce seuil" est accepté tel quel.

**Acceptance Scenarios**:

1. **Given** une sortie LLM contenant un montant suivi d'une unité (tCO2e, FCFA, %, kWh) sans `cite_source` attaché, **When** le middleware s'exécute, **Then** le message est rejeté avec une raison structurée et un retry est demandé.
2. **Given** une sortie LLM citant explicitement `cite_source: id=N` où N est `verified`, **When** le middleware s'exécute, **Then** le message est accepté et transmis au front.
3. **Given** une sortie LLM citant `cite_source: id=N` où N est `pending`, `outdated` ou inexistant, **When** le middleware s'exécute, **Then** le message est rejeté avec une raison structurée.
4. **Given** que 2 retries successifs ont échoué, **When** le middleware traite la 3ᵉ tentative, **Then** la PME reçoit le message "Je ne dispose pas de source vérifiée" — jamais une erreur technique.
5. **Given** un message déjà validé récemment (cache mémoire), **When** le même message est ré-évalué, **Then** la décision cachée est réutilisée pour respecter la contrainte de latence.

---

### User Story 4 - Composant UI Source cliquable (Priority: P2)

En tant que PME ou auditeur, je veux qu'à côté de chaque chiffre, critère, seuil ou formule affiché dans l'interface, un picto "source" cliquable ouvre une modale (via le pattern bottom sheet de la plateforme) listant les sources sous-jacentes avec URL deep-link officielle, version, date de capture et statut (Vérifiée, Non vérifiée, Obsolète), afin de pouvoir vérifier moi-même chaque affirmation.

**Why this priority**: Sans visibilité utilisateur, la promesse de transparence est invisible. C'est P2 car les API et règles de US1-3 livrent déjà la garantie ; l'UI rend la garantie expérientielle.

**Independent Test**: Le composant accepte une liste d'identifiants de sources, rend un picto cliquable, ouvre une bottom sheet listant les sources avec leur badge de statut visuel et lien externe vers l'URL officielle.

**Acceptance Scenarios**:

1. **Given** un texte affiché contenant un chiffre ESG, **When** la page se rend, **Then** un picto Source apparaît à côté du chiffre.
2. **Given** que l'utilisateur clique sur le picto, **When** la bottom sheet s'ouvre, **Then** chaque source liée est affichée avec titre, publisher, version, date, badge de statut et lien externe vers l'URL officielle.
3. **Given** une source `outdated`, **When** elle est affichée, **Then** un badge "Obsolète" visuellement distinct est rendu.

---

### User Story 5 - Annexe Sources auto-générée pour rapports (Priority: P2)

En tant qu'utilisateur générant un rapport (ESG, candidature, attestation), je veux que toutes les sources mobilisées dans le rapport soient agrégées en annexe "Sources et références" dédoublonnées, triées et formatées avec URL, titre, publisher, version et date, afin que le rapport ait une qualité scientifique et auditable.

**Why this priority**: Les rapports sont un livrable client clé, mais ils dépendent de la chaîne US1-3 pour avoir des sources fiables à lister.

**Independent Test**: Un utilitaire backend reçoit une liste d'identifiants de sources potentiellement dupliquée et produit un document texte structuré (markdown ou équivalent) listant chaque source unique une seule fois, trié, prêt à être inséré dans un rapport.

**Acceptance Scenarios**:

1. **Given** une liste de 10 identifiants dont 3 doublons, **When** l'utilitaire est appelé, **Then** la sortie liste 7 entrées uniques.
2. **Given** une source `pending` ou `rejected` dans la liste, **When** l'utilitaire est appelé, **Then** ces sources sont exclues de l'annexe.
3. **Given** une source manquant un champ obligatoire (URL ou titre), **When** l'utilitaire est appelé, **Then** un avertissement structuré est retourné et l'entrée est marquée "[source incomplète]".

---

### User Story 6 - Tableau de bord admin des claims non sourcés (Priority: P3)

En tant qu'admin, je veux visualiser la liste agrégée des claims que le LLM a marqués comme non sourçables (via `flag_unsourced`), avec contexte et fréquence, afin d'identifier en priorité les sources manquantes du catalogue à ajouter.

**Why this priority**: Outil d'amélioration continue. Indispensable à long terme mais le cœur fonctionne sans.

**Independent Test**: L'endpoint admin retourne une liste paginée et agrégée des claims non sourcés (regroupés par texte normalisé, avec compteur de fréquence) restreinte au tenant courant via RLS.

**Acceptance Scenarios**:

1. **Given** 5 entrées `flag_unsourced` dont 3 partagent un texte normalisé identique, **When** un admin appelle l'endpoint, **Then** 3 lignes agrégées sont retournées (1 avec compte=3, 2 avec compte=1).
2. **Given** un admin du tenant A, **When** il appelle l'endpoint, **Then** seuls les claims de son tenant sont visibles (RLS).

---

### Edge Cases

- Que se passe-t-il quand une source `verified` est rétrogradée à `outdated` alors qu'elle est référencée par 100 indicateurs ? Les indicateurs ne sont plus exposés au LLM ; un rapport admin liste les objets impactés.
- Que se passe-t-il si le service d'embeddings est indisponible au moment de la vérification d'une source ? La transition `pending → verified` est bloquée jusqu'à ce que l'embedding puisse être calculé et persisté.
- Que se passe-t-il si le LLM appelle `cite_source` avec un id qui n'existe pas ou appartient à un autre tenant ? Refus structuré avec raison ; l'incident est journalisé.
- Que se passe-t-il si la sortie LLM contient un chiffre purement narratif ("3 piliers de l'ESG") qui n'est pas un seuil ? Les heuristiques démarrent strictes (chiffre + unité ESG = exigence de source) ; tout chiffre sans unité ESG/financière est ignoré.
- Que se passe-t-il si un message LLM cite plusieurs sources et que l'une d'elles est `outdated` ? Le message est rejeté ; le LLM doit retenter avec uniquement des sources `verified`.
- Que se passe-t-il si deux admins valident la même source en parallèle ? Premier commit gagne ; le second reçoit un conflit de version (sera renforcé par le versioning F04).
- Que se passe-t-il quand le retry chain dépasse le budget de latence ? Le middleware coupe et renvoie l'échappatoire "pas de source vérifiée".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST persister une entité Source comportant au minimum : identifiant unique, URL, titre, publisher, version, date de publication, page, section, date de capture, identifiant du capteur, identifiant du valideur, statut de vérification (parmi `pending`, `verified`, `outdated`, `rejected`), notes libres.
- **FR-002**: Le système MUST imposer une contrainte d'intégrité empêchant tout enregistrement des entités catalogue (Indicateur, Critère, Formule, Seuil, Facteur d'émission, Document requis, Référentiel) sans référence à une Source. Pour les entités catalogue qui n'existent pas encore en base, la contrainte MUST être préparée et systématiquement appliquée à leur création.
- **FR-003**: Le système MUST exposer aux consommateurs (LLM, UI PME, rapports) uniquement les objets de catalogue dont la Source liée est en statut `verified`, via des vues SQL dédiées `v_<entity>_verified` filtrant sur `source.verification_status = 'verified'`. Les tables brutes restent accessibles aux administrateurs sous contrôle RLS (F02). Tout objet dont la Source n'est pas `verified` est en statut `draft` et invisible côté lecture publique.
- **FR-004**: Le système MUST exposer un endpoint de recherche paginée des sources, restreint aux administrateurs, filtrable par texte libre, publisher et statut ; ainsi qu'un endpoint de lecture unitaire d'une source en lecture publique (pour le picto et la page de vérification F30).
- **FR-005**: Le système MUST fournir une opération `cite_source(source_id)` qui retourne une Source si et seulement si elle est `verified`, et un refus structuré sinon.
- **FR-006**: Le système MUST fournir une opération `search_source(query, publisher?, k)` qui combine recherche full-text (index GIN sur `tsvector(title || publisher || notes)`) et similarité vectorielle (index IVFFlat sur `embedding vector(1024)` calculé au moment de la vérification via le fournisseur d'embeddings imposé par la stack), agrège les deux scores côté requête, et retourne uniquement des sources `verified`.
- **FR-007**: Le système MUST fournir une opération `flag_unsourced(claim, context_json)` qui enregistre l'incident dans une table dédiée avec `account_id` (lu depuis le contexte de requête actif via le middleware `SET LOCAL app.account_id`), `user_id` (autorisé NULL pour les appels système, tracé comme tel) et horodatage, et retourne l'identifiant créé. L'enregistrement MUST être soumis à l'isolation tenant (RLS).
- **FR-008**: Le système MUST exécuter un middleware sur chaque sortie LLM destinée au front qui :
  (a) détecte la présence de chiffres ESG/financiers (heuristique initiale : chiffre suivi d'unité parmi tCO2e, FCFA, EUR, %, kWh) et la mention de critères/seuils/formules par mots-clés ;
  (b) exige qu'au moins un appel `cite_source` au format tool-call JSON natif OpenRouter (function-calling structuré) ciblant une source `verified` accompagne le message ; aucun parsing de balises en clair n'est utilisé ;
  (c) rejette toute sortie ne respectant pas (b) avec une raison structurée ;
  (d) déclenche un retry du LLM, plafonné à 2, après quoi le message d'échappatoire "Je ne dispose pas de source vérifiée" est retourné à l'utilisateur ;
  (e) cache la décision en mémoire (TTL 5 minutes, clé = hash(message) + version du statut des sources citées) ; le cache est invalidé immédiatement si le statut d'une source citée change.
- **FR-009**: Le système MUST fournir un composant d'interface utilisateur réutilisable acceptant une liste d'identifiants de sources et rendant : un picto cliquable, l'ouverture d'un bottom sheet listant les sources avec titre, publisher, version, date de capture, badge de statut (Vérifiée / Non vérifiée / Obsolète) et lien externe vers l'URL officielle.
- **FR-010**: Le système MUST fournir un utilitaire backend qui, à partir d'une liste d'identifiants de sources, produit une annexe "Sources et références" dédoublonnée, triée, formatée en markdown (et helper section PDF), excluant les sources non `verified`.
- **FR-011**: Le système MUST fournir une table journalisant les claims non sourcés (FR-007) et un endpoint admin agrégé (regroupement par texte normalisé + compteur de fréquence) restreint par RLS au tenant courant.
- **FR-012**: Le système MUST conserver, dans le dépôt de prompts, un template de système prompt LLM contenant les instructions non-négociables d'anti-hallucination (référençant Module 0.1), prêt à être consommé par la Phase 3.
- **FR-013**: Le système MUST refuser la transition d'une source `pending → verified` lorsque le valideur est identique au capteur (double validation obligatoire) et MUST tracer chaque transition dans le journal d'audit (extension par F04).
- **FR-014**: Le système MUST refuser la suppression d'une Source référencée par un objet `verified` (ON DELETE RESTRICT) ; il MUST permettre la transition vers `outdated`.
- **FR-015**: Le système MUST appliquer l'isolation multi-tenant (RLS via `account_id NOT NULL`) sur les tables introduites par cette feature (notamment le journal des claims non sourcés). Les sources elles-mêmes appartiennent au catalogue global mais leur lecture admin reste contrôlée par les rôles définis en F02.
- **FR-016**: Le système MUST recalculer et persister l'embedding d'une source au moment de sa transition `pending → verified` ; si le service d'embeddings est indisponible, la transition MUST échouer proprement avec message structuré.

### Key Entities

- **Source** : Référence officielle vérifiable. Attributs : URL, titre, publisher, version, date de publication, page, section, date et auteur de capture, auteur de vérification, statut (`pending`/`verified`/`outdated`/`rejected`), notes, vecteur d'embedding 1024 dimensions calculé à la vérification.
- **UnsourcedClaimLog** : Journal d'incidents lorsque le LLM ne trouve pas de source vérifiée pour une affirmation. Attributs : identifiant, identifiant tenant, identifiant utilisateur, texte du claim, contexte JSON, horodatage de création.
- **Lien Catalogue ↔ Source** : Référence obligatoire (NOT NULL) depuis chaque entité catalogue (Indicateur, Critère, Formule, Seuil, Facteur d'émission, Document requis, Référentiel) vers la Source qui l'atteste. Une entité catalogue dont la Source n'est pas `verified` est masquée des lectures exposées.
- **Décision de validation LLM** : Verdict structuré produit par le middleware (accepté / rejeté + raison) ; conservé en cache mémoire à des fins de latence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : 0 objet du catalogue exposé au LLM ou à l'UI sans Source en statut `verified`, mesuré par un audit SQL automatisé exécuté quotidiennement.
- **SC-002** : Sur un eval set d'au moins 20 cas représentatifs (chiffres ESG/financiers avec et sans citation), 100% des sorties LLM contenant un chiffre ESG sans citation sont rejetées par le middleware avant retour au front.
- **SC-003** : Le composant UI de citation rend correctement les trois états visuels (Vérifiée, Non vérifiée, Obsolète) et expose un lien externe fonctionnel pour 100% des sources testées en page de démonstration.
- **SC-004** : Une annexe générée pour un rapport contenant au minimum 5 sources est lisible, dédoublonnée et datée à 100% (vérifié par test automatisé).
- **SC-005** : Sur un catalogue de 5000 sources `verified`, 95% des appels `search_source` répondent en moins de 200ms (mesuré p95 sur 1000 appels).
- **SC-006** : Le middleware de validation ajoute moins de 50ms de latence par message en moyenne sur la trace de production simulée (mesuré sur 500 messages).
- **SC-007** : 100% des transitions `pending → verified` réalisées par un valideur différent du capteur sont tracées dans le journal d'audit (audit hebdomadaire sur les 7 derniers jours).
- **SC-008** : 100% des entrées `unsourced_claim_log` sont correctement isolées par tenant (audit RLS automatisé).

## Assumptions

- L'authentification PME/Admin et le RLS multi-tenant fournis par F02 sont disponibles et utilisables tels quels (rôles SQL `app_user` / `migrator`, ENUM `account_user_role`, middleware `SET LOCAL app.account_id`).
- Le schéma de base de F01 (18 tables, `account_id NOT NULL`, type Money pegged FCFA-EUR 655.957, colonne `vector(1024)`) est disponible. Les tables catalogue (Indicateur, Critère, Formule, Seuil, Facteur d'émission, Document requis, Référentiel) qui n'existent pas encore en base auront leur contrainte FK Source NOT NULL appliquée à leur création (Phase 1).
- L'audit log append-only et le versioning des référentiels seront livrés par F04 ; cette feature s'appuie sur des hooks d'audit existants ou pose les insertions structurées qu'F04 consommera.
- Le fournisseur d'embeddings (Voyage AI, modèle 1024 dimensions, FR-friendly) configuré en F01 est disponible pour calculer l'embedding d'une source à sa vérification.
- Le LLM lui-même (Phase 3 via OpenRouter) n'est pas livré ici ; cette feature livre les contrats backend (tools, middleware, template de prompt) que la Phase 3 consommera sans modification du backend.
- Les heuristiques initiales de détection des chiffres ESG démarrent strictes (chiffre + unité ESG/financière) et seront affinées via l'eval set F35.
- La plateforme est fermée (PME inscrites + Admin) ; aucune lecture n'est exposée à un public anonyme hors lecture unitaire d'une source pour la page de vérification F30 et pour le picto Source.
- Le pattern UI bottom sheet est le standard de la plateforme pour ouvrir des contenus contextuels comme la liste des sources d'une affirmation.
