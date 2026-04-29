# F08 — Catalogue Fonds, Intermédiaires & Offres

**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 3.1 (Catalogue), 9.1 (Gestion du Catalogue)
**Dépendances** : F04, F06, F07
**Estimation** : 3 jours

## Contexte et objectif

C'est la **différenciation cœur** de la plateforme : modéliser les **trois entités** Fonds source, Intermédiaire accrédité, Offre (= couple Fonds × Intermédiaire) — pas juste une liste de fonds.

> **Vérité du terrain (brainstorming)** : la plupart des grands fonds verts ne décaissent jamais directement aux PME africaines. L'**Intermédiaire** est souvent le vrai filtre, et c'est l'**Offre** qui est l'unité commercialement accessible. Une PME peut être éligible "GCF via BOAD" et incompatible "GCF via UNDP" — la plateforme doit montrer cette nuance.

Cette feature livre :
- CRUD admin pour les 3 entités + table d'accréditation (Intermédiaire ↔ Fonds, datée, plafonnée).
- Calcul automatique des "critères effectifs" et "documents effectifs" d'une Offre comme intersection/union des deux entités sources.
- Vue "comparateur d'intermédiaires pour un même fonds" (pour les PME, qui sera consommée par F25 Matching).

## User Stories

### US1 — CRUD Fonds source (P1)
**En tant qu'**admin,
**je veux** créer/éditer/publier un Fonds source avec tous ses attributs (identité, thématique, instruments, plafonds, éligibilité géo, taxonomie/référentiel propre, submission_mode),
**afin de** modéliser GCF, FEM, AFD, BAD, BOAD, BIDC, etc.

**Test indépendant** : POST `/admin/fonds/`, formulaire complet, statut `draft`, devient `published` après vérification des sources liées (F06). Au moins 1 source `verified` requise (politique du fonds, taxonomie).

### US2 — CRUD Intermédiaire accrédité (P1)
**En tant qu'**admin,
**je veux** créer/éditer/publier un Intermédiaire (BOAD, NSIA, Ecobank, PNUD, Atmosfair, etc.) avec identité, type, pays, contact, frais, délais,
**afin de** modéliser les acteurs qui décaissent vraiment.

### US3 — Accréditations datées et plafonnées (P1)
**En tant qu'**admin,
**je veux** une table d'accréditation à 3 dimensions (Intermédiaire × Fonds × période), avec plafond Money, statut, source officielle de l'accréditation,
**afin de** modéliser que BOAD est accréditée NIE pour GCF depuis YYYY-MM, avec un plafond X.

**Scénarios** :
1. Une accréditation a un `valid_from`, optionnel `valid_to`, un plafond Money typé (Module 0.6).
2. Une Offre ne peut exister que si une accréditation `active` (now() entre valid_from et valid_to) existe entre son fonds et son intermédiaire.
3. Une accréditation expirée passe automatiquement les Offres associées en `outdated`.

### US4 — CRUD Offre = couple (Fonds × Intermédiaire) (P1)
**En tant qu'**admin,
**je veux** créer une Offre en sélectionnant un Fonds et un Intermédiaire (parmi ceux ayant accréditation active), et que les **critères effectifs** et **documents effectifs** soient calculés automatiquement :
- critères = intersection des critères du fonds et de l'intermédiaire (souvent restrictif),
- documents = union des documents requis,
- frais = frais fonds + marges intermédiaire,
- délais = délais fonds + délais intermédiaire,
- référentiel effectif = référentiel fonds + couche intermédiaire (consommé par F23 Scoring).

**afin de** ne pas saisir 2 fois ce qui peut être dérivé.

**Scénarios** :
1. Création Offre "GCF via BOAD" → critères auto-calculés en lecture, l'admin peut ajouter des `criteres_offre_specifiques` (rares mais possibles).
2. Le fonds modifie ses critères (nouvelle version) → l'Offre doit être ré-générée (ou un badge "à mettre à jour" apparaît).
3. `accepted_languages` (FR, EN) saisi sur l'Offre — consommé par F26 Génération de dossier.

### US5 — Vue "comparateur intermédiaires pour un même fonds" (P2)
**En tant qu'**admin (ou plus tard PME via F25),
**je veux** une vue tabulaire qui aligne tous les intermédiaires accrédités pour un fonds donné avec leurs critères/frais/délais/track-record,
**afin de** voir d'un coup d'œil "GCF via BOAD vs GCF via UNDP vs GCF via PNUE".

### US6 — Submission mode (rolling vs call_for_proposals) (P2)
**En tant qu'**admin,
**je veux** distinguer les fonds à guichet ouvert (`rolling`) des appels à projets datés (`call_for_proposals` avec sessions/échéances),
**afin de** alimenter les alertes et la timeline (F25, F31).

**Scénarios** :
1. Fonds GCF → `rolling`, pas de date limite globale.
2. Programme spécifique AFD/proparco "Adapt'Action 2026" → `call_for_proposals` avec `deadline=2026-09-30`.
3. Une Offre dérivée d'un fonds `call_for_proposals` hérite de la deadline.

## Exigences fonctionnelles

