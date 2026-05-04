# Index des Features ESG Mefali — Découpage Spec-Kit

> **Source** : [`fonctionnalites_brainstorming.md`](../fonctionnalites_brainstorming.md) (1029 lignes, 11 modules + transversaux).
>
> **Objectif** : implémenter progressivement la plateforme via Spec-Kit (`/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`).
>
> **Mode d'emploi** : chaque fiche `NN-...md` est une **description en langage naturel** prête à être passée comme `$ARGUMENTS` à `/speckit.specify`. Démarrer une feature uniquement quand toutes ses dépendances sont en `published`.

---

## Stack technique imposée par le brainstorming

| Couche | Choix |
|---|---|
| Frontend | Nuxt 4 + Composition API + Pinia + TailwindCSS v4 + chart.js + mermaid + Leaflet + gsap + driver.js + fontawesome + toast-ui/editor |
| Orchestration LLM front | LangGraph (LangChain en utilitaire) |
| Backend | FastAPI (Python) |
| LLM | minimax-m2.7 via OpenRouter (interchangeable via `LLM_BASE_URL` + `LLM_MODEL`) |
| Embeddings | **Voyage AI** (`voyage-3.5`, 1024 dimensions, multilingue performant pour le français) — clé `VOYAGE_API_KEY` |
| Speech-to-Text | **Replicate** (Whisper) — clé `REPLICATE_API_TOKEN` (pour audio dans F22) |
| BDD | PostgreSQL + pgvector + Row-Level Security |
| Stockage docs | Local (MinIO/S3 plus tard) |
| File d'attente | Synchrone MVP (Redis + Celery plus tard) |
| Hébergement | Europe ou Afrique de l'Ouest — **pas USA** (RGPD/UEMOA/Côte d'Ivoire 2013-450) |

### Conventions d'environnement local (à respecter par toutes les features)

- **Backend FastAPI** : exécuté localement via un environnement virtuel Python `.venv` (créé à la racine du dossier backend, géré par `pip` ou `uv`). Pas de containerisation du backend en dev.
- **PostgreSQL + pgvector** : **seul** service dockerisé. Compose file unique exposant le port 5432, volume nommé pour la persistance, image `pgvector/pgvector:pg16` (ou équivalent récent).
- **Frontend Nuxt 4** : exécuté localement via `pnpm dev` (ou équivalent), pas de container en dev.
- **Variables d'environnement** : centralisées dans `backend/.env` (ignoré par git) avec un `backend/.env.example` versionné. Frontend Nuxt utilise `.env` à la racine front. Le `docker-compose.yml` lit éventuellement `backend/.env` pour les credentials Postgres mais reste indépendant.
- **Migrations** : Alembic côté backend (le `.venv` du backend exécute les migrations contre la base dockerisée).

---

## Phasage en 12 phases / 35 features

### Phase 0 — Fondations transversales (5 features)
Aucune feature métier ne peut s'en affranchir. À implémenter en premier, dans l'ordre.

| # | Feature | Modules brainstorm | Dépend de |
|---|---|---|---|
| 01 | Initialisation stack & modèle multi-tenant | Architecture technique, 0.7 | — |
| 02 | Authentification & rôles PME/Admin (RLS) | 0.2 | 01 |
| 03 | Entité Source & sourçage anti-hallucination | 0.1 | 01, 02 | _ready_for_implement → **livré**_
| 04 | Audit log append-only & versioning | 0.4, 0.5 | 01, 02 |
| 05 | Conformité données personnelles & consentements | 0.3, 0.6 | 02, 04 |

### Phase 1 — Back-office Admin & Catalogue (5 features)
Sans le catalogue, la plateforme est vide. Ces features peuplent les Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs.

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 06 | Squelette back-office admin & workflow draft→published | 9.1 (général) | 02, 03 |
| 07 | Gestion des Sources (saisie, vérification, impact analysis) | 9.2 | 03, 06 |
| 08 | Catalogue Fonds, Intermédiaires, Offres | 3.1, 9.1 | 04, 06, 07 |
| 09 | Catalogue Référentiels, Indicateurs, Critères, Documents requis, Facteurs d'émission | 0.7, 9.1 | 04, 06, 07 |
| 10 | Support PME admin & métriques admin | 9.3, 9.4 | 02, 04, 06 |

