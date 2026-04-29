# F17 — Tools de Mutation LLM (CRUD profil, projets, candidatures, attestations, scores)

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 1.1.3 (LLM Moteur d'Action sur la Plateforme)
**Dépendances** : F04, F11, F12, F14, F15
**Estimation** : 2.5–3 jours

## Contexte et objectif

Le LLM ne fait pas que répondre — il **fait**. Il peut effectuer toute action métier sur la plateforme via des **tools de mutation** : créer un projet en langage naturel, marquer une candidature acceptée, générer un dossier ou une attestation, supprimer une donnée.

> **Garde-fous obligatoires (du brainstorming)** :
> - Toute action **destructive** (delete, revoke, écrasement majeur) → confirmation via `ask_yes_no` (F15) avant exécution.
> - Toute action **journalisée** dans audit log (F04) avec `source_of_change='llm'`.
> - Le LLM ne peut **JAMAIS** modifier le catalogue (Fonds, Intermédiaires, Référentiels, Indicateurs, Sources, Templates) — réservé aux admins via back-office (F08, F09).
> - Mutations **scoped au compte** : RLS garantit qu'un LLM agissant pour PME A ne peut jamais toucher PME B.

## User Stories

### US1 — update_company_profile en langage naturel (P1)
**En tant que** PME,
**je veux** dire au LLM "mon CA est de 250M FCFA et j'ai 75 employés" → le LLM met à jour mon entreprise (F11),
**afin de** ne pas avoir à naviguer dans le formulaire.

**Test indépendant** : message texte → LLM extrait → invoque `update_company_profile({taille_ca_money: {amount: 250000000, currency: 'XOF'}, taille_effectifs: 75})` → entreprise mise à jour, audit log écrit, EventBus notifie l'UI (F13 US4).

### US2 — create_project / update_project / delete_project (P1)
**En tant que** PME,
**je veux** dire "crée un projet de panneaux solaires de 50 MW dans le nord du Sénégal pour 5M EUR" → le LLM crée un projet préfilled,
**afin de** démarrer rapidement.

**Scénarios** :
1. `create_project` : LLM extrait → invoque tool → projet en `brouillon`. Le LLM peut suivre par `ask_qcm` pour les types d'impact, etc.
2. `update_project` : modifications partielles autorisées.
3. `delete_project` : **destructif** → demande `ask_yes_no` "Confirmer la suppression du projet 'Panneaux solaires Nord' ?" avant.

### US3 — create_candidature / update_candidature_status / delete_candidature (P1)
**En tant que** PME,
**je veux** dire "candidate au GCF via BOAD pour mon projet panneaux" → le LLM crée la candidature,
**afin de** lancer un dossier.

`update_candidature_status` permet de signaler un changement (acceptée, refusée, en instruction) — saisie manuelle via LLM, alternative au statut UI.

### US4 — attach_document : Attacher un document à une entité (P2)
**En tant que** PME,
**je veux** dire "attache ce PDF à mon projet panneaux" (avec `ask_file_upload` de F15),
**afin de** lier rapidement.

### US5 — recompute_score : Recalculer un score ESG (P2)
**En tant que** PME,
**je veux** dire "recalcule mon score GCF avec les nouvelles infos" → le LLM invoque le service de scoring (F23),
**afin de** voir l'impact de mes mises à jour.

### US6 — generate_attestation / revoke_attestation (P2)
**En tant que** PME,
**je veux** dire "génère mon attestation publique" → le LLM appelle F30,
**afin de** obtenir un PDF signé sans naviguer.

`revoke_attestation` est destructif → `ask_yes_no` obligatoire.

### US7 — generate_dossier (P2)
**En tant que** PME,
**je veux** dire "génère le dossier pour ma candidature GCF/BOAD en français" → le LLM appelle F26,
**afin de** déclencher la rédaction par la skill associée.

### US8 — Confirmation systématique des actions destructives (P1)
**En tant que** PME,
**je veux** que toute action irréversible (delete, revoke, écrasement majeur) déclenche un `ask_yes_no` listant clairement ce qui va se passer,
**afin de** ne jamais perdre une donnée par accident.

### US9 — Bandeau "Action LLM en cours" + UNDO court (P2)
**En tant que** PME,
**je veux** voir un bandeau "Le LLM a modifié votre projet — Annuler dans 10s ?" après une mutation non destructive,
**afin de** revenir en arrière vite si le LLM a mal compris.

**Mécanisme MVP simple** : pour chaque mutation, on snapshot l'avant-état dans `audit_log.old_value` et on expose un endpoint `POST /me/audit-log/{id}/revert` pour les opérations idempotentes (mises à jour de champ). Pas de revert sur create/delete (utiliser CRUD direct).

### US10 — Aucune mutation sur le catalogue (P1)
**En tant que** garant de l'intégrité,
**je veux** que le LLM **ne puisse pas** invoquer de mutation sur Fonds/Intermédiaires/Offres/Référentiels/Indicateurs/Sources/Skills/Templates,
**afin de** réserver la maintenance du catalogue aux admins.

**Implémentation** : ces tools n'existent **pas** dans le registry (F14 TOOL_REGISTRY) côté PME. Le sélecteur de tools (F14 US2) ne peut donc pas les exposer.

## Exigences fonctionnelles

- **FR-001** : Tools de mutation déclarés via `@tool` (F14) avec schémas Pydantic stricts :
  - `update_company_profile(fields: dict)`,
  - `create_project(fields)`, `update_project(id, fields)`, `delete_project(id)`,
  - `create_candidature(project_id, offre_id)`, `update_candidature_status(id, status)`, `delete_candidature(id)`,
  - `attach_document(entity_type, entity_id, doc_id)`,
  - `recompute_score(entity_id, referentiel_id)`,
  - `generate_attestation(score_id)`, `revoke_attestation(id, reason)`,
  - `generate_dossier(candidature_id, language)`.
- **FR-002** : Décorateur backend `@destructive` qui : avant exécution, vérifie qu'un `ask_yes_no` confirmation a été donnée dans le tour précédent (ou exige une confirmation explicite via un argument `confirmed=true` du tool). Sinon, le tool retourne un résultat structuré demandant au LLM d'invoquer `ask_yes_no` avant.
- **FR-003** : Décorateur `@audited` qui appelle automatiquement `record_audit(...)` (F04 helper) avec `source_of_change='llm'`, l'avant-état complet, l'après-état, le tool name.
- **FR-004** : RLS appliquée systématiquement (F02) : le tool handler exécute la mutation dans la session Postgres avec `app.current_account_id` set sur le compte du user — impossible d'écrire en dehors.
- **FR-005** : Pour chaque mutation, l'EventBus (F13 FR-008) émet `entity_updated` → l'UI réagit en temps réel.
- **FR-006** : Endpoint `POST /me/audit-log/{id}/revert` pour les mutations idempotentes (US9). Les mutations non revertibles (delete) génèrent un audit log mais pas de revert button.
- **FR-007** : Validation Pydantic stricte (F14) : aucun champ extra accepté, types stricts, enums fermés, FK existence vérifiée.
- **FR-008** : Le sélecteur de tools (F14 US2) **n'expose** les mutations qu'aux contextes pertinents :
  - Page Profil → Entreprise : `update_company_profile`.
  - Page Profil → Projets : `create_project`, `update_project`, `delete_project`.
  - Page Candidatures : `create_candidature`, `update_candidature_status`, `delete_candidature`.
  - Globalement (chat flottant) : sous-ensemble selon entité active.
- **FR-009** : Aucun tool de mutation **catalogue** dans le registry pour rôle PME. Les tools admin sont dans un registry séparé (post-MVP : Module 1.1.3 ne le couvre pas).
- **FR-010** : Limitation de débit : pas plus de 10 mutations LLM en 1 minute par user (anti-abus).

## Exigences non-fonctionnelles

- **NFR-001** : Latence d'une mutation simple (`update_company_profile` 1 champ) < 500ms backend.
- **NFR-002** : 100% des mutations sont auditées + 100% RLS appliqué (testé par tests d'intégration).
- **NFR-003** : Confirmation destructive : ne JAMAIS contourner. Test e2e qui tente d'invoquer `delete_project` sans confirmation → rejet.
- **NFR-004** : L'UNDO (US9) fonctionne sur les 10 dernières secondes, pas plus (UI sobre).

## Entités clés

- Aucune nouvelle table — l'état est dans les tables métier déjà créées + `audit_log`.

## Success Criteria

- **SC-001** : Les 11 tools de mutation fonctionnent end-to-end sur une PME de test (audit log + EventBus + UI réactive).
- **SC-002** : Tentative `delete_project` sans confirmation → tool retourne "demande confirmation via ask_yes_no" → LLM enchaîne avec `ask_yes_no` → utilisateur confirme → suppression OK.
- **SC-003** : Tentative cross-tenant (LLM agissant pour PME A invoque mutation avec ID d'une PME B) → 404, audit log d'incident.
- **SC-004** : UNDO sur `update_company_profile` rétablit l'avant-état en < 1s.
- **SC-005** : Tool catalogue (`update_referentiel`) absent du registry PME — testé.

## Hors-scope MVP

- Mutations sur le catalogue par admin via LLM (post-MVP, non recommandé même à terme).
- Multi-step transactions (créer projet + uploader doc + créer candidature en 1 seul tool) — préférer la composition de tools simples par le LLM.
- Schedule mutation différée ("modifie ça demain") — post-MVP.

## Risques et points de vigilance

- **Confusion d'entité** : le LLM peut invoquer `update_project` avec le mauvais `id` (un projet d'une autre conversation). RLS protège, mais UX cassée. Mitigation : le contexte de page (F13 US3) doit être prioritaire ; le LLM ne devrait invoquer que des entités présentes dans le contexte actif. Contrainte à inscrire dans le system prompt (F14).
- **Cascades** : `delete_project` supprime les candidatures liées (cohérent F12). Le `ask_yes_no` doit lister explicitement les conséquences ("Ceci supprimera aussi 2 candidatures").
- **Abus** : un user malveillant peut spammer le LLM pour générer 1000 projets. Rate limit (FR-010) + détection d'anomalie (post-MVP).
- **Audit log volumineux** : chaque mutation = 1 ligne. Une session active peut générer 50 lignes/heure. Index + post-MVP partitionnement.
- **`recompute_score`** : invoque F23 — assurer que c'est synchrone (pas async/queue) en MVP, sinon UX bizarre.
- **`generate_dossier`** : peut prendre 30s-1min (génération via skill, F26). Streaming d'avancement obligatoire.
