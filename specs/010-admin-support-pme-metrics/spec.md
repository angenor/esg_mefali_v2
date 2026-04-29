# Feature Specification: Support PME Admin & Métriques Admin

**Feature Branch**: `010-admin-support-pme-metrics`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F10 — Support PME Admin & Métriques Admin (Phase 1, Modules 9.3 & 9.4). Dépendances : F02 (auth+RLS), F04 (audit+versioning), F06 (back-office)."

## Overview

Permettre à l'équipe ESG Mefali (rôle admin) d'**aider une PME en difficulté** (réinitialiser un mot de passe, débloquer un compte, révoquer/régénérer une attestation compromise) tout en préservant la confidentialité : chaque consultation d'un compte PME est elle-même journalisée et visible par la PME. Fournir en parallèle un **tableau de bord agrégé** sur l'état du catalogue, des PME, de l'activité et des coûts LLM.

Pas de surveillance abusive : un admin qui consulte un compte PME laisse une trace dans l'audit log de la PME, qui peut elle-même voir cette trace dans son historique. C'est une garantie de confiance et de conformité.

## Clarifications

### Session 2026-04-29

- Q: Provider d'email transactionnel pour reset password et notifications ? → A: Resend (abstraction `EmailSender` pour swap futur, free tier dev, simple)
- Q: Granularité des sections d'audit `admin_view` ? → A: Liste fermée 7 sections : `dashboard | projets | candidatures | scores | attestations | llm | audit`
- Q: Politique de notification PME post-révocation d'attestation ? → A: In-app + email en MVP (transparence forte, réutilise Resend)
- Q: Stratégie de cache pour `/admin/dashboard/stats` ? → A: Cache mémoire in-process backend, TTL 60s, invalidation explicite sur révocation d'attestation (pas de Redis en MVP)
- Q: Politique de retry pour les envois d'email transactionnel ? → A: 3 tentatives avec backoff exponentiel (1m / 5m / 15m), via `BackgroundTasks` FastAPI ; au-delà, statut `failed` visible dans `EmailDeliveryLog`

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vue lecture seule des comptes PME (Priority: P1)

En tant qu'admin support, j'ouvre une page admin qui liste les comptes PME avec recherche par email/nom d'entreprise, et je clique pour voir un compte en lecture seule, afin de diagnostiquer un problème reporté par une PME.

**Why this priority**: Cas d'usage support n°1. Sans cette vue, l'admin ne peut rien diagnostiquer et la plateforme dépend du seul self-service PME.