### Phase 2 — Profil PME (2 features)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 11 | Profil → Entreprise (édition manuelle + sync LLM) | 1.2 | 02, 04 |
| 12 | Profil → Projets (CRUD, duplication, statuts, documents projet) | 1.3 | 02, 04, 11 |

### Phase 3 — Chat & LLM Tool-Use (6 features)
Le cœur conversationnel. Module 10 (fiabilité tool-use) est traité en premier pour que tout le reste s'y appuie.

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 13 | Interface chat multimodale & contexte de page | 1.1 (vue UI), réactivité | 02, 04 |
| 14 | LangGraph routing & validation Pydantic + retry | 10.1, 10.2, 10.3, 10.5 | 13 |
| 15 | Tools de réponse en bottom sheet (ask_*, show_form, summary_card) | 1.1.1 | 13, 14 |
| 16 | Tools de visualisation inline (show_kpi/radar/bar/line/pie/timeline/comparison/match/map/mermaid) | 1.1.2 | 13, 14 |
| 17 | Tools de mutation LLM (CRUD profil, projets, candidatures, attestations, scores) | 1.1.3 | 04, 11, 12, 14, 15 |
| 18 | Mémoire contextuelle (15 derniers msgs + RAG pgvector + recall_history) | 1.4 | 13, 14 |

### Phase 4 — Skills (Playbooks Métier) (3 features)
Couche orchestration au-dessus des tools.

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 19 | Moteur de Skills (loader, fusion prompt, injection sources, intégration LangGraph) | 11.1, 11.3, 11.5 | 03, 06, 14 |
| 20 | CRUD Skills back-office (workflow draft→published, anti-injection, eval gating) | 11.2, 11.3, 11.4 | 06, 19 |
| 21 | Seed des skills MVP (esg_diagnostic, score_gcf, dossier_gcf_via_boad + 5-6 additionnelles) | 11.7 | 08, 09, 19, 20 |

### Phase 5 — Conformité ESG (Module 2) (3 features)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 22 | Upload & OCR de documents (PDF, images, Word, Excel, FR/EN) + extraction LLM | 2.1 | 11, 12, 13, 17 |
| 23 | Scoring ESG multi-référentiels (Mefali + UEMOA/GCF/IFC/GRI/ODD + intermédiaires) | 2.2, 2.3 | 09, 21, 22 |
| 24 | Rapport de conformité PDF (multi-référentiels + radar + lacunes + annexe sources) | 2.4 | 23 |

### Phase 6 — Conseiller Financement (Module 3) (3 features)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 25 | Matching Projet ↔ Offre (double score fonds+intermédiaire, comparateur, alertes) | 3.2 | 12, 23 |
| 26 | Générateur de dossiers de candidature (via Skills, multilingue FR/EN, multi-offres) | 3.3 | 21, 25 |
| 27 | Simulateur de financement (coût total réel, ROI vert, comparateur) | 3.4 | 25 |

### Phase 7 — Empreinte Carbone (Module 4) (1 feature)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 28 | Calculateur d'empreinte carbone (questionnaire + calcul + facteurs sourcés ADEME/IPCC + plan réduction) | 4.1, 4.2, 4.3 | 09, 11, 15, 16 |

### Phase 8 — Scoring Crédit Vert (Module 5) (2 features)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 29 | Collecte données (Mobile Money, déclaratif, photos, publiques) & algorithme hybride sourcé | 5.1, 5.2 | 05, 11, 12, 21 |
| 30 | Attestation vérifiable (PDF + signature Ed25519 + QR + page publique + révocation) | 5.3 | 23, 29 |

### Phase 9 — Plan d'Action (Module 6) (1 feature)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 31 | Plan d'action, rappels cron, bibliothèque & fiches intermédiaires | 6.1, 6.2, 6.3 | 12, 23, 25 |

### Phase 10 — Tableau de Bord PME (Module 7) (1 feature)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 32 | Dashboard PME (scores, candidatures, rapports, audit log, Mes données, multi-utilisateurs) | 7.1, 7.2, 7.3 | 04, 05, 23, 24, 25, 30 |

### Phase 11 — Extension Chrome (Module 8) (2 features)

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 33 | Extension Chrome — détection sites, observation SPA, pré-remplissage, i18n | 8.1, 8.2, 8.7 | 11, 12, 25 |
| 34 | Extension Chrome — guidage, suivi candidatures, notifications, recommandations | 8.3, 8.4, 8.5, 8.6 | 25, 26, 33 |

