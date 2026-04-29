# F34 — Extension Chrome — Panneau de Guidage, Suivi Candidatures, Notifications, Recommandations

**Phase** : 11 — Extension Chrome (Module 8)
**Modules brainstorm** : 8.3 (Panneau Latéral de Guidage), 8.4 (Suivi des Candidatures), 8.5 (Notifications et Rappels), 8.6 (Recommandations d'Offres)
**Dépendances** : F25, F26, F33
**Estimation** : 3 jours

## Contexte et objectif

Cette feature complète la valeur de l'extension Chrome livrée en F33 :
- **Panneau latéral de guidage** spécifique à l'**Offre** (couple Fonds × Intermédiaire), pas seulement au fonds — barre de progression, navigateur d'étapes, aide par champ, mini-chat IA contextuel.
- **Suivi des candidatures** : création automatique au détecter une Offre, sauvegarde de progression entre sessions, statut, mise à jour manuelle ou via LLM.
- **Notifications et rappels** : alertes échéances (J-30, J-7, J-1), candidatures inactives, déduplication, cycle 6h.
- **Recommandations d'Offres** dans le contexte de navigation (cohérent F25).

## User Stories

### US1 — Panneau latéral de guidage (P1)
**En tant que** PME sur un portail détecté,
**je veux** un panneau latéral (slide-in droite, fermable) qui :
- présente le guide pas-à-pas spécifique à **cette Offre** (couple Fonds × Intermédiaire),
- affiche une **barre de progression** (étape X / N),
- liste les **étapes** (cliquables, navigables),
- pour chaque étape, propose une **aide par champ** (info-bulles avec sources),
- intègre un **mini-chat IA** contextuel pour poser des questions en temps réel.

**afin de** ne pas se perdre.

**Test indépendant** : sur portail BOAD avec Offre GCF×BOAD détectée → panneau s'ouvre avec 8 étapes spécifiques à cette Offre.

### US2 — Mini-chat IA contextuel (P1)
**En tant que** PME,
**je veux** dans le panneau, un mini-chat où je peux poser des questions ("que mettre dans ce champ ?", "quelle longueur attendue ?"),
**afin de** un coach embarqué.

**Mécanisme** : réutilise les endpoints chat (F13) avec contexte enrichi (Offre détectée, champ courant si focus). Skill `skill_dossier_<offre>` (F21) chargée.

### US3 — Checklist documentaire (P1)
**En tant que** PME,
**je veux** dans le panneau, voir la checklist des documents requis (union fonds + intermédiaire, cohérent F08, F26) avec :
- ✓ uploadé sur ESG Mefali,
- ○ manquant — bouton "Uploader" qui pointe vers F22.

**afin de** ne rien oublier.

### US4 — Création automatique d'une candidature (P1)
**En tant que** PME,
**je veux** que lorsque je commence à remplir un formulaire d'Offre détectée, une **candidature** soit automatiquement créée en statut `brouillon` (ou réutilisée si existe déjà pour ce projet+offre),
**afin de** que ma progression soit sauvegardée.

**Scénarios** :
1. Première navigation sur formulaire → bandeau "Voulez-vous lier cela à un projet ?" → choix projet → candidature créée.
2. Reprise plus tard → progression rechargée.

### US5 — Sauvegarde de progression entre sessions (P1)
**En tant que** PME,
**je veux** que les valeurs saisies dans les champs soient sauvegardées (côté extension stockage local + backend periodic sync) — récupérables si je reviens sur le portail le lendemain,
**afin de** ne pas tout perdre si je suis interrompue.

### US6 — Tableau de bord candidatures dans la popup (P1)
**En tant que** PME,
**je veux** dans le popup de l'extension, voir mes candidatures en cours :
- nom Offre,
- progression (% des étapes),
- prochaine échéance,
- statut chez l'intermédiaire (déclaratif).

**afin de** savoir où j'en suis sans aller sur la plateforme.

### US7 — Mise à jour du statut candidature (P1)
**En tant que** PME,
**je veux** mettre à jour le statut de ma candidature (acceptée / refusée / en instruction) :
- manuellement via dropdown,
- ou via instruction au LLM ("ma candidature BOAD est acceptée") qui invoque `update_candidature_status` (F17).

**Pas d'email parsing en MVP** (cohérent brainstorming Module 8.4).

### US8 — Alertes échéances (P1)
**En tant que** PME,
**je veux** des notifications navigateur (Chrome notifications API) :
- J-30, J-7, J-1 avant deadline d'une Offre `call_for_proposals` (cohérent F31),
- 3+ jours d'inactivité sur une candidature en cours.

**afin de** être alertée même hors-portail.

### US9 — Déduplication intelligente (P2)
**En tant que** PME,
**je veux** ne pas recevoir 5 fois la même alerte (J-30 affiché → ne plus afficher pendant 24h),
**afin de** non-pollution.

### US10 — Cycle de vérification 6h (P2)
**En tant que** dev,
**je veux** que l'extension vérifie les échéances et candidatures inactives toutes les 6h (alarms API Chrome),
**afin de** rester à jour.

### US11 — Recommandations d'Offres compatibles (P1)
**En tant que** PME naviguant sur un site fonds (ex : gcf.org),
**je veux** que le panneau propose **plusieurs Offres dérivées** (GCF via BOAD, GCF via PNUD, GCF via Acumen…) avec scores de compatibilité décomposés (cohérent F25),
**afin de** choisir le meilleur intermédiaire.

### US12 — Comparaison côte-à-côte d'Offres (P2)
**En tant que** PME,
**je veux** dans l'extension, ouvrir un modal qui aligne 3 Offres sur leurs critères/délais/frais (cohérent F25 US4),
**afin de** trancher.

### US13 — Accès direct au site de l'intermédiaire (P2)
**En tant que** PME,
**je veux** un bouton "Aller sur le portail intermédiaire" depuis l'extension, pas vers le fonds source nu,
**afin de** ne pas perdre de temps sur un site qui ne décaisse pas.

## Exigences fonctionnelles

- **FR-001** : `panel.html` (et JS associé) : panneau slide-in à droite, fermable. Affiche guide étapes (consomme F26 template structure), checklist docs (consomme F08), mini-chat (consomme F13).
- **FR-002** : Endpoints :
  - `GET /extension/offres-recommandees?url=` → liste Offres compatibles selon URL détectée.
  - `GET /extension/candidatures` → liste candidatures actives + progression.
  - `PATCH /extension/candidatures/{id}/progress` body `{form_data, current_step}` → sauvegarde de progression.
  - `PATCH /extension/candidatures/{id}/status` (cohérent F25).
- **FR-003** : Création automatique candidature : popup "Lier à un projet" si formulaire détecté → POST sur `/me/candidatures` (cohérent F25).
- **FR-004** : Persistance form_data : côté extension `chrome.storage.local` + sync backend toutes les 30s (debounce).
- **FR-005** : Notifications via `chrome.notifications.create` ; ID des notifs = `{kind, candidature_id}` pour déduplication.
- **FR-006** : `chrome.alarms.create` pour cycle 6h.
- **FR-007** : Mini-chat panel utilise `<ChatFloating>` simplifié ou un widget dédié léger qui appelle les endpoints F13.
- **FR-008** : Affichage des recommandations d'Offres dans le panneau sous forme de cards (réutilise `<ShowMatchCard>` adapté ou simplifié).
- **FR-009** : Liens directs vers le portail intermédiaire (champ `intermediaire.portail_url` de F08).
- **FR-010** : Comparateur popup : appelle `/me/fonds/{fonds_id}/intermediaires-comparator` (cohérent F25 FR-003).

## Exigences non-fonctionnelles

- **NFR-001** : Panneau latéral n'écrase pas le contenu du portail (overlay positionné fixé).
- **NFR-002** : Notifications respectent les préférences utilisateur (toggle dans popup extension).
- **NFR-003** : Sync de progression résiliente (offline → retry quand online).
- **NFR-004** : Mini-chat IA répond en < 3s (avec streaming si possible).

## Entités clés

- `Candidature.progression_form_data_json` (extension du schéma) — stockage de l'état de remplissage.
- Pas de nouvelles tables majeures.

## Success Criteria

- **SC-001** : Sur portail BOAD avec formulaire GCF→BOAD → panneau s'ouvre avec 8 étapes + checklist docs.
- **SC-002** : Mini-chat IA répond à "quelle longueur pour cette section ?" avec contexte adapté.
- **SC-003** : Reprendre la candidature 24h plus tard → form_data restauré.
- **SC-004** : Notification J-7 reçue 7 jours avant deadline.
- **SC-005** : Recommandations 3 Offres GCF×intermédiaires affichées avec scores.

## Hors-scope MVP

- Email parsing OAuth Gmail/Outlook pour mise à jour statut auto (post-MVP backlog).
- Génération de dossier complet directement depuis l'extension (post-MVP — pour l'instant, génération sur la plateforme F26).
- Synchronisation deux-sens portail ↔ ESG Mefali (post-MVP — pour l'instant : sens unique ESG → portail).
- Mode offline complet (post-MVP).

## Risques et points de vigilance

- **Persistance forme** : si la PME passe d'un onglet à l'autre, l'état doit suivre. Test rigoureux.
- **Notifications spam** : limiter strictement la fréquence + permettre désactivation par type.
- **Mini-chat token consommation** : un mini-chat dans l'extension peut consommer des tokens à grande échelle. Limiter le nombre de tours par session, prévenir si abus (post-MVP : quota par PME).
- **Cohérence statuts** : la candidature peut être éditée à la fois sur la plateforme et via l'extension. Bien gérer la dernière modif (timestamp, idempotence).
- **Approbation extension** : chrome.tabs.onUpdated + chrome.notifications nécessitent permissions fortes — bien justifier dans la fiche Store.
