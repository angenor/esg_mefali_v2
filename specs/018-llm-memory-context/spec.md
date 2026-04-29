# Feature Specification: F18 — Mémoire Contextuelle LLM (15 derniers messages + RAG pgvector)

**Feature Branch**: `018-llm-memory-context`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: F18 — Mémoire Contextuelle (15 derniers messages + RAG pgvector + recall_history). Phase 3 — Chat & LLM Tool-Use. Modules brainstorm 1.4. Dépendances: F03, F11, F12, F13, F14.

## Clarifications

### Session 2026-04-29

- Q: Modèle d'embedding et dimension à utiliser ? → A: `voyage-3.5` (1024 dimensions) — aligné socle infrastructure.
- Q: Type d'index vectoriel sur la colonne embedding ? → A: `ivfflat lists=100` (suffisant MVP < 100k messages, migration `hnsw` post-MVP).
- Q: Mécanisme de re-essai pour les embeddings échoués ? → A: hors-scope MVP (re-traitement manuel ou batch ultérieur ; le message est persisté avec embedding nul).
- Q: Estimateur de tokens utilisé ? → A: approximation `n_caractères / 4` (tokenizer dédié post-MVP si dérive constatée).
- Q: Périmètre des champs profil exposés au LLM ? → A: whitelist explicite avec indicateurs ESG synthétiques uniquement, deny-by-default sur les champs sensibles (FR-014).

## User Scenarios & Testing *(mandatory)*

Cette feature livre la **mémoire contextuelle** consommée par le LLM à chaque tour de conversation : un profil entreprise + projets toujours frais, une fenêtre des 15 derniers messages préservée en clair, et un mécanisme de rappel sémantique de l'historique ancien (RAG sur embeddings).

### User Story 1 - Profil entreprise + projets injectés à chaque tour (Priority: P1)

En tant que PME utilisatrice, je veux que le LLM connaisse en permanence l'identité de mon entreprise (raison sociale, secteur, effectifs, CA, pays) et la liste de mes projets actifs sans que j'aie à les répéter, afin de ne pas avoir des conversations qui repartent de zéro.

**Why this priority**: Sans cette injection systématique, chaque échange impose à la PME de re-décrire son contexte — l'expérience produit devient inutilisable et le LLM hallucine des hypothèses sur l'entreprise.

**Independent Test**: La PME édite manuellement son CA dans `/profil/entreprise`, ouvre le chat, demande "calcule mon ratio CA / effectifs". La réponse utilise la nouvelle valeur (zéro lecture stale, zéro re-saisie).

**Acceptance Scenarios**:

1. **Given** une PME avec un profil F11 renseigné et 3 projets F12 actifs, **When** elle envoie un message au chat, **Then** la requête envoyée à l'orchestrateur LLM contient un bloc système avec son profil compact et ses projets actifs.
2. **Given** une PME qui vient d'éditer son effectif salariés, **When** elle envoie son prochain message, **Then** la valeur reflétée dans le contexte LLM est la nouvelle valeur (pas un cache).
3. **Given** une PME sans projets actifs, **When** elle envoie un message, **Then** la section "Projets actifs" est absente du contexte (pas de bruit vide).

---

### User Story 2 - Budget tokens contrôlé et compaction (Priority: P1)

En tant que développeur opérant la plateforme, je veux que le contexte injecté (profil + projets + historique récent) ne dépasse jamais un budget configuré, avec compaction automatique en cas de dépassement, afin de maîtriser les coûts d'inférence et de ne pas saturer la fenêtre du modèle.