### Phase 12 — Eval LLM Continue (1 feature)
À démarrer dès qu'il y a du tool-use réel à évaluer (en parallèle de la Phase 3-4).

| # | Feature | Modules | Dépend de |
|---|---|---|---|
| 35 | Golden set 50-100 cas + CI eval + post-processeur (chips, bandeau non sourcé) + traçabilité | 10.4, 10.6, 10.7, 10.8 | 14 (au moins) |

---

## Graphe de dépendances simplifié

```
Phase 0 (01→02→03→04→05)
        ↓
Phase 1 (06 → 07 → {08, 09} → 10)
        ↓
Phase 2 (11 → 12)
        ↓
Phase 3 (13 → 14 → {15, 16, 18} → 17)
        ↓
Phase 4 (19 → 20 → 21)
        ↓
┌───────┴────────┬────────────┬────────────┐
Phase 5         Phase 6     Phase 7      Phase 8
(22→23→24)     (25→{26,27}) (28)       (29→30)
        ↓
Phase 9 (31), Phase 10 (32), Phase 11 (33→34)

Phase 12 (35) — démarrable dès la Phase 3
```

---

## Conventions transverses (rappel — à appliquer dans CHAQUE feature)

Ces invariants viennent du Module 0 du brainstorming et doivent être respectés sans exception :

1. **Sourçage obligatoire** (Module 0.1) : tout chiffre, critère, formule, seuil, facteur d'émission, document requis affiché à l'utilisateur ou produit par le LLM doit pointer vers une `Source` `verified`. Sinon le LLM doit utiliser `flag_unsourced` ou refuser. Validation backend stricte rejetant les payloads non sourcés.
2. **Multi-tenant strict** (Module 0.2) : `account_id` sur chaque table métier + RLS PostgreSQL. Aucune feature ne contourne l'isolation.
3. **Audit log** (Module 0.4) : toute mutation (manuelle, LLM, import) journalisée avec `source_of_change`.
4. **Versioning** (Module 0.5) : référentiels et critères versionnés ; candidatures stockent un snapshot JSON immuable.
5. **Money typé** (Module 0.6) : `{amount, currency}`. FCFA-EUR peg fixe 655,957. USD via API. Devise PME + devise fonds en parallèle.
6. **Mapping ESG cohérent** (Module 0.7) : la couche `Indicateur` est le pivot. Une seule réponse PME alimente plusieurs scores sans duplication.
7. **Plateforme fermée aux intermédiaires** : seuls les rôles `PME` et `Admin` existent ; les intermédiaires reçoivent des dossiers et attestations vérifiables hors-plateforme.
8. **Édition manuelle disponible** : tout champ alimenté par le LLM doit être consultable et modifiable manuellement par l'utilisateur, avec sync bidirectionnelle vers le contexte LLM.
9. **Tool-use fiable** (Module 10) : descriptions auto-descriptives, schémas Pydantic stricts, ≤ 5–10 tools concurrents par tour, validation + retry, eval gating.
10. **UI bottom sheet** (Module 1.1.1) : les composants interactifs vivent à la place de l'input (bas), jamais inline dans la bulle LLM (haut). Bascule "Répondre librement" toujours présente.

---

## Ordre d'attaque recommandé

