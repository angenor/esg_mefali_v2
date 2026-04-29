# F11 — Profil → Entreprise (édition manuelle synchronisée LLM)

**Phase** : 2 — Profil PME
**Modules brainstorm** : 1.2 (Profilage Intelligent de l'Entreprise) — partie UI/édition
**Dépendances** : F02, F04
**Estimation** : 1.5–2 jours

## Contexte et objectif

L'entité **Entreprise** est le **contexte porteur** : qui est la PME, son secteur, sa taille, sa gouvernance, ses pratiques actuelles. 1 par compte. Elle alimente le scoring crédit (F29) et la conformité ESG globale (F23).

Cette feature livre la **vue Profil → Entreprise** où la PME peut **consulter et éditer manuellement** tous les champs, indépendamment du LLM. Le LLM enrichira via la Phase 3 (chat + tools de mutation), mais l'utilisateur doit pouvoir corriger, compléter ou écraser ce que le LLM a extrait. Synchronisation bidirectionnelle obligatoire.

## User Stories

### US1 — Voir le profil de mon entreprise (P1)
**En tant que** PME,
**je veux** une page `/profil/entreprise` qui affiche tous les champs de mon entreprise organisés par section (Identité, Activité, Localisation, Pratiques, Gouvernance),
**afin de** comprendre quelles données sont stockées sur mon compte.

**Test indépendant** : un compte fraîchement inscrit voit un formulaire vierge avec les sections définies. Un compte existant voit ses données déjà saisies.

### US2 — Éditer manuellement chaque champ (P1)
**En tant que** PME,
**je veux** modifier directement chaque champ depuis l'UI (édition inline ou modale), avec validation côté client (formats, bornes),
**afin de** corriger des erreurs ou compléter ce que le LLM a extrait.

**Scénarios** :
1. Champ "Effectifs" : input numérique 0–10 000.
2. Champ "Secteur" : autocomplete sur taxonomie sectorielle (NAF/CITI ou liste maison sourcée).
3. Champ "Localisation siège" : sélecteur pays UEMOA/CEDEAO + ville libre.
4. Champ "Pratiques environnementales actuelles" : textarea libre + tags suggérés.
5. Toute édition manuelle → audit log avec `source_of_change='manual'`.

### US3 — Synchronisation bidirectionnelle avec le LLM (P1)
**En tant que** PME,
**je veux** qu'une édition manuelle soit immédiatement reflétée dans le contexte LLM (à mon prochain message, le LLM voit la nouvelle valeur),
**afin de** ne pas avoir à répéter au LLM ce que j'ai déjà corrigé.

**Et réciproquement** : quand le LLM met à jour un champ via `update_company_profile` (F17), la page se met à jour en temps réel (websocket ou polling) si la PME est dessus.

**Scénarios** :
1. PME édite "Effectifs" de 50 → 75 manuellement, puis pose une question au LLM → le LLM répond avec 75 dans son contexte.
2. PME ouvre `/profil/entreprise`, ouvre le chat flottant (F13), demande au LLM "mets mon CA à 250M FCFA" → l'UI de la page se met à jour sans reload.

### US4 — Indicateur visuel de provenance (P2)
**En tant que** PME,
**je veux** voir à côté de chaque champ d'où vient sa valeur (saisie manuelle, extrait par le LLM d'un document, déclaratif initial),
**afin de** savoir où le LLM a "deviné" et où j'ai validé.

**Scénarios** :
1. Champ "Secteur" extrait du statut juridique → badge "Extrait du document statuts.pdf le 12/03".
2. Champ édité manuellement → badge "Modifié manuellement le 14/03".
3. Cliquer sur le badge ouvre un mini-historique du champ (audit log filtré).

### US5 — Champs obligatoires vs optionnels et complétude (P2)
**En tant que** PME,
**je veux** voir un % de complétude de mon profil et savoir quels champs sont nécessaires pour débloquer telle ou telle feature (ex : F23 Scoring ESG nécessite Secteur + Effectifs + CA),
**afin de** prioriser ma saisie.

### US6 — Édition multi-utilisateurs sans conflit (P3)
**En tant que** collaborateur d'une PME (Module 7.3 : tous les users PME ont les mêmes droits),
**je veux** que si 2 collègues éditent en même temps, on ne se marche pas dessus,
**afin de** travailler sereinement.

