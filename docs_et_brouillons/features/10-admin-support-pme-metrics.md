# F10 — Support PME Admin & Métriques Admin

**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 9.3 (Support PME), 9.4 (Métriques Admin)
**Dépendances** : F02, F04, F06
**Estimation** : 1.5 jours

## Contexte et objectif

Permettre à l'équipe ESG Mefali d'**aider une PME en difficulté** (réinitialiser un mot de passe, débloquer un compte, révoquer une attestation compromise) tout en préservant la confidentialité (chaque consultation d'un compte PME est elle-même journalisée), et fournir un **tableau de bord agrégé** sur l'état du catalogue et des PME.

Pas de surveillance abusive : un admin qui consulte un compte PME laisse une trace dans l'audit log de la PME, qui peut elle-même voir cette trace dans son historique (F04 + F32). C'est une garantie de confiance.

## User Stories

### US1 — Vue lecture seule des comptes PME (P1)
**En tant qu'**admin support,
**je veux** ouvrir une page admin qui liste les comptes PME avec recherche par email/nom d'entreprise, et cliquer pour voir un compte en lecture seule,
**afin de** diagnostiquer un problème reporté par une PME.

**Test indépendant** : page `/admin/pme` liste les comptes ; cliquer ouvre `/admin/pme/{account_id}` qui affiche entreprise, projets, candidatures, scores, attestations, conversations LLM, audit log — **toujours en lecture seule** (aucun bouton d'édition pour l'admin sur les données PME).

### US2 — Chaque consultation admin est tracée (P1)
**En tant que** PME,
**je veux** voir dans mon historique d'actions (F04 + F32) une ligne quand un admin consulte mes données, avec qui et quand,
**afin de** garantir la transparence.

**Scénarios** :
1. Admin ouvre `/admin/pme/{id}` → ligne audit_log : `entity_type='admin_view', entity_id=account_id, source_of_change='admin', notes='consultation support'`.
2. La PME voit la ligne dans son historique. Aucun champ sensible n'est exposé sur ce log (pas de IP de l'admin, juste son email).

### US3 — Réinitialisation de mot de passe (P1)
**En tant qu'**admin support,
**je veux** déclencher l'envoi d'un email de réinitialisation à un user PME bloqué,
**afin de** débloquer un compte sans avoir accès au mot de passe.

**Scénarios** :
1. Admin clique "Reset password" sur un user → email envoyé (template) avec lien token unique 1h.
2. Action auditée dans audit_log de l'admin et de la PME.
3. L'admin **ne voit jamais** le mot de passe ni le token.

### US4 — Régénération / révocation d'attestations (P1)
**En tant qu'**admin support,
**je veux** révoquer une attestation publique en cas d'incident (donnée compromise, score frauduleux, demande PME), avec motif obligatoire,
**afin de** mettre à jour la page publique de vérification (F30).