**Sprint 1 (Fondations + Catalogue de base)** : 01 → 02 → 03 → 04 → 05 → 06 → 07
**Sprint 2 (Catalogue complet + Profil)** : 08 → 09 → 10 → 11 → 12
**Sprint 3 (Chat + Tool-use)** : 13 → 14 → 15 → 16 → 18 → 17 (commencer 35 en parallèle)
**Sprint 4 (Skills)** : 19 → 20 → 21
**Sprint 5 (ESG)** : 22 → 23 → 24
**Sprint 6 (Financement + Carbone)** : 25 → 26 → 27 (// 28)
**Sprint 7 (Crédit vert + Plan)** : 29 → 30 (// 31)
**Sprint 8 (Dashboard + Extension)** : 32 (// 33 → 34)

---

## Phase UI MVP (frontend Nuxt) — features 36 → 52

Le backend des features 01-35 livre l'API mais **le frontend Nuxt est resté volontairement à l'état de squelette d'auth** (login/register/reset). Toutes les pages produit sont marquées DEFERRED dans les `manual-tests-XX.md`. Cette phase reprend chaque "scope UI DEFERRED" et le découpe en sous-features livrables, en commençant par les fondations design transverses.

### Phase A — Fondations design (préalable à tout)
- **F36** Design System & Tokens (palette, typo, spacing, motion, dark mode strategy) — _in-implementation_, voir [specs/036-design-system-tokens/](../../specs/036-design-system-tokens/)
- **F37** UI Primitives Library (~27 atomes : Button, Input, Modal, Toast, Card, etc.) — _done_ (2026-05-03), voir [specs/037-ui-primitives/](../../specs/037-ui-primitives/)
- **F38** App Shell, Layout & Navigation (sidebar, header, layouts, middlewares route) — _done_ (2026-05-03), voir [specs/038-app-shell-navigation/](../../specs/038-app-shell-navigation/)

### Phase B — Briques transversales LLM/chat
- **F39** Bottom Sheet Engine — UI de F15 (`ask_*`, `show_form`, `show_summary_card`)
- **F40** Visualization Library — UI de F16 (KPI, charts, mermaid, table, map)
- **F41** Chat Conversational Layer — UI de F12/F13/F14/F18 (shell, bubbles, EventBus, langgraph)

### Phase C — Onboarding & profil
- **F42** Onboarding Tour & Auth UX Polish (driver.js, register multi-étapes, password strength)
- **F43** Profile Entreprise & Projets UI — UI de F11 + F12-profile-projets

### Phase D — Tableaux de bord & visualisations métier
- **F44** Dashboard PME — UI de F32 (cartes scores, carbone, crédit, candidatures, plan, attestations) — `ready` (specs/044-dashboard-pme-ui/)
- **F45** Plan d'action ESG UI — UI de F31 (timeline horizontal, cards étapes, drawer édition) — _US11 (historique versions) reportée : nécessite endpoint backend `GET /me/action-plan/versions` non livré par F31 ; US12 (export PDF) reportée derrière flag `NUXT_PUBLIC_FEATURE_PLAN_EXPORT_PDF` jusqu'à livraison F51._
- **F46** Scoring ESG visualisations — UI de F23 (radar, drilldown, multi-référentiels)
- **F47** Empreinte carbone UI — UI de F28 (Scope 1/2/3 donut, drilldown, comparateur facteurs) — `done` (specs/047-empreinte-carbone-ui/) — _US7 (sync chat) couverte par useCarbon ; US8 (comparateur IPCC) désactivée MVP ; US9 (export PDF) délégation derrière F51._
- **F48** Credit scoring UI — UI de F29 (gauge, sub-scores, badges éligibilité, recos)

### Phase E — Documents, rapports, attestations
- **F49** Rapports PDF + Page publique `/verify/{id}` — UI de F24 + F30
- **F50** Documents upload + OCR viewer UI — UI de F22

### Phase F — Matching, candidatures, simulateur
- **F51** Matching offres + Wizard candidature + Simulateur — UI de F25/F26/F27

### Phase G — Notifications & extension panneau
- **F52** Notifications + Settings + Exports + Extension side panel — UI de F34/F05/F32-export

### Sprint UI recommandé

- **Sprint UI-1 (Fondations)** : 36 → 37 → 38
- **Sprint UI-2 (Briques chat/LLM)** : 39 → 40 → 41
- **Sprint UI-3 (Onboarding + profil)** : 42 → 43
- **Sprint UI-4 (Dashboards & viz métier)** : 44 → 45 → 46 → 47 → 48
- **Sprint UI-5 (Documents & rapports)** : 49 → 50
- **Sprint UI-6 (Financement & flux complexes)** : 51
- **Sprint UI-7 (Périphérie)** : 52

**Important** : F36–F38 sont **bloquantes** pour tout le reste. Ne pas les paralléliser avec F39+. Les phases D–G peuvent être largement parallélisées une fois la phase B livrée.

---

## Lancer une feature avec Spec-Kit

```bash
# 1. Créer la branche feature (hook spec-kit)
# 2. Lancer la spec
/speckit.specify "$(cat docs_et_brouillons/features/01-foundations-stack-init.md)"

# 3. Itérer
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```

Le contenu de chaque fiche est rédigé pour que **`/speckit.specify` n'ait pas à inventer le périmètre** : User Stories prioritisées P1/P2/P3, exigences fonctionnelles testables, entités clés, hors-scope explicite.
