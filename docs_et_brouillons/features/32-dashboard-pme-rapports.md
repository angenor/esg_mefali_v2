# F32 — Dashboard PME (scores, candidatures, rapports, audit log, Mes données, multi-utilisateurs)

**Phase** : 10 — Tableau de Bord PME (Module 7)
**Modules brainstorm** : 7.1 (Dashboard Principal), 7.2 (Rapports / Exports / Audit Log), 7.3 (Multi-utilisateurs simplifié)
**Dépendances** : F04, F05, F23, F24, F25, F30, F31
**Estimation** : 2 jours

## Contexte et objectif

Le tableau de bord PME est la **page d'accueil après login** : vue synthétique, navigation centrale vers toutes les features. Il consolide ce qui a déjà été livré dans les phases précédentes (scores ESG, candidatures, attestations, plan d'action) et ajoute :
- exports rapports/historiques,
- visibilité de l'**audit log** côté PME (cohérent F04),
- page **"Mes données"** (cohérent F05),
- multi-utilisateurs simplifié (tous égaux, commentaires sur projets/candidatures).

## User Stories

### US1 — Page d'accueil dashboard (P1)
**En tant que** PME,
**je veux** au login arriver sur `/dashboard` qui affiche :
- mes 3 scores principaux (ESG Mefali, score combiné crédit, empreinte carbone),
- prochaines actions recommandées (issues du plan F31),
- statut des candidatures par Offre (couple Fonds × Intermédiaire) — étape, prochain rappel, prochaine échéance,
- carte des intermédiaires actifs et de leurs accréditations en cours (cohérent F08).

**afin de** une vue 360° de ma situation.

### US2 — Graphes d'évolution (P1)
**En tant que** PME,
**je veux** voir des graphes d'évolution sur 12 mois :
- score ESG (par référentiel sélectionné),
- empreinte carbone,
- score crédit combiné.

**afin de** suivre mes progrès.

### US3 — Statut des candidatures par Offre (P1)
**En tant que** PME,
**je veux** une section dédiée listant chaque candidature avec :
- Offre (Fonds + Intermédiaire),
- statut (cohérent F25),
- étape suivante,
- prochain rappel (cohérent F31),
- date échéance.

### US4 — Carte des intermédiaires (P2)
**En tant que** PME,
**je veux** un Leaflet (`show_map` F16) avec les intermédiaires actifs (BOAD, NSIA, Ecobank, etc.) géolocalisés et leurs accréditations en cours,
**afin de** vue géographique.

### US5 — Téléchargements groupés (P1)
**En tant que** PME,
**je veux** une page `/dashboard/exports` listant :
- rapports ESG complets (F24),
- rapports carbone,
- attestations émises (F30),
- export complet de mes données (cohérent F05 — "Mes données" page),
- historique des candidatures par Offre,

**afin de** avoir tout sous la main.

### US6 — Page "Mes données" (P1)
**En tant que** PME,
**je veux** `/dashboard/mes-donnees` (cohérent F05 US1) :
- résumé de mes données stockées,
- export JSON,
- gestion consentements (lien vers F05),
- demande suppression compte.

### US7 — Historique des actions (audit log côté PME) (P1)
**En tant que** PME,
**je veux** `/dashboard/historique` qui affiche l'audit log filtré sur mon compte (cohérent F04 US3) :
- qui (moi / collaborateur / LLM / admin),
- quoi (entité, champ),
- quand,
- avant/après.

**afin de** transparence + traçabilité.

### US8 — Multi-utilisateurs simplifié (P2)
**En tant que** PME avec collaborateurs,
**je veux** :
- inviter d'autres users sur mon Account (email),
- voir la liste des users actifs,
- révoquer l'accès d'un user,
- tous ont les mêmes droits (cohérent Module 7.3).

**afin de** travailler en équipe sans complexité RBAC.