- **FR-001** : Table `fonds_source` : `id, name, organisation, type ENUM('multilateral','bilateral','regional','national','prive'), thematique[], instruments[], plafond_money, plancher_money, eligibilite_geo[], submission_mode ENUM('rolling','call_for_proposals'), referentiel_id (FK vers Referentiel propre), site_url, contact_json, version, status, source_ids[]`.
- **FR-002** : Table `intermediaire` : `id, name, type ENUM('DAE','NIE','RIE','MIE','banque_locale','dev_carbone','agence_nationale','agence_implem'), pays[], zone_op, contact_json, frais_json, delais_json, portail_url, track_record_json, version, status, source_ids[]`.
- **FR-003** : Table `accreditation` : `id, intermediaire_id, fonds_id, valid_from, valid_to NULL, plafond_money, source_id, notes`. Index `(intermediaire_id, fonds_id, valid_from)`. Helper `is_active(at?)`.
- **FR-004** : Table `offre` : `id, fonds_id, intermediaire_id, name, accepted_languages TEXT[], deadline TIMESTAMPTZ NULL (override possible), criteres_offre_specifiques JSONB, frais_specifiques JSONB, delais_specifiques JSONB, version, status, source_ids[]`. Contrainte : il existe une accréditation active sur la période de l'Offre.
- **FR-005** : Endpoint `GET /admin/offres/{id}/effective` → calcule et retourne `{criteres_effectifs:[...], documents_effectifs:[...], frais_effectifs:Money, delais_effectifs:int_jours, referentiel_effectif:{fonds, intermediaire}, accepted_languages}`. Cette vue est ce que consomme F25 (Matching) et F26 (Dossier).
- **FR-006** : Endpoint `GET /admin/fonds/{id}/intermediaires` → liste des intermédiaires accrédités actifs (avec leurs offres dérivées).
- **FR-007** : Endpoint `GET /admin/intermediaires/{id}/fonds` → réciproque.
- **FR-008** : Page admin `/admin/fonds/[id]/comparator` → tableau comparatif aligné de toutes les Offres dérivées (critères, frais, délais, track-record).
- **FR-009** : Endpoint `GET /admin/offres?fonds=&intermediaire=&pays=&secteur=&status=` paginé, accessible aussi côté lecture publique pour la PME (sans `status=draft`) — sera consommé par F25.
- **FR-010** : Job ou hook de cohérence : à chaque save d'un Fonds ou d'un Intermédiaire `published`, marquer les Offres dérivées avec un badge `needs_refresh` si l'intersection critères/documents change. L'admin clique "Actualiser" pour propager.

## Exigences non-fonctionnelles

- **NFR-001** : Le calcul `effective` doit être déterministe et testé sur 5 cas d'école (GCF×BOAD, GCF×UNDP, FEM×PNUD, SUNREF×Ecobank, FNE-CI×banque locale).
- **NFR-002** : Toutes les opérations sont auditées (F04). Les accréditations sont versionnées (F04).
- **NFR-003** : Pas plus de 100 fonds, 200 intermédiaires, 500 offres en MVP. Mais l'archi doit pouvoir scaler à 10x.

## Entités clés

- **FondsSource** (FR-001).
- **Intermediaire** (FR-002).
- **Accreditation** (FR-003).
- **Offre** (FR-004).
- **CritereEffectif** / **DocumentEffectif** : calculés en vue, pas de tables dédiées.

## Success Criteria

- **SC-001** : Un admin saisit un Fonds + un Intermédiaire + une Accréditation + une Offre en < 30 minutes au total.
- **SC-002** : Le calcul `/admin/offres/{id}/effective` donne le bon résultat sur les 5 cas d'école (suite de tests).
- **SC-003** : Le comparateur affiche correctement 3 Offres dérivées d'un même Fonds.
- **SC-004** : Une Offre sans accréditation active passe en `outdated` (testé par cron ou lazy check).

## Hors-scope MVP

- Marketplace public d'offres (la liste reste interne à la plateforme PME en MVP).
- Notifications automatiques quand une nouvelle Offre matche un Projet existant — F25 (Matching) le fera.
- Import CSV en masse de fonds/intermédiaires (post-MVP utile, pas critique).
- Statistiques de track-record agrégées (taux de succès) — saisie manuelle en MVP, pas de calcul automatique.

## Risques et points de vigilance

- **Complexité du calcul effective** : un référentiel d'intermédiaire peut être un sous-ensemble ou une extension du référentiel du fonds. Modéliser ça proprement = clé. Recommandation : `effective` retourne un arbre à 2 niveaux (`fonds_layer`, `intermediaire_layer`) plutôt qu'une fusion plate, pour que F23 puisse calculer 2 scores distincts (cohérence brainstorming Module 2.3.3).
- **Données réelles à saisir** : taxonomie BOAD, GCF, IFC PS = saisie manuelle longue. Prévoir 1 sprint dédié pour peupler.
- **Versions concurrentes** : si Fonds passe en v2, les Offres dérivées doivent gérer la transition. Recommandation : Offre v1 reste liée à Fonds v1 jusqu'à action explicite admin.
- **`accepted_languages`** : par défaut `['fr']`. F26 vérifiera que la langue de génération est dans cette liste.
