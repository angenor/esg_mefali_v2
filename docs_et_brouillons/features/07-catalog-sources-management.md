# F07 — Gestion des Sources (CRUD, Vérification, Impact Analysis)

**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 9.2 (Gestion des Sources)
**Dépendances** : F03, F06
**Estimation** : 1.5–2 jours

## Contexte et objectif

F03 a posé l'entité Source au niveau DB et les tools LLM. F06 a posé le squelette back-office. F07 livre **l'expérience admin complète** pour saisir, vérifier et maintenir la base de Sources qui alimente tout le sourçage anti-hallucination.

C'est la **première feature opérationnelle** de la plateforme : sans Sources, rien ne peut être `published` ni utilisé par le LLM. L'équipe ESG Mefali doit pouvoir saisir 50–100 sources de référence (taxonomie UEMOA, critères GCF, IFC PS, politiques BOAD, ADEME Base Carbone, etc.) avant d'aller plus loin.

## User Stories

### US1 — Saisir une nouvelle Source (P1)
**En tant qu'**admin,
**je veux** un formulaire de création de Source avec tous les champs (`url`, `title`, `publisher`, `version`, `date_publi`, `page`, `section`, `notes`),
**afin de** enregistrer la source officielle d'un critère, d'une formule ou d'un facteur d'émission.

**Test indépendant** : POST `/admin/sources/` avec un payload valide → la source est créée en `verification_status='pending'`, le créateur est enregistré (`captured_by`).

**Scénarios** :
1. URL fournie → un fetch HEAD vérifie qu'elle répond (warning si 4xx/5xx mais pas blocant).
2. Source dupliquée (même URL + même page) → le formulaire propose de réutiliser l'existante.
3. URL d'archive Wayback (post-MVP) optionnellement complétée.

### US2 — Workflow de double vérification (P1)
**En tant qu'**admin,
**je veux** qu'une source ne passe en `verified` que lorsqu'**un autre admin** que le créateur l'a relue et validée,
**afin de** garantir une double lecture sur tout ce qui sourcera des chiffres officiels.

**Scénarios** :
1. Admin A crée la source → statut `pending`, ne peut pas la valider lui-même (bouton "Valider" désactivé pour A).
2. Admin B ouvre, vérifie l'URL, le titre, la version, clique "Valider" → statut `verified`, `verified_by=B`.
3. Une source `pending` peut être supprimée par n'importe quel admin tant qu'elle n'est référencée par aucun objet (cohérence F03 FK).
4. Une source `verified` peut être marquée `outdated` (mais pas supprimée tant que des objets `published` la référencent).

### US3 — Liste filtrable et recherche (P1)
**En tant qu'**admin,
**je veux** une liste de toutes les sources avec filtres (statut, publisher, date capture, créateur) et recherche full-text (titre + publisher + notes),
**afin de** retrouver rapidement une source ou identifier les `pending`.

### US4 — Impact analysis avant modification ou suppression (P1)
**En tant qu'**admin,
**je veux** qu'avant de modifier ou marquer `outdated` une source, le système me liste **tous** les objets du catalogue qui en dépendent (Indicateurs, Critères, Formules, Facteurs d'émission, Documents, Référentiels, Skills),
**afin de** mesurer l'impact métier d'un changement.

**Scénarios** :
1. Admin clique "Impact" sur une source GCF criteria → liste : 8 critères, 1 référentiel, 2 skills, 12 candidatures référençant le snapshot.
2. Si la source est marquée `outdated`, les objets `published` qui la référencent passent automatiquement en statut `outdated` (ou conservent `published` mais affichent un badge "source obsolète" — choix à clarifier ; recommandation : badge plutôt que cascade brutale, pour ne pas casser les candidatures en cours).

### US5 — Page publique de lecture d'une Source (P2)
**En tant que** PME ou auditeur,
**je veux** pouvoir cliquer sur le picto Source (de F03 `<SourceCite>`) et arriver sur une page lisible affichant URL deep-linkée, titre, publisher, version, date capture, statut,
**afin de** vérifier moi-même la source.

**Test indépendant** : GET `/sources/{id}` (route Nuxt publique) rend une page sobre. Cohérent avec F03 FR-004.

### US6 — Vue admin "sources non sourçables détectées par le LLM" (P3)
**En tant qu'**admin,
**je veux** voir une page qui agrège les `flag_unsourced` (F03) avec compteur,
**afin de** prioriser quelles nouvelles sources ajouter au catalogue.