### US9 — Commentaires sur projets et candidatures (P2)
**En tant que** PME / collaborateur,
**je veux** ajouter des commentaires libres sur un projet ou une candidature (avec horodatage et auteur),
**afin de** discussion interne.

**Aucun workflow d'approbation** en MVP — juste des notes.

### US10 — L'audit log trace qui a fait quoi (P1)
**En tant que** PME,
**je veux** que l'audit log distingue clairement les actions de chaque collaborateur,
**afin de** transparence.

## Exigences fonctionnelles

- **FR-001** : Page `/dashboard` (Vue) avec sections (US1) :
  - Cards scores principaux,
  - Prochaines actions (consomme F31),
  - Candidatures (consomme F25),
  - Carte intermédiaires (consomme F08).
- **FR-002** : Endpoint `GET /me/dashboard/summary` qui agrège tout en un seul appel optimisé.
- **FR-003** : Page `/dashboard/exports` listant fichiers téléchargeables (`/me/rapports`, `/me/attestations`, etc.).
- **FR-004** : Page `/dashboard/mes-donnees` consomme les endpoints F05.
- **FR-005** : Page `/dashboard/historique` consomme `/me/audit-log` (F04 FR-005) avec filtres.
- **FR-006** : Endpoints multi-users :
  - `POST /me/account/users/invite` body `{email}` → email invitation token 24h.
  - `GET /me/account/users` (liste).
  - `DELETE /me/account/users/{id}` (révoque).
  - Ajout au `account_id` du compte invitant.
- **FR-007** : Page `/dashboard/equipe` (CRUD users du compte).
- **FR-008** : Table `commentaire` : `id, account_id, user_id, entity_type ENUM('projet','candidature'), entity_id, body, created_at`.
- **FR-009** : Endpoints commentaires : `GET/POST /me/{entity}/{id}/commentaires`.
- **FR-010** : Composant Vue `<CommentairesPanel :entity-type :entity-id>` réutilisé sur les pages projet/candidature.

## Exigences non-fonctionnelles

- **NFR-001** : Dashboard charge en < 1.5s (dont endpoint summary < 500ms).
- **NFR-002** : RLS strict (F02) : 100% des données sont scope au compte.
- **NFR-003** : Tous les chiffres affichés sont sourcés (cohérent F03).
- **NFR-004** : Mobile responsive (les PME accèdent souvent depuis mobile).

## Entités clés

- **Commentaire** (FR-008).
- Réutilise toutes les entités précédentes (Score, Candidature, Attestation, AuditLog, etc.).

## Success Criteria

- **SC-001** : Dashboard charge avec données réelles d'une PME démo en < 1.5s.
- **SC-002** : Inviter un collègue, il rejoint le compte, accès à toutes les données.
- **SC-003** : Commentaires sur 1 projet visibles par tous les collaborateurs.
- **SC-004** : Historique audit log lisible et filtrable.
- **SC-005** : Mes données : export JSON complet et valide.

## Hors-scope MVP

- Workflow d'approbation interne (post-MVP).
- RBAC granulaire (Owner/Member/Viewer) — post-MVP.
- Notifications in-app (post-MVP, pour MVP : email + dashboard).
- Personnalisation du dashboard (widgets configurables).
- Tableaux de bord croisés (multi-PME pour groupes — post-MVP).

## Risques et points de vigilance

- **Endpoint summary surchargé** : si on agrège tout naïvement, latence haute. Préférer N requêtes parallèles côté front + page rendue progressivement (skeleton).
- **Invitations email** : nécessite le service email (cohérent F10 / F31). Ne pas dupliquer le mécanisme.
- **Commentaires et audit log** : un commentaire est-il une mutation ? Recommandation : oui, audité (cohérent F04).
- **Multi-users et tests d'isolation** : 2 users du même Account voient les mêmes données ; 2 users d'Accounts différents NE voient PAS les données croisées (RLS F02). Test indispensable.
- **UX mobile** : carte Leaflet sur mobile peut être lourde. Lazy-load.