**Why this priority**: Une PME avec 30 projets et 100 messages saturerait la fenêtre — sans budget, les coûts dérapent et la qualité chute (perte d'instructions système).

**Independent Test**: Charger un compte de test avec 25 projets et 80 messages, builder le contexte, vérifier que la taille estimée reste sous le budget configuré et que les éléments compactés conservent les champs critiques (nom, statut, secteur, montants).

**Acceptance Scenarios**:

1. **Given** une PME avec 25 projets dont 12 actifs, **When** le contexte est construit, **Then** seuls les projets actifs sont listés et limités à 10 entrées maximum (les autres sont remplacés par un compteur "+N projets").
2. **Given** un projet avec une description de 2 000 caractères, **When** il est compacté, **Then** la description est tronquée à 200 caractères avec ellipse, mais nom/statut/secteur/montants sont préservés intacts.
3. **Given** un budget de 2 000 tokens, **When** la somme estimée dépasse le budget, **Then** le constructeur réduit en priorité les descriptions, puis le nombre de projets, puis raccourcit la fenêtre des messages, et ne dépasse jamais le budget une fois la dernière passe terminée.

---

### User Story 3 - 15 derniers messages préservés en clair (Priority: P1)

En tant que développeur, je veux que les 15 derniers messages utilisateur + assistant du thread courant soient inclus tels quels dans le contexte, afin que le LLM ait la mémoire courte de la conversation immédiate et puisse référencer un échange précédent.

**Why this priority**: La cohérence dialogale repose sur cette fenêtre — sans elle, le LLM oublie ce qui vient d'être discuté trois tours plus tôt.

**Independent Test**: Créer un thread avec 20 messages, builder le contexte, vérifier que les 15 plus récents sont présents, dans l'ordre chronologique, avec leurs payloads tools quand pertinent (visualisations).

**Acceptance Scenarios**:

1. **Given** un thread de 20 messages, **When** on construit le contexte, **Then** les 15 plus récents sont inclus dans l'ordre chronologique.
2. **Given** un message assistant avec un payload de visualisation (F16), **When** il est inclus dans la fenêtre, **Then** le label / titre du payload accompagne le message (pas le JSON brut volumineux).
3. **Given** un thread de 8 messages seulement, **When** on construit le contexte, **Then** les 8 messages sont inclus sans erreur (pas de borne min).

---

### User Story 4 - Tool recall_history pour la mémoire longue (Priority: P2)

En tant que PME, je veux pouvoir dire au LLM "tu te rappelles ce qu'on avait dit sur le projet biogaz le mois dernier ?" et que le LLM retrouve les éléments enterrés dans la conversation, afin de ne pas reperdre des décisions ou hypothèses anciennes.

**Why this priority**: C'est la valeur "mémoire long terme" différenciante, mais elle n'a de sens que sur des threads volumineux (> 15 messages). Reportable au cycle suivant si pression budget.

**Independent Test**: Créer un thread de 50 messages avec 5 messages mentionnant "biogaz Sénégal" enterrés au milieu. Invoquer le tool `recall_history(query="biogaz Sénégal")`. Le résultat doit retourner ≤ 5 messages les plus pertinents sémantiquement, antérieurs aux 15 derniers, et exclusivement issus du thread courant.

**Acceptance Scenarios**:

1. **Given** un thread de 50 messages, **When** le LLM invoque `recall_history(query="biogaz")`, **Then** il reçoit jusqu'à 5 messages anciens pertinents, chacun avec un snippet, le `thread_id`, l'horodatage et l'auteur (user / assistant).
2. **Given** un thread de 10 messages seulement, **When** le sélecteur d'outils (F14) construit la liste des tools disponibles, **Then** `recall_history` n'est PAS exposé (utile uniquement quand l'historique dépasse la fenêtre récente).
3. **Given** une PME A et une PME B sur la même instance, **When** la PME A invoque `recall_history`, **Then** aucun message de la PME B ne remonte (isolation par compte respectée).

---

### User Story 5 - Embeddings calculés à la persistance (Priority: P1)

En tant que développeur, je veux que chaque message persisté ait un embedding vectoriel calculé et stocké au moment de l'écriture, afin d'alimenter immédiatement la recherche sémantique (recall_history US4 et search_source F03) sans batch différé.

**Why this priority**: Sans embeddings persistés, US4 ne fonctionne pas et F03 perd sa source vectorielle. C'est le socle data des deux features.

**Independent Test**: Envoyer un message via l'API chat, lire en base immédiatement après, vérifier que la colonne embedding est non nulle et a la dimensionnalité attendue (1024).

**Acceptance Scenarios**:

1. **Given** un nouveau message persisté, **When** la transaction se termine avec succès, **Then** sa colonne embedding contient un vecteur de dimension 1024.
2. **Given** un message dont le contenu est exclusivement un payload tool (visualisation, action), **When** l'embedding est calculé, **Then** c'est le label / titre humain du payload qui est embeddé (pas le JSON brut), pour rester pertinent sémantiquement.
3. **Given** une indisponibilité temporaire du fournisseur d'embeddings, **When** la persistance d'un message échoue côté embedding, **Then** le message est tout de même persisté (embedding nul) et marqué pour re-essai ultérieur — la conversation n'est pas bloquée.

---

### User Story 6 - Synchronisation édition manuelle ↔ contexte LLM (Priority: P1)

En tant que PME, je veux qu'une édition manuelle de mon profil entreprise ou de mes projets soit immédiatement reflétée dans le contexte vu par le LLM au prochain tour, afin que mes corrections aient un effet sans délai ni purge de cache à comprendre.

**Why this priority**: Un cache stale est la pire expérience produit possible (la PME corrige, le LLM ignore la correction et propose des analyses fausses).

**Independent Test**: Modifier l'effectif de la PME via l'API profil, envoyer un message dans le chat dans la foulée, vérifier que la valeur lue par le constructeur de contexte est la nouvelle valeur.

**Acceptance Scenarios**:

1. **Given** une édition de profil entreprise, **When** la PME envoie un message dans la seconde qui suit, **Then** le contexte injecté contient la nouvelle valeur (lecture directe, pas de TTL ni d'invalidation à orchestrer).
2. **Given** une suppression de projet, **When** un nouveau tour démarre, **Then** ce projet n'apparaît plus dans la section "Projets actifs".

---

### Edge Cases

- **Profil vide** : PME qui vient de s'inscrire sans avoir rempli le profil — le contexte ne contient pas de section "Profil entreprise" plutôt qu'un bloc à champs vides.
- **Aucun projet** : section "Projets actifs" omise plutôt que "[]".
- **Message extrêmement long** (>10 000 caractères) : tronqué dans la fenêtre récente avec marqueur "[…tronqué…]" mais embeddé sur les premiers 8 000 caractères.
- **Embedding indisponible** : message persisté avec embedding nul, recall_history saute simplement ces messages, ré-embedding différé hors-scope MVP.
- **Thread courant à exactement 15 messages** : recall_history non exposé (seuil strict > 15).
- **Query recall_history vide ou < 3 caractères** : tool retourne une liste vide sans appel embedding (économie de coût).
- **Champs sensibles** : tokens, mots de passe, identifiants techniques internes ne doivent jamais apparaître dans le contexte (whitelist explicite).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer un constructeur de contexte qui, à partir d'un identifiant de compte et d'un identifiant de thread, assemble un paquet contenant : profil entreprise compact, projets actifs compacts, fenêtre des 15 derniers messages.
- **FR-002**: Le système DOIT fournir un compacteur de profil entreprise qui ne retient qu'une whitelist de champs métier (raison sociale, secteur, effectifs, CA, pays, statut juridique, indicateurs ESG synthétiques) et exclut tout champ sensible (tokens, identifiants techniques, données personnelles non nécessaires).
- **FR-003**: Le système DOIT fournir un compacteur de projets qui filtre sur les statuts actifs (≠ clôturé / annulé), limite à 10 projets, tronque les descriptions à 200 caractères et préserve nom, statut, secteur, montants typés.
- **FR-004**: Le système DOIT estimer la taille en tokens du contexte construit (approximation acceptable : nb_caractères / 4 ou tokenizer dédié) et garantir que la sortie ne dépasse pas le budget configurable (`CONTEXT_TOKEN_BUDGET`, défaut 2 000 tokens).
- **FR-005**: En cas de dépassement du budget, le système DOIT compacter dans un ordre déterministe : 1) tronquer descriptions, 2) réduire le nombre de projets, 3) raccourcir la fenêtre messages (jamais sous 5).
- **FR-006**: Le système DOIT exposer un tool `recall_history(query, k=5)` qui calcule l'embedding de la query, exécute une recherche par similarité cosinus sur les embeddings de messages, filtre par compte (RLS), restreint au thread courant, exclut les 15 derniers messages, et retourne au plus k résultats avec snippet, identifiant de message, identifiant de thread, horodatage, rôle.
- **FR-007**: Le système DOIT calculer et persister l'embedding (dimension 1024) de chaque message au moment de la persistance ; en cas d'échec du fournisseur, le message DOIT être quand même persisté (embedding nul, marqueur de re-essai).
- **FR-008**: Pour les messages dont le contenu est un payload tool (visualisation, action), le système DOIT embedder le label / titre humain du payload plutôt que le JSON brut.
- **FR-009**: Le système NE DOIT PAS mettre en cache le profil ni les projets entre tours : relecture systématique en base à chaque construction de contexte.
- **FR-010**: Le contexte produit DOIT être un message système ajouté en tête de la conversation envoyée au LLM, formaté en sections lisibles (`# Profil entreprise`, `# Projets actifs`, `# Conversation récente`).
- **FR-011**: Le tool `recall_history` NE DOIT être exposé au sélecteur d'outils (F14) QUE pour les threads ayant strictement plus de 15 messages.
- **FR-012**: La recherche `recall_history` DOIT être restreinte au thread courant uniquement (cross-thread reporté post-MVP).
- **FR-013**: Le système DOIT créer un index de recherche vectorielle sur la colonne embedding des messages, optimisé pour la similarité cosinus, dimensionné pour < 100 000 messages en MVP.
- **FR-014**: Aucun champ sensible (mots de passe, jetons d'authentification, secrets API) NE DOIT apparaître dans le contexte construit. La whitelist du compacteur fait foi (deny by default).
- **FR-015**: La recherche `recall_history` DOIT respecter l'isolation par compte (RLS) — un compte ne peut jamais récupérer un message d'un autre compte, même par collision sémantique.
- **FR-016**: Toute query `recall_history` de moins de 3 caractères ou vide DOIT retourner une liste vide sans appeler le fournisseur d'embeddings (économie de coût).

### Key Entities

- **ContextBundle** : agrégat éphémère retourné par le constructeur — contient profil compact, projets compacts, fenêtre messages, taille estimée. Non persisté, reconstruit à chaque tour.
- **chat_message.embedding** (entité existante F13) : vecteur de dimension 1024 calculé par le fournisseur d'embeddings, indexé pour recherche vectorielle cosinus.
- **CONTEXT_TOKEN_BUDGET** : paramètre de configuration globale (défaut 2 000), exposé via variable d'environnement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur 5 cas d'édition manuelle de profil suivis d'une question dépendant du champ édité, 100 % des réponses LLM utilisent la nouvelle valeur (zéro stale).
- **SC-002**: Sur un thread de 50 messages contenant un sujet enterré, l'invocation de `recall_history` retourne le message pertinent en moins de 200 ms p95.
- **SC-003**: Sur un compte chargé avec 25 projets et 100 messages, le contexte construit ne dépasse jamais le budget tokens configuré (vérifié sur 100 invocations consécutives).
- **SC-004**: 100 % des messages persistés depuis l'activation de la feature ont un embedding non nul OU un marqueur de re-essai (zéro perte silencieuse).
- **SC-005**: Le constructeur de contexte exécute une lecture profil + projets + 15 derniers messages en moins de 150 ms p95 (sur jeu de données représentatif).
- **SC-006**: Aucun champ sensible n'apparaît dans le contexte sur 1 000 invocations aléatoires (audit automatisé).

## Assumptions

- F11 (profil entreprise) et F12 (profils projets) exposent une API de lecture stable consommable par le constructeur.
- F13 fournit déjà la table des messages avec une colonne embedding préparée (dimension 1024) et un endpoint de persistance.
- F14 (orchestrateur LLM + sélecteur d'outils) sait consommer un contexte système en tête de conversation et accepte une liste dynamique d'outils.
- Le fournisseur d'embeddings vectoriels (Voyage AI, modèle `voyage-3.5`, dimension 1024) est déjà configuré côté infrastructure (clé API, client HTTP).
- Le moteur de stockage relationnel supporte un index vectoriel (extension pgvector activée — invariant socle).
- Les coûts d'embedding par message (~1 appel API par message persisté) sont budgétairement acceptables pour le MVP — un suivi de quota Voyage est mis en place hors de cette feature.
- La compaction "projets actifs" se base sur un statut métier interprétable (ex : statut ≠ `cloture` / `annule`), aligné avec la convention F12.
- L'estimation tokens par division du nombre de caractères par 4 est acceptable pour le MVP ; un tokenizer plus précis sera intégré post-MVP si dérive constatée.
- La recherche vectorielle est limitée au thread courant en MVP. L'extension cross-thread (mémoire long-terme transverse) est explicitement hors-scope.
- En cas d'échec embedding sur un message, le re-essai automatique en arrière-plan est hors-scope MVP — un re-traitement manuel ou batch viendra plus tard.
