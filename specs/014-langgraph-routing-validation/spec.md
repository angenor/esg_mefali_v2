# Feature Specification: LangGraph Routing & Pydantic Validation Pipeline (F14)

**Feature Branch**: `014-langgraph-routing-validation`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F14 — LangGraph Routing & Validation Pydantic + Retry. Pipeline classifier d'intention → sélecteur de tools (5–10 max) → LLM principal → validateur Pydantic → retry max 2 → réponse, pour rendre le tool-use fiable face aux 30+ tools de la plateforme."

## Clarifications

### Session 2026-04-29

- Q: Cache d'intention par fil — portée et durée ? → A: Mémoire process (LRU), clé `thread_id`, TTL 10 minutes glissant (pas de Redis en MVP).
- Q: Voie LLM légère du classifier — quel modèle ? → A: Réutiliser le LLM principal (modèle configuré par variable d'environnement) avec un prompt court spécialisé "classification" ; pas de second fournisseur en MVP.
- Q: Rétention du journal `tool_call_log` ? → A: 12 mois append-only en chaud, puis archivage froid ; conforme à la convention audit-log-versioning de F04.
- Q: Concurrence du pipeline par utilisateur ? → A: 1 pipeline simultané maximum par `thread_id` (verrou logiciel) ; les requêtes concurrentes sur un même fil sont sérialisées.
- Q: Comportement si la whitelist d'une Skill active vide la sélection ? → A: Servir le set par défaut minimal `{ask_qcu, ask_yes_no}` et journaliser un avertissement ; la conversation n'est jamais bloquée.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Pipeline d'orchestration tool-use bout-en-bout (Priority: P1)

En tant qu'utilisatrice PME en conversation avec l'assistant, je tape un message ("ajoute un projet d'agroforesterie de 50 millions FCFA"). Le système doit (1) classifier mon intention, (2) sélectionner un sous-ensemble pertinent de tools (5 à 10 max), (3) invoquer le LLM principal avec un system prompt cadré, (4) valider la réponse contre un schéma strict avant de l'exécuter, (5) renvoyer une réponse cohérente. Si le LLM produit un payload invalide, le système retente automatiquement (max 2) avec un message d'erreur structuré, sinon bascule sur une réponse texte de fallback claire.

**Why this priority** : C'est le cœur de la feature ; sans ce pipeline complet, aucun tool n'est fiable. Tous les autres récits dépendent de l'existence de ce moteur.

**Independent Test** : Pipeline testable bout-en-bout avec 5 tools fictifs : 10 cas d'entrée déclenchent classifier + sélecteur + (LLM mocké) + validateur, et le résultat correspond aux attentes (tool sélectionné, payload validé, réponse générée). Un cas avec payload invalide vérifie que le retry tourne bien et que le fallback texte est servi en cas d'échec persistant.

**Acceptance Scenarios** :

1. **Given** un message PME "ajoute un projet d'agroforesterie 50 MFCFA" en page Profil/Projets, **When** le pipeline traite le message, **Then** l'intention `mutation` est détectée, ≤10 tools incluant un tool de mutation projet sont fournis au LLM, le payload retourné est validé, et la réponse exécutable atteint le frontend en moins de 1 seconde de surcoût pipeline (hors temps LLM).
2. **Given** un message ambigu "modifier mon projet", **When** le classifier hésite, **Then** un set de tools "ask_*" (questions fermées) est sélectionné pour permettre au LLM de poser une clarification.
3. **Given** un payload LLM invalide (champ enum hors valeurs autorisées), **When** la validation échoue, **Then** une erreur structurée est renvoyée au LLM avec champ/reçu/attendu, le LLM retente, et après deux échecs un fallback texte est servi avec un incident loggé.

---

### User Story 2 — Classifier d'intention robuste (Priority: P1)

En tant que développeuse backend, je veux que chaque message utilisateur soit classé en une catégorie d'intention parmi {profilage, mutation, analyse, navigation, question_fermee, aide, autre}, avec règles déterministes en première ligne et fallback LLM léger pour les cas ambigus, et un cache par fil de discussion pour éviter les reclassifications systématiques.

**Why this priority** : Le sélecteur de tools dépend de l'intention. Sans intention fiable, le sous-ensemble de tools est arbitraire et le LLM dégrade.

**Independent Test** : 30 messages d'exemple (5 par intention + 5 ambigus) sont passés au classifier ; ≥90% atteignent l'intention attendue, et les ambigus retombent sur la voie LLM ou par défaut documentée.

**Acceptance Scenarios** :

1. **Given** un message "supprime ce projet", **When** le classifier l'analyse, **Then** l'intention `mutation` est retournée par les règles sans appel LLM.
2. **Given** un message complexe "compare ma performance ESG aux pairs et explique pourquoi je perds des points", **When** les règles ne tranchent pas, **Then** le fallback LLM léger est invoqué et l'intention `analyse` ressort.
3. **Given** deux messages successifs sur le même fil avec le même thème, **When** le second arrive, **Then** le cache de la dernière intention par fil évite un nouvel appel LLM si la similarité contextuelle est élevée.
4. **Given** le LLM léger indisponible (timeout, erreur), **When** la classification est requise, **Then** la décision retombe sur un défaut documenté (`autre`) et le pipeline continue sans bloquer.

---

### User Story 3 — Sélecteur de tools borné à 5–10 (Priority: P1)

En tant que développeuse, je veux qu'à chaque tour de conversation, un sous-ensemble de **5 à 10 tools maximum** soit transmis au LLM, dérivé de l'intention courante, de la page active (contexte), des entités sélectionnées, et des skills actives, via un système de règles déclaratif lisible.

**Why this priority** : Au-delà de 10 tools, la précision de sélection du LLM s'effondre. C'est l'invariant de fiabilité.

**Independent Test** : 10 paires (intention, contexte) → vérifier que le set retourné contient les tools attendus, ne dépasse jamais 10, et n'est jamais vide (un set par défaut minimal est servi).

**Acceptance Scenarios** :

1. **Given** intention `mutation` + page `Profil → Entreprise`, **When** le sélecteur calcule, **Then** au plus 10 tools sont renvoyés, dont les tools de mutation profil et les tools de question fermée.
2. **Given** intention `aide` sans contexte page, **When** le sélecteur calcule, **Then** un set minimal {ask_qcu, ask_yes_no} est renvoyé.
3. **Given** une skill active déclarant un `tool_whitelist`, **When** le sélecteur s'exécute, **Then** seuls les tools dans la whitelist sont retenus, dans la limite de 10.

---

### User Story 4 — Tools auto-descriptifs avec schéma strict (Priority: P1)

En tant que développeuse, je veux pouvoir déclarer un tool une seule fois avec un nom verbal sans ambiguïté, une description "use when / don't use when", des exemples positifs et négatifs, et un schéma de payload **strict** (interdiction de champs inattendus). Tout le reste du pipeline (sélecteur, system prompt, validateur) consomme ces métadonnées sans duplication.

**Why this priority** : Sans convention unique, les descriptions divergent du schéma et le LLM hallucine. La déclaration unique élimine cette dérive.

**Independent Test** : Déclarer 5 tools fictifs avec la convention ; vérifier qu'ils s'inscrivent automatiquement dans un registre interne, que leur description est récupérable pour le system prompt, et que leur schéma rejette les champs additionnels.

**Acceptance Scenarios** :

1. **Given** un tool déclaré avec un schéma strict, **When** un payload contient un champ non déclaré, **Then** la validation échoue avec un message explicite mentionnant le champ inattendu.
2. **Given** un tool déclaré, **When** le system prompt est construit, **Then** son nom, sa description, ses règles d'usage et un exemple positif sont inclus.

---

### User Story 5 — System prompt construit dynamiquement (Priority: P1)

En tant que développeuse, je veux que le system prompt envoyé au LLM principal soit assemblé à chaque tour à partir de briques cohérentes : invariants de la plateforme (sourçage, multi-tenant, langue FR, ton), arbre de décision tools, anti-exemples, descriptions des tools sélectionnés, contexte de la page courante.

**Why this priority** : Empêche la dérive entre tools déclarés et prompt. Conditionne la précision du choix de tool.

**Independent Test** : À partir d'un set de tools sélectionnés et d'un contexte, le builder retourne un prompt déterministe contenant les briques attendues et restant sous le plafond de tokens ; au-delà du plafond, une alarme est levée et la troncature est appliquée selon une règle documentée.

**Acceptance Scenarios** :

1. **Given** un set de 8 tools et un contexte page `Candidatures`, **When** le builder s'exécute, **Then** le prompt contient les invariants, l'arbre de décision, les 8 descriptions, et les anti-exemples, dans un budget tokens documenté.
2. **Given** un set de tools dont la concaténation des descriptions excède le plafond (≈4 000 tokens), **When** le builder s'exécute, **Then** une alarme est journalisée et les sections les moins prioritaires sont tronquées sans casser le sens.

---

### User Story 6 — Validation Pydantic systématique avec erreur structurée (Priority: P1)

En tant que développeuse, je veux que tout payload produit par le LLM pour invoquer un tool soit validé contre le schéma déclaré du tool **avant** toute exécution ou rendu, et que toute erreur de validation soit traduite en un objet structuré (champ fautif, valeur reçue, contrainte attendue) à la fois loggable et exploitable par la boucle de retry.

**Why this priority** : Empêche tout effet de bord dû à un payload halluciné. Sans cela, la mutation se produit sur des données incorrectes.

**Independent Test** : 5 payloads volontairement malformés (champ manquant, type incorrect, enum hors liste, valeur hors borne, champ supplémentaire interdit) sont validés ; tous sont rejetés avec une erreur structurée lisible (champ, reçu, attendu).

**Acceptance Scenarios** :

1. **Given** un payload avec une valeur d'enum incorrecte, **When** la validation s'exécute, **Then** une erreur structurée mentionne le champ, la valeur reçue et la liste des valeurs acceptées.
2. **Given** un payload contenant un champ non déclaré, **When** la validation s'exécute, **Then** une erreur de type "champ inattendu" est renvoyée et le tool n'est jamais exécuté.

---

### User Story 7 — Retry borné avec fallback texte (Priority: P1)

En tant que développeuse, je veux qu'en cas d'échec de validation, l'erreur structurée soit ré-injectée au LLM en lui demandant de corriger, jusqu'à **2 retries**. Si toutes les tentatives échouent, l'utilisateur reçoit une réponse texte de repli ("je n'arrive pas à formaliser cette action — peux-tu reformuler ?") et un incident est journalisé pour analyse.

**Why this priority** : Sans retry, un payload légèrement faux échoue ; avec un retry illimité, le coût explose. Le compromis (max 2) est un invariant de coût.

**Independent Test** : Avec un LLM mocké qui retourne 2 payloads invalides puis un valide, vérifier que le tool est exécuté au troisième essai. Avec un LLM mocké qui n'arrive jamais à corriger, vérifier que le fallback texte est servi et qu'un incident est journalisé.

**Acceptance Scenarios** :

1. **Given** une première sortie LLM invalide, **When** le retry s'enclenche, **Then** un message d'erreur structuré est renvoyé au LLM et un nouvel essai est tenté avec un contexte minimal (économie de tokens).
2. **Given** trois sorties LLM invalides consécutives, **When** la limite est atteinte, **Then** le pipeline retourne un message texte de repli, journalise un incident, et n'exécute aucun tool.

---

### User Story 8 — Streaming des étapes du pipeline (Priority: P2)

En tant qu'utilisatrice, je veux voir mon assistant "réfléchir" en direct : indication d'analyse, démarrage d'un appel d'outil, complétion, puis le texte qui s'écoule, puis la fin du message. Cela évite l'effet "boîte noire" pendant les 5–15 secondes de génération.

**Why this priority** : L'expérience F13 est déjà streamée ; F14 doit s'inscrire dans cette continuité sans casser le contrat.

**Independent Test** : Un message "complexe" déclenche au moins quatre événements distincts côté client (réflexion, outil démarré, outil complété, texte/fin de message), dans l'ordre, sans perte.

**Acceptance Scenarios** :

1. **Given** un message déclenchant un appel d'outil, **When** le pipeline s'exécute, **Then** le frontend reçoit successivement des événements `thinking`, `tool_call_started`, `tool_call_completed`, `text_delta` (un ou plusieurs), `message_done`.
2. **Given** une erreur en cours de pipeline, **When** elle survient, **Then** un événement d'erreur structuré est émis avant `message_done` pour que l'UI puisse afficher un état dégradé.

---

### User Story 9 — Journal exhaustif des appels de tool (Priority: P2)

En tant qu'admin plateforme, je veux que chaque appel de tool soit journalisé (compte, utilisateur, fil, nom du tool, arguments, résultat, statut, latence, retries, modèle, tokens prompt/complétion, timestamp), de manière append-only et isolée par compte (multi-tenant), pour pouvoir analyser a posteriori, ajuster les descriptions, et nourrir l'évaluation continue (F35).

**Why this priority** : Sans journal, aucune amélioration mesurable. Cohérence avec les invariants Module 0 (audit append-only, multi-tenant).

**Independent Test** : Un test d'intégration qui exécute 10 appels (succès, validation_error, handler_error, timeout) vérifie que chacun produit exactement une ligne de journal avec le statut adéquat, et qu'un compte ne voit jamais les lignes d'un autre compte.

**Acceptance Scenarios** :

1. **Given** un appel de tool réussi, **When** il se termine, **Then** une ligne est insérée avec statut `ok`, durée mesurée, et tokens consommés.
2. **Given** un appel échouant en validation après deux retries, **When** le pipeline se termine, **Then** une ligne `validation_error` est journalisée avec le compteur de retries.
3. **Given** une session admin du compte A, **When** elle requête le journal, **Then** seules les lignes du compte A sont visibles (isolation multi-tenant).

---

### Edge Cases

- **Classifier LLM injoignable** : timeout / erreur réseau → repli sur règles déterministes ; intention par défaut `autre` ; pipeline poursuit avec un set de tools minimal.
- **Sélecteur retournant 0 tool** : un set par défaut minimal documenté est servi pour ne jamais bloquer la conversation.
- **System prompt dépassant le budget tokens** : alarme journalisée + troncature documentée des sections les moins prioritaires.
- **Boucle infinie potentielle de retry** : compteur strict ≤ 2, garanti par un invariant testé.
- **Tools concurrents > 10** : refusé par construction du sélecteur (limite hard) — un test couvre la tentative.
- **Skill active désactivant tous les tools utiles** : le set par défaut minimal reprend la main pour servir au moins une réponse texte.
- **Coût retry non comptabilisé pour l'utilisateur** : les tokens des retries sont enregistrés séparément, pas imputés au quota PME.
- **Drift entre description de tool et schéma** : la déclaration unique du tool empêche structurellement l'écart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT exposer un point d'entrée unique d'orchestration qui accepte un message utilisateur, un contexte de page, et l'historique du fil, et produit une réponse traçable (texte ou exécution de tool validée).
- **FR-002** : Le système DOIT permettre la déclaration de tools selon une convention unique incluant nom, description, règles "use when / don't use when", exemples positifs et négatifs, schéma strict de payload, et fonction de traitement asynchrone.
- **FR-003** : Le système DOIT classifier l'intention du message utilisateur en une catégorie parmi {profilage, mutation, analyse, navigation, question_fermee, aide, autre}, via règles d'abord, puis voie LLM légère en fallback, avec mise en cache de l'intention par fil.
- **FR-004** : Le système DOIT sélectionner un sous-ensemble de tools borné à **5–10 maximum** à partir de l'intention, du contexte de page, des entités actives et des skills actives, via des règles déclaratives lisibles, et garantir un set par défaut minimal si aucune règle ne s'applique.
- **FR-005** : Le système DOIT construire dynamiquement un system prompt incluant invariants plateforme, arbre de décision tools, anti-exemples, descriptions des tools sélectionnés, et contexte de page, en restant sous un plafond de tokens documenté ; en cas de dépassement, alarme + troncature contrôlée.
- **FR-006** : Le système DOIT valider tout payload proposé par le LLM contre le schéma strict du tool ciblé avant toute exécution, en interdisant les champs inattendus.
- **FR-007** : En cas d'échec de validation, le système DOIT renvoyer au LLM une erreur structurée (champ fautif, valeur reçue, contrainte attendue) et tenter au plus **2 retries**, puis basculer sur une réponse texte de repli et journaliser un incident.
- **FR-008** : Le système DOIT journaliser chaque appel de tool dans un journal append-only contenant compte, utilisateur, fil, nom du tool, arguments, résultat, statut parmi {ok, validation_error, handler_error, timeout}, latence, nombre de retries, modèle utilisé, tokens prompt/complétion, et horodatage. L'isolation multi-tenant par compte DOIT être garantie au niveau stockage.
- **FR-009** : Le pipeline DOIT être capable d'émettre des événements de progression (analyse en cours, début d'appel d'outil, fin d'appel d'outil, fragments de texte, fin de message, erreur) compatibles avec le streaming existant du chat.
- **FR-010** : Le système DOIT exposer un point d'extension permettant à une skill active (livrée plus tard en F19) de restreindre la liste des tools sélectionnables (whitelist).
- **FR-011** : Les tokens consommés par les retries DOIVENT être journalisés séparément et NE PAS être imputés au quota d'usage de l'utilisatrice PME.
- **FR-012** : En cas d'indisponibilité de la voie LLM légère du classifier, le système DOIT retomber sur la voie règles et continuer sans bloquer la conversation.
- **FR-013** : Le cache d'intention par fil DOIT être stocké en mémoire processus (LRU), clé = identifiant du fil, avec un TTL glissant de 10 minutes ; aucun stockage externe (Redis ou autre) n'est requis en MVP.
- **FR-014** : La voie LLM légère du classifier DOIT réutiliser le même fournisseur et le même modèle que le LLM principal (configuré par variable d'environnement), avec un prompt court spécialisé classification ; aucun second fournisseur n'est introduit en MVP.
- **FR-015** : Le journal des appels d'outil DOIT être conservé append-only pendant au moins 12 mois en stockage chaud, puis archivé en stockage froid ; aucune mutation après insertion, conforme à la convention F04 (audit-log-versioning).
- **FR-016** : Le système DOIT garantir au plus **un** pipeline en cours d'exécution par identifiant de fil ; les requêtes concurrentes sur le même fil DOIVENT être sérialisées (verrou logiciel) afin d'éviter les conditions de course sur le cache d'intention et le contexte conversationnel.
- **FR-017** : Si l'application de la whitelist d'une Skill active rend l'ensemble de tools sélectionnés vide, le système DOIT servir le set par défaut minimal `{ask_qcu, ask_yes_no}` et journaliser un avertissement ; la conversation ne DOIT jamais être bloquée.

### Key Entities *(include if feature involves data)*

- **ToolCallLog** : enregistrement append-only d'un appel d'outil. Attributs : compte, utilisateur, fil, nom du tool, arguments fournis, résultat produit, statut, latence, retries, modèle, tokens (prompt/complétion), horodatage. Isolé par compte (RLS).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur un jeu de 10 cas test couvrant les 7 intentions et 5 tools fictifs, le pipeline (classifier + sélecteur + validateur, LLM mocké) atteint le résultat attendu dans **≥ 90 %** des cas.
- **SC-002** : 5 payloads volontairement malformés sont **rejetés à 100 %** avec une erreur structurée lisible identifiant le champ fautif et la contrainte violée.
- **SC-003** : Lorsqu'un payload invalide est suivi d'un payload valide simulé en retry, le pipeline exécute le tool **au plus tard au 3ᵉ appel LLM** ; lorsqu'aucune correction n'arrive, un fallback texte est servi et un incident est journalisé.
- **SC-004** : Pour un message déclenchant un appel d'outil, le frontend reçoit **au moins 4 événements de progression** dans l'ordre attendu (analyse, début outil, fin outil, fin de message) sans perte.
- **SC-005** : **100 %** des appels de tool produisent une ligne de journal cohérente avec leur statut réel (vérifié par test d'intégration), avec isolation multi-tenant testée.
- **SC-006** : Le surcoût de latence du pipeline (hors temps de génération du LLM principal) reste **inférieur à 1 seconde au 95ᵉ percentile** sur un jeu de mesures d'au moins 50 exécutions.
- **SC-007** : Le system prompt total reste **inférieur à 4 000 tokens** dans 100 % des cas où ≤10 tools sont sélectionnés ; au-delà, l'alarme et la troncature sont déclenchées et observables.
- **SC-008** : La couverture de tests automatisés sur les modules nouveaux du pipeline atteint **≥ 80 %**.
- **SC-009** : Pour deux requêtes concurrentes sur un même fil, **100 %** des cas testés voient le second pipeline démarrer après la complétion du premier (sérialisation observable par horodatage).
- **SC-010** : Lorsqu'un fil reçoit deux messages successifs sur le même thème dans un intervalle ≤ 10 minutes, **0 appel** supplémentaire de classification LLM est observé (cache TTL respecté).

## Assumptions

- F13 (chat-interface-base) est mergée et fournit déjà : tables de fils et messages, point d'entrée chat REST + streaming SSE, bus d'événements applicatif. F14 se branche derrière l'endpoint chat existant.
- Les invariants Module 0 (multi-tenant isolé par compte, audit append-only, sourçage obligatoire des affirmations factuelles, langue FR par défaut, plateforme PME/Admin) s'appliquent et conditionnent les choix.
- Le modèle LLM principal est unique et configurable ; le routage multi-modèle est explicitement hors scope MVP.
- Les tools concrets (réponse, visualisation, mutation) sont livrés dans les features suivantes (F15, F16, F17). F14 livre **uniquement** le moteur, la convention de déclaration et 5 tools fictifs servant d'harnais de test.
- Les Skills (F19) ne sont pas encore implémentées ; F14 prévoit le point d'extension (whitelist) mais n'en livre pas le moteur.
- Les voies LLM (principal et léger pour le classifier) sont accessibles via un service externe configuré et le pipeline doit gérer les indisponibilités.
- L'utilisatrice cible est une PME francophone Afrique de l'Ouest ; les latences réseau sont prises en compte dans les seuils.

## Dependencies

- **F13 — chat-interface-base** : tables de conversation, endpoint chat, streaming SSE, bus d'événements (mergée).
- **F02 — auth-roles-rls** : isolation multi-tenant par compte (déjà en place).
- **F04 — audit-log-versioning** : convention d'append-only et de traçabilité (déjà en place).

## Out of Scope (MVP)

- Routage multi-modèle (par exemple un modèle léger pour le classifier + un modèle plus puissant pour l'analyse) — un seul modèle configuré pour le MVP.
- Cache sémantique des résultats de tools.
- Apprentissage en ligne sur corrections utilisateurs.
- Plus de 10 tools concurrents par tour (limite hard volontaire).
- Livraison des tools concrets et des skills (F15+).