## Exigences fonctionnelles

- **FR-001** : CRUD complet `/admin/sources` (list, create, read, update, mark-outdated, soft-delete-if-orphan).
- **FR-002** : Endpoint `POST /admin/sources/{id}/verify` (POST sans body) → vérifie `verified_by != captured_by`, passe `verification_status='verified'`, audit log.
- **FR-003** : Endpoint `POST /admin/sources/{id}/mark-outdated` → passe `outdated`, audit log, déclenche le badge "source obsolète" sur les objets dépendants (sans cascade automatique sur leur statut).
- **FR-004** : Endpoint `GET /admin/sources/{id}/impact` → renvoie `{indicateurs: [...], criteres: [...], formules: [...], facteurs_emission: [...], documents_requis: [...], referentiels: [...], skills: [...], candidatures: [...]}`.
- **FR-005** : Recherche full-text Postgres `tsvector` sur `title || ' ' || publisher || ' ' || coalesce(notes,'')`. Index GIN.
- **FR-006** : Filtres listes : statut multi-select, publisher autocomplete, date range, capté par moi.
- **FR-007** : Le formulaire admin tente un `HEAD` HTTP au save (avec timeout 5s) et affiche un warning si non 2xx, mais ne bloque pas le save.
- **FR-008** : Détection de doublon : recherche `WHERE url = ?` au save → si trouvé, propose la fusion (UI : "Une source identique existe — réutiliser ?").
- **FR-009** : Page publique `/sources/{id}` (route Nuxt sans auth) — read-only, mêmes données que F03 FR-004 + lien "Voir le document officiel".
- **FR-010** : Page `/admin/unsourced-claims` listant les `flag_unsourced` (F03 FR-009) groupés par claim avec compteur, lien "Créer une nouvelle source à partir de ce claim".

## Exigences non-fonctionnelles

- **NFR-001** : Tableau des sources : pagination 25/50/100, tri par toutes les colonnes principales, lazy load images (favicon publisher si dispo).
- **NFR-002** : Endpoint `impact` doit répondre en < 500ms même si la source est référencée par 1000+ objets (utiliser des compteurs agrégés et lazy expansion).
- **NFR-003** : La double-validation est strictement appliquée : impossible de bypass via API (vérification serveur).
- **NFR-004** : Une fois `verified`, modifier les champs critiques (`url`, `version`, `publisher`) **incrémente la version** de la source (F04). Les champs accessoires (`notes`) peuvent être édités sans nouvelle version.

## Entités clés

- Aucune nouvelle table (table `source` posée en F03).
- Versionning de la `Source` activé via le mécanisme de F04.

## Success Criteria

- **SC-001** : 50 sources de référence saisies par l'équipe en 1 jour de travail (UX rapide).
- **SC-002** : 100% des sources ayant statut `verified` ont `verified_by != captured_by`.
- **SC-003** : Cliquer "Impact" sur n'importe quelle source retourne une réponse cohérente (vérifié sur 5 cas test).
- **SC-004** : La page publique `/sources/{id}` est accessible sans login et indexable par moteurs de recherche (sitemap.xml, post-MVP).
- **SC-005** : Le tableau des sources se charge en < 1 seconde pour 5000 sources (mesuré).

## Hors-scope MVP (post-MVP, cohérent F03)

- `archived_url` (snapshot Wayback automatique).
- `hash_contenu` et cron de revalidation périodique.
- Scraper automatique de sites officiels (GCF, BOAD, ADEME).
- Workflow communautaire (consultants externes proposent des sources).
- Import en masse (CSV) — utile mais pas critique en MVP.

## Risques et points de vigilance

- **Cascade outdated** : ne PAS faire de cascade automatique sur les objets dépendants (briserait les candidatures en cours). Préférer un badge "source obsolète à vérifier" + tâche admin pour réviser.
- **Double validation forte** : si l'équipe ESG Mefali a 1 ou 2 admins seulement, prévoir un mode "auto-validation par un admin différent" pour ne pas bloquer. À clarifier en `/speckit.clarify`.
- **Saisie en masse au début** : 50–100 sources à entrer = travail manuel important. Prévoir un import CSV minimaliste comme post-MVP fast-track, voire en MVP si l'équipe en a besoin (à décider).
- **URL canonicalisation** : `https://gcf.org/policies` vs `https://www.gcf.org/policies/` → considérés identiques ou différents ? Trancher en clarify (recommandation : normaliser au save : protocole, slash final, paramètres de tracking retirés).