**Independent Test**: La page `/admin/pme` liste les comptes paginés ; un clic ouvre `/admin/pme/{account_id}` qui affiche entreprise, projets, candidatures, scores, attestations, conversations LLM, audit log — toujours en lecture seule (aucun bouton d'édition).

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il navigue sur `/admin/pme` et tape "acme" dans la recherche, **Then** la liste se filtre sur les comptes dont l'email ou la raison sociale contient "acme".
2. **Given** un admin sur la liste, **When** il clique sur un compte, **Then** il voit `/admin/pme/{account_id}` avec toutes les sections (entreprise, projets, candidatures, scores, attestations, conversations LLM, audit log) sans aucun bouton d'édition.
3. **Given** un admin sur la fiche d'un compte avec 10 projets, 50 candidatures et 1000 messages LLM, **When** la page se charge, **Then** elle est interactive en moins de 2 secondes (pagination/lazy load des sections volumineuses autorisées).

---

### User Story 2 — Chaque consultation admin est tracée (Priority: P1)

En tant que PME, je veux voir dans mon historique d'actions une ligne lorsqu'un admin consulte mes données, avec qui et quand, afin de garantir la transparence.

**Why this priority**: Garantie de confiance plateforme + conformité données personnelles. Sans cela, la lecture admin devient surveillance opaque.

**Independent Test**: Dès qu'un admin ouvre `/admin/pme/{id}` ou une de ses sous-sections, une ligne d'audit `entity_type='admin_view'` apparaît dans l'historique de la PME, visible côté PME, exposant uniquement l'email de l'admin, la section consultée et l'horodatage (pas l'IP ni d'autre PII admin).

**Acceptance Scenarios**:

1. **Given** un admin qui ouvre `/admin/pme/{id}`, **When** la requête aboutit, **Then** une ligne `audit_log` est insérée pour ce compte PME avec `entity_type='admin_view'`, `entity_id=account_id`, `source_of_change='admin'`, `actor_email=<email_admin>`, `section='dashboard'`, et un horodatage.
2. **Given** un admin qui consulte la sous-section "projets" du compte, **When** la requête aboutit, **Then** la ligne d'audit porte `section='projets'` (granularité par section, pas intra-section).
3. **Given** une PME consultant son historique d'actions, **When** elle filtre sur `admin_view`, **Then** elle voit toutes les consultations admin avec email admin + date + section, sans IP, sans User-Agent, sans détail intra-section.
4. **Given** la table d'audit, **When** une ligne `admin_view` est créée, **Then** elle respecte l'append-only (pas de suppression possible, helpers `record_audit` réutilisés depuis F04).

---

### User Story 3 — Réinitialisation de mot de passe (Priority: P1)

En tant qu'admin support, je veux déclencher l'envoi d'un email de réinitialisation à un user PME bloqué, afin de débloquer un compte sans avoir accès au mot de passe.

**Why this priority**: Cas de support le plus fréquent. SC-001 cible < 2 min de résolution.

**Independent Test**: L'admin clique "Reset password" sur un user → un email avec lien token unique 1h est envoyé à l'utilisateur ; deux lignes d'audit (côté admin et côté PME) sont créées ; aucun token n'est exposé à l'admin.

**Acceptance Scenarios**:

1. **Given** un admin sur la fiche d'un user PME, **When** il clique "Reset password" et confirme, **Then** un email de réinitialisation est envoyé avec un lien à durée de vie 1h, et l'admin reçoit une confirmation "email envoyé" sans aucun token visible.
2. **Given** la même action, **When** elle est exécutée, **Then** deux lignes d'audit sont créées : une côté admin (`actor=admin, action=reset_password_request, target_user_id=...`) et une côté PME (`source_of_change='admin', entity_type='user', action='reset_password_request'`).
3. **Given** un échec d'envoi d'email (provider indisponible), **When** le système retente selon la politique de retry, **Then** les échecs sont consignés dans un journal admin dédié (visible depuis le dashboard) et l'admin voit un statut "Échec, retry en cours".
4. **Given** l'utilisateur final, **When** il clique sur le lien après expiration (≥ 1h), **Then** le système refuse et affiche un message "lien expiré, demandez un nouveau reset".

---

### User Story 4 — Régénération / révocation d'attestations (Priority: P1)

En tant qu'admin support, je veux révoquer une attestation publique en cas d'incident (donnée compromise, score frauduleux, demande PME), avec motif obligatoire, afin de mettre à jour la page publique de vérification (F30).

**Why this priority**: Garde-fou de la valeur publique des attestations ; nécessaire pour répondre à un incident sans déployer de correctif code.

**Independent Test**: Un admin révoque une attestation X avec motif → l'attestation passe à `revoked` ; la page publique `/verify/{id}` affiche immédiatement "Attestation révoquée le YYYY-MM-DD" avec le motif (filtré PII) ; la PME est notifiée.

**Acceptance Scenarios**:

1. **Given** un admin sur la fiche d'une attestation, **When** il clique "Révoquer" et saisit un motif (champ obligatoire, longueur min 10 caractères), **Then** l'attestation reçoit `revoked_at=now()`, `revoked_by=<admin_id>`, `revoked_reason=<texte>`, et une ligne d'audit est créée.
2. **Given** une attestation révoquée, **When** un visiteur consulte `/verify/{id}`, **Then** la page indique "Attestation révoquée le YYYY-MM-DD" et le motif filtré (sans PII) ; la propagation est immédiate (pas de cache > 60s).
3. **Given** un admin qui clique "Régénérer", **When** la PME n'a pas donné de consentement préalable, **Then** la régénération est mise en attente jusqu'à acceptation explicite par la PME (consentement consigné dans l'audit) OU bloquée si la fonction de consentement n'est pas activée.
4. **Given** une révocation effectuée, **When** elle aboutit, **Then** la PME reçoit une notification **in-app + email** (Resend) et la voit dans son dashboard.

---

### User Story 5 — Tableau de bord admin agrégé (Priority: P2)

En tant qu'équipe ESG Mefali, je veux une page `/admin/dashboard` qui agrège l'état des sources, du catalogue, des PME, de l'activité et des messages LLM, afin de piloter la plateforme.

**Why this priority**: Apporte de la visibilité opérationnelle ; non bloquant pour le support direct (US1–US4).

**Independent Test**: La page `/admin/dashboard` charge en moins de 1.5s avec données réelles et affiche cinq blocs (sources, catalogue, PME, activité, LLM).

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il ouvre `/admin/dashboard`, **Then** il voit cinq blocs : Sources (total / pending / verified / outdated + top publishers), Catalogue (fonds, intermédiaires, offres, référentiels publiés vs draft), PME (comptes actifs 30j, nouveaux comptes ce mois), Activité (candidatures par statut, attestations émises, attestations révoquées), LLM (messages 7 derniers jours, taux validation OK/retry/fallback).
2. **Given** une charge typique, **When** la page se rend, **Then** elle est interactive en moins de 1.5s (cache 60s sur les agrégats côté serveur autorisé).
3. **Given** un admin qui rafraîchit la page deux fois en moins de 60s, **When** la deuxième requête arrive, **Then** elle est servie depuis le cache (lecture identique, charge serveur réduite).

---

### User Story 6 — Coûts LLM agrégés (Priority: P3)

En tant qu'équipe technique, je veux voir les coûts LLM totaux par jour/semaine, afin d'anticiper les budgets.

**Why this priority**: Optimisation budgétaire ; les volumes en MVP restent faibles, donc cible P3.

**Independent Test**: Le dashboard affiche un graphique tokens entrée/sortie par jour sur une plage choisie, avec coût estimé selon une grille tarifaire éditable.

**Acceptance Scenarios**:

1. **Given** des appels LLM passés depuis 7 jours, **When** l'admin ouvre la section "LLM Usage" du dashboard et choisit la plage, **Then** un graphique journalier affiche prompt_tokens, completion_tokens et coût estimé en monnaie (Money typé).
2. **Given** un admin qui modifie la grille `LlmPricing` (ajout d'une ligne avec `valid_from` futur), **When** la grille s'active à `valid_from`, **Then** les coûts calculés à partir de cette date utilisent les nouveaux tarifs sans rétro-application sur l'historique.
3. **Given** la collecte des coûts, **When** un appel LLM est effectué, **Then** une ligne `LlmUsageLog` est insérée à partir des `usage` retournés par le provider (pas de re-tokenisation), avec `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `status`, `account_id` (nullable).

---

### Edge Cases

- **Admin tente une mutation hors périmètre autorisé** (édition d'un projet PME, etc.) → API renvoie 403, aucune mutation, ligne d'audit "tentative refusée".
- **Audit log temporairement indisponible** → la requête admin est bloquée (fail-closed) plutôt que servie sans trace ; sinon la garantie SC-002 est cassée.
- **Email provider en panne prolongée** → reset password en file d'attente, statut visible sur le journal admin ; pas de fenêtre où l'admin croit avoir envoyé un email qui n'est jamais parti.
- **Admin consulte 100 fois la même fiche** → 100 lignes d'audit (granularité = par GET de section). Aucun dédoublonnage : la transparence prime.
- **Compte PME supprimé / désactivé** → la fiche admin reste accessible en lecture seule pour audit, marquée "compte désactivé".
- **Token de reset déjà utilisé** → seconde tentative refusée, audit log conservé.
- **Attestation déjà révoquée** → seconde demande de révocation refusée avec message clair ; idempotence préservée.
- **Régénération sans consentement PME** → bloquée, message explicite à l'admin.
- **Recherche admin sur grand volume** (>100k comptes) → pagination obligatoire, recherche indexée, pas de scan complet à chaque saisie.
- **Cache dashboard incohérent** → TTL 60s strict, invalidation explicite sur révocation d'attestation pour propagation immédiate (SC-004).
- **Motif de révocation contenant PII** → filtre PII appliqué côté affichage public (motif libre côté admin, mais sortie publique nettoyée).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La plateforme MUST fournir une page admin paginée listant les comptes PME, avec recherche plein texte sur email et raison sociale (latence < 500ms sur 10k comptes).
- **FR-002**: La plateforme MUST fournir une fiche admin lecture seule par compte PME, agrégeant entreprise, projets, candidatures, scores, attestations, conversations LLM et audit log (chaque sous-section paginable / lazy-loadée).
- **FR-003**: Le système MUST journaliser chaque consultation admin d'un compte PME via une ligne `audit_log` (`entity_type='admin_view'`, `source_of_change='admin'`, `section ∈ {dashboard, projets, candidatures, scores, attestations, llm, audit}` — enum strict) en réutilisant les helpers `record_audit` de F04.
- **FR-004**: La PME MUST pouvoir voir dans son historique d'actions toutes les lignes `admin_view` la concernant, avec email admin, section, horodatage, et SANS IP/User-Agent/PII admin.
- **FR-005**: Le système MUST permettre à un admin de déclencher un reset password pour un user PME ; un email transactionnel avec lien token (durée 1h, single-use) est envoyé via **Resend** (interface `EmailSender` abstraite) ; le token n'est jamais exposé à l'admin. La politique de retry est : 3 tentatives avec backoff exponentiel (1m / 5m / 15m) ; au-delà, statut `failed` consigné dans `EmailDeliveryLog`.
- **FR-006**: Toute action de support (reset password, unlock, revoke attestation, regenerate attestation) MUST produire deux lignes d'audit : côté admin et côté PME (transparence symétrique).
- **FR-007**: Le système MUST refuser toute mutation admin sur les données PME hors des quatre actions whitelistées ci-dessus, avec audit "tentative refusée".
- **FR-008**: Le système MUST permettre à un admin de révoquer une attestation avec motif obligatoire (≥ 10 caractères), positionnant `revoked_at`, `revoked_by`, `revoked_reason` ; la propagation à la page publique de vérification doit être effective en < 60s.
- **FR-009**: Le système MUST permettre à un admin de demander la régénération d'une attestation ; la régénération n'aboutit qu'après consentement explicite consigné de la PME (sinon mise en attente ou refus selon configuration).
- **FR-010**: Le système MUST exposer un endpoint d'agrégats temps réel pour le dashboard admin (sources, catalogue, PME, activité, LLM), avec cache mémoire **in-process backend TTL 60s** (pas de Redis en MVP) et invalidation explicite sur événements critiques (révocation d'attestation).
- **FR-011**: Le système MUST exposer un endpoint d'usage LLM agrégé par jour sur une plage temporelle (tokens entrée/sortie/latence/statut), alimenté par `LlmUsageLog`.
- **FR-012**: Le système MUST permettre aux admins d'éditer la grille `LlmPricing` (Money typé) avec versioning par `valid_from`/`valid_to` ; aucun calcul rétroactif ne doit altérer l'historique.
- **FR-013**: La page `/admin/dashboard` MUST afficher cinq blocs (Sources, Catalogue, PME, Activité, LLM) avec graphiques chart.js et charge interactive < 1.5s.
- **FR-014**: Le système MUST consigner et exposer aux admins un journal des échecs d'envoi d'email transactionnel (statut, dernière tentative, retries) accessible depuis le dashboard.
- **FR-015**: Les filtres PII MUST être appliqués sur le motif de révocation lorsqu'il est rendu sur la page publique `/verify/{id}` (motif libre côté admin, sortie publique nettoyée).
- **FR-016**: Toutes les interactions multi-étapes destructrices ou révocables (révocation, régénération, reset) MUST utiliser le pattern bottom sheet (Module 0) côté front pour la confirmation et la saisie de motif.
- **FR-017**: Tous les endpoints admin MUST appliquer la RLS / contrôle de rôle (réutilisation F02) : seul le rôle admin a accès, et chaque accès est journalisé.
- **FR-018**: La plateforme MUST rester fermée (PME + Admin uniquement) ; aucune route admin ne doit être exposée à un rôle PME via élévation accidentelle.

### Key Entities

- **AdminViewAuditEntry** *(non nouvelle table — usage spécifique de `audit_log` F04)* : enregistrement append-only de chaque consultation admin avec `entity_type='admin_view'`, `entity_id=account_id`, `actor_admin_email`, `section`, horodatage, `source_of_change='admin'`.
- **PasswordResetToken** *(éventuel partage avec F02)* : token single-use, TTL 1h, lié à `user_id`, jamais exposé à l'admin ; consommé sur première utilisation.
- **AttestationRevocation** *(extension de l'attestation existante F30 — pas de nouvelle table)* : champs `revoked_at`, `revoked_by`, `revoked_reason` ajoutés sur l'entité Attestation.
- **LlmUsageLog** *(nouvelle table)* : `id`, `account_id` (nullable), `user_id` (nullable), `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `status`, `created_at`. Réutilisée par F35 (Eval).
- **LlmPricing** *(nouvelle table)* : `id`, `model`, `prompt_per_1k_money`, `completion_per_1k_money`, `valid_from`, `valid_to`. Money typé. Versioning temporel par `valid_from`/`valid_to`.
- **EmailDeliveryLog** *(nouvelle table légère)* : `id`, `kind` (reset_password / notification), `recipient_user_id`, `status` (queued/sent/failed/bounced), `last_attempt_at`, `retries`, `provider_message_id`. Visible aux admins pour diagnostic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un admin résout un cas "PME a perdu son mot de passe" en moins de 2 minutes depuis l'ouverture du back-office (mesuré sur 10 cas en recette).
- **SC-002**: 100 % des consultations admin de comptes PME apparaissent dans l'audit log de la PME (vérifié par test automatisé sur tous les endpoints admin lecture).
- **SC-003**: Le dashboard admin charge en moins de 1.5 seconde (P95) avec données réelles de production.
- **SC-004**: La révocation d'attestation est visible sur la page publique de vérification en moins de 60 secondes après l'action admin.
- **SC-005**: La fiche admin d'un compte PME (10 projets / 50 candidatures / 1000 messages LLM) atteint l'état interactif en moins de 2 secondes (P95).
- **SC-006**: Aucun token de reset password n'est jamais retourné par une API au rôle admin (vérifié par audit de schémas de réponse + tests).
- **SC-007**: 0 incident de mutation admin sur données PME hors whitelist (mesuré par audit log "tentative refusée" — toute violation déclenche alerte CI).

## Assumptions

- Les rôles `admin` et `pme` (F02) sont déjà en place avec RLS active ; les comptes admin sont gérés en pré-provisionnement (pas de self-signup admin).
- Les helpers `record_audit` (F04) acceptent un `entity_type` libre dont `admin_view` ; sinon une migration mineure est ajoutée.
- L'historique d'actions PME (F32) sait afficher les lignes `admin_view` ; sinon un widget minimal est livré ici.
- La page publique `/verify/{id}` (F30) n'est pas encore livrée ; cette feature livre uniquement les hooks (champs `revoked_*`) consommés par F30.
- Le wrapper LLM central (F18 / F35) renvoie systématiquement les `usage` du provider ; aucune retokenisation locale n'est faite.
- Le cache d'agrégats du dashboard est un cache mémoire backend (pas Redis dédié en MVP) ; TTL 60s.
- Les notifications PME pour révocation/régénération réutilisent le canal de notifications existant ou tombent en in-app si email indisponible.
- Le filtre PII appliqué au motif public est une fonction utilitaire partagée (déjà en place ou créée ici comme micro-service de masquage).
- Le format Money typé (Module 0) est utilisé pour `LlmPricing` (devise + amount entier en plus petite unité).
- Le pattern bottom sheet (Module 0) est implémenté côté front ; cette feature n'invente pas de UX nouvelle.
- Aucun commit/push n'est effectué par cette spec ; toute la livraison reste sur la branche `010-admin-support-pme-metrics`.

## Out of Scope (MVP)

- Impersonification admin ("login as PME").
- Tickets de support intégrés (Zendesk, GLPI, etc.).
- Coût LLM ventilé par PME (post-MVP ; MVP = agrégat global).
- Métriques business (chiffre d'affaires financements, taux de conversion candidatures…).
- Alerting automatique (email admin si seuil dépassé).
- Mécanisme de "consentement édition admin" pour autoriser ponctuellement une correction côté admin.
- Verrouillage automatique de compte après N tentatives (l'unlock est prévu mais le mécanisme de lock est post-MVP).

## Open Clarifications

_Toutes les clarifications ont été résolues dans la session du 2026-04-29 (voir section ## Clarifications)._