**Scénarios** :
1. Admin clique "Révoquer attestation X", saisit motif → attestation passe `revoked_at=now()`, `revoked_by=admin_id`, `revoked_reason='...'`.
2. La page publique `/verify/{id}` affiche maintenant "Attestation révoquée le YYYY-MM-DD" + motif **non sensible** (motif libre côté admin mais filtre PII recommandé).
3. La PME reçoit une notification (ou voit l'événement dans son dashboard).

### US5 — Tableau de bord admin agrégé (P2)
**En tant qu'**équipe ESG Mefali,
**je veux** une page `/admin/dashboard` qui affiche :
- Sources : total, `pending`, `verified`, `outdated`, top publishers,
- Catalogue : nombre de fonds, intermédiaires, offres, référentiels publiés vs draft,
- PME : nombre de comptes actifs (login dans 30 derniers jours), nouveaux comptes ce mois-ci,
- Activité : candidatures en cours par statut, attestations émises, attestations révoquées,
- LLM : nombre de messages LLM les 7 derniers jours, taux de validation OK / retry / fallback.

**afin de** piloter la plateforme.

### US6 — Coûts LLM agrégés (P3)
**En tant qu'**équipe technique,
**je veux** voir les coûts LLM totaux par jour/semaine,
**afin de** anticiper les budgets.

(Niveau MVP simple : compteur de tokens entrée/sortie agrégé. Coût par PME = post-MVP.)

## Exigences fonctionnelles

- **FR-001** : Page `/admin/pme` (liste paginée des comptes, recherche email/entreprise).
- **FR-002** : Page `/admin/pme/{account_id}` (lecture seule de l'ensemble des données du compte).
- **FR-003** : Middleware FastAPI `audit_admin_view(account_id)` appelé sur chaque GET d'un compte PME → insertion dans `audit_log` avec `source_of_change='admin'`.
- **FR-004** : Endpoint `POST /admin/users/{user_id}/reset-password` → génère token 1h, envoie email (via SMTP — provider à clarifier, en MVP un service simple type Resend/Postmark/SES). Audit. Pas de retour du token côté admin.
- **FR-005** : Endpoint `POST /admin/users/{user_id}/unlock` (si verrouillage post-MVP) → désactive le verrou. Audit.
- **FR-006** : Endpoint `POST /admin/attestations/{id}/revoke` avec body `{reason}` → `revoked_at, revoked_by, revoked_reason`. Audit.
- **FR-007** : Endpoint `POST /admin/attestations/{id}/regenerate` → nouvelle version d'attestation pour la PME (la PME doit valider/accepter, ou l'admin agit avec consentement explicite consigné).
- **FR-008** : Endpoint `GET /admin/dashboard/stats` → agrégats temps réel (avec cache 60s pour ne pas surcharger).
- **FR-009** : Endpoint `GET /admin/dashboard/llm-usage?from=&to=` → tokens entrée/sortie par jour. Compteurs incrémentés par le wrapper LLM (logger central).
- **FR-010** : Page `/admin/dashboard` (Vue) consommant les endpoints, avec graphiques (chart.js déjà installé en F01).

## Exigences non-fonctionnelles

- **NFR-001** : Aucune mutation directe par l'admin sur les données PME (entreprise, projets, candidatures, etc.). Seules exceptions : reset password, unlock, revoke attestation, regenerate attestation. Toutes auditées.
- **NFR-002** : La page de consultation PME charge en < 2s pour un compte avec 10 projets, 50 candidatures, 1000 messages chat.
- **NFR-003** : L'envoi d'email de reset utilise une queue ou retry ; un échec d'envoi est visible dans un journal admin.
- **NFR-004** : Les coûts LLM sont calculés à partir des tokens et d'une table `llm_pricing(model, prompt_per_1k, completion_per_1k, valid_from)` éditable par les admins (au cas où OpenRouter ajuste).

## Entités clés

- Aucune nouvelle table métier majeure.
- `LlmUsageLog` (id, account_id NULL, user_id NULL, model, prompt_tokens, completion_tokens, latency_ms, status, created_at) — alimenté par le wrapper LLM. Sera ré-utilisé par F35 (Eval).
- `LlmPricing` (id, model, prompt_per_1k_money, completion_per_1k_money, valid_from, valid_to).

## Success Criteria

- **SC-001** : Un admin résout un cas "PME a perdu son mot de passe" en < 2 min via le back-office.
- **SC-002** : 100% des consultations admin de comptes PME apparaissent dans l'audit log de la PME.
- **SC-003** : Le dashboard admin charge en < 1.5s avec données réelles.
- **SC-004** : La révocation d'attestation propage immédiatement à la page publique `/verify/{id}` (test E2E).

## Hors-scope MVP

- Outils de support avancés : impersonification temporaire (login as), assistance live chat avec la PME.
- Tickets de support intégrés (GLPI, Zendesk).
- Coûts LLM par PME (post-MVP).
- Métriques de business (CA financements obtenus via plateforme, post-MVP).
- Alerting automatique (admin email si X> seuil) — on garde en post-MVP.

## Risques et points de vigilance

- **Audit asymétrique** : la PME doit voir QUE l'admin l'a consultée mais pas forcément ce qu'il a regardé en détail. Définir un niveau de granularité acceptable. Recommandation : log `entity_type='admin_view', section='dashboard'` (ou `'projets'`, `'candidatures'`, etc.) sans détail intra-section.
- **Email transactionnel** : choix du provider (Resend / Postmark / Mailgun / SES) à trancher en `/speckit.clarify`. Pas de bloquant code mais variable d'env à prévoir.
- **Coûts LLM calculés** : OpenRouter renvoie `usage` dans la réponse. S'appuyer dessus, pas re-tokeniser.
- **Lecture vs écriture admin** : il sera tentant pour un admin de "corriger" rapidement un projet PME défaillant. Refuser strictement en MVP — c'est la PME qui édite. Sinon, mécanisme de "consentement édition admin" plus complexe (post-MVP).