**Mécanisme MVP simple** : optimistic concurrency via `version` (rejeter avec 409 si version stale, l'utilisateur recharge).

## Exigences fonctionnelles

- **FR-001** : Table `entreprise` (déjà créée en F01) enrichie : `id, account_id (UNIQUE), name, secteur_code, secteur_label, taille_ca_money, taille_effectifs INT, localisation_siege_pays_iso2, localisation_siege_ville, zones_operation_pays_iso2[], gouvernance_json (forme juridique, nb actionnaires, présence comité audit, etc.), pratiques_actuelles_json, version, created_at, updated_at`.
- **FR-002** : Champs avec **provenance** : ajouter à chaque champ un méta `(value, source_of_change, last_modified_at, last_modified_by)`. Implémenté via une table `entreprise_field_meta` ou via `audit_log` agrégé. Recommandation : utiliser audit_log pour la trace, et un calcul "dernier source_of_change" exposé dans l'API.
- **FR-003** : Endpoints REST :
  - `GET /me/entreprise` (lecture du profil, avec metadata par champ).
  - `PUT /me/entreprise` (édition complète avec If-Match/version).
  - `PATCH /me/entreprise` (édition partielle d'un ou plusieurs champs).
  - Audit log à chaque mutation (F04).
- **FR-004** : Validation Pydantic stricte côté backend : enum sectors (taxonomie maison ou NAF/CITI), pays ISO2, money typé (F05), bornes numériques.
- **FR-005** : Page Vue `/profil/entreprise` :
  - Layout "form-builder" en sections,
  - Édition inline ou modale par champ,
  - Indicateur de complétude global,
  - Badge de provenance par champ (F11 US4).
- **FR-006** : WebSocket ou Server-Sent Events pour la synchro temps réel (US3) — un canal `account.{id}.entreprise.updated` côté serveur, abonnement côté front quand la page est ouverte. (Alternative MVP simple : polling toutes les 5s — à clarifier.)
- **FR-007** : Endpoint `GET /me/entreprise/completeness` → `{percentage, missing_required_for_features:["esg_scoring", "credit_scoring"]}` (US5).
- **FR-008** : Mécanisme de version optimiste (`version` int, header `If-Match`) — 409 sur conflit.

## Exigences non-fonctionnelles

- **NFR-001** : Édition d'un champ → persistance + sync LLM en < 500ms p95.
- **NFR-002** : Le formulaire complet (toutes sections déployées) charge en < 1s.
- **NFR-003** : Validation côté front identique à celle backend (même schéma, ex: zod côté Nuxt + Pydantic côté FastAPI ; ou autogénération d'un schéma front depuis OpenAPI).
- **NFR-004** : Aucun champ sensible (effectifs, CA) n'est exposé dans des logs ou messages d'erreur en clair.

## Entités clés

- **Entreprise** (FR-001) — enrichie.
- Pas de nouvelle table dédiée à la provenance — utilise `audit_log`.

## Success Criteria

- **SC-001** : Une PME complète son profil entreprise (10 champs principaux) en < 5 minutes.
- **SC-002** : Édition manuelle d'un champ → audit log + invalidation cache LLM (vérifié par test d'intégration : prochain message LLM contient la nouvelle valeur).
- **SC-003** : Sync temps réel : édition LLM → UI mise à jour en < 1s.
- **SC-004** : Les badges de provenance sont corrects sur 5 cas tests (manuel, LLM, document extracté).

## Hors-scope MVP

- OCR-driven prefill auto-créé en F22 (cette feature ne fait que afficher/éditer ; la saisie depuis documents vient de F22).
- Workflow d'approbation interne intra-PME (différents user roles, post-MVP F32).
- Versioning fin par champ (on a la version au niveau entreprise, suffisant).
- Multi-entreprises par compte (1:1 strict en MVP).

## Risques et points de vigilance

- **Synchro LLM** : invalider le cache du contexte conversationnel à chaque édition manuelle pour ne pas servir une valeur stale au LLM. Pattern : pas de cache du profil entreprise côté LLM, on relit en début de chaque tour (F18).
- **Complétude** : les "champs requis pour feature X" doivent être déclaratifs dans une config, pas en dur — pour qu'évoluer F23/F29 ne casse pas F11.
- **Conflit multi-users** : optimistic concurrency simple suffit en MVP (peu probable que 2 PME users édient en même temps). Pas de CRDT.
- **Taxonomie sectorielle** : hésiter entre NAF (FR), CITI (ONU), liste maison adaptée afrique. Recommandation : liste maison ~50 secteurs validée par admins, sourcée — alimentée comme un référentiel via F09.
