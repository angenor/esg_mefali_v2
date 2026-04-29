<!--
SYNC IMPACT REPORT — Constitution ESG Mefali
=============================================
Version change: (template, non versionné) → 1.0.0
Bump rationale: ratification initiale (MAJOR ouvert à 1.0.0). Aucune version
antérieure publiée — passage du squelette template à une constitution complète
avec 10 principes non négociables + sections contraintes/conformité/langue/
discipline + gouvernance.

Modified principles (placeholders → définitifs) :
  - [PRINCIPLE_1_NAME] → I. Sourçage anti-hallucination de bout en bout
  - [PRINCIPLE_2_NAME] → II. Multi-tenant strict (Row-Level Security)
  - [PRINCIPLE_3_NAME] → III. Audit log append-only
  - [PRINCIPLE_4_NAME] → IV. Versioning des Référentiels & Snapshot des Candidatures
  - [PRINCIPLE_5_NAME] → V. Money typé partout
  - (nouveaux par rapport au gabarit 5-principes)
  - VI. Mapping ESG via couche Indicateur unique
  - VII. Plateforme fermée aux intermédiaires
  - VIII. Édition manuelle disponible + sync LLM bidirectionnelle
  - IX. Tool-use LLM fiable (LangGraph + Pydantic + retry)
  - X. UX bottom sheet (haut = LLM, bas = utilisateur)

Added sections :
  - Contraintes Techniques & Architecture
  - Conformité Légale & Données Personnelles
  - Langue
  - Discipline Produit & Workflow Spec-Kit
  - Governance (rempli)

Removed sections : aucune (template à 5 principes étendu à 10).

Templates requiring updates :
  - ✅ .specify/templates/plan-template.md — section "Constitution Check"
    réécrite en gates concrets P1–P10.
  - ✅ .specify/templates/spec-template.md — aucun changement requis (template
    générique compatible).
  - ✅ .specify/templates/tasks-template.md — aucun changement requis (les
    tâches principielles seront injectées par /speckit-tasks à partir des
    gates P1–P10).
  - ✅ .specify/templates/checklist-template.md — aucun changement requis.
  - ✅ CLAUDE.md — déjà délégué au plan courant ; rien à amender.

Follow-up TODOs : aucun.
-->

# ESG Mefali Constitution

> Plateforme conversationnelle IA de finance verte pour PME africaines
> francophones. Cette constitution énumère les principes **non négociables**
> qui s'appliquent à TOUTE feature future. Chaque exécution de
> `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze` DOIT vérifier la
> conformité aux principes ci-dessous avant de produire son artefact.

## Core Principles

### I. Sourçage anti-hallucination de bout en bout (NON NÉGOCIABLE)

Toute affirmation factuelle (chiffre, critère, formule, seuil, facteur
d'émission, document requis, citation réglementaire) MUST pointer vers une
entité `Source` au statut `verified`, cliquable depuis l'UI et reproduite
dans toute exportation.

Règles applicables sans exception :

- Le schéma backend MUST imposer une contrainte `NOT NULL` sur `source_id`
  pour les entités : `Indicateur`, `Critère`, `Formule`, `Seuil`,
  `Facteur d'émission`, `Document requis`, `Référentiel`.
- Le validateur de payload LLM MUST rejeter toute assertion ESG ou financière
  produite par un tool sans appel préalable à `cite_source` ; la sortie
  retourne une erreur structurée et déclenche le retry décrit en P9.
- Tout objet du catalogue reste en statut `draft` tant que ses sources ne
  sont pas vérifiées par un administrateur **distinct** du créateur
  (double-validation). Aucune publication n'est possible avec une source
  `draft`, `pending` ou `rejected`.
- Tout rapport PDF (conformité, attestation, simulateur, dossier de
  candidature) MUST inclure une annexe « Sources et références » générée
  automatiquement à partir des `source_id` mobilisés.

**Rationale** : la valeur métier de la plateforme repose sur la confiance des
PME et des fonds vis-à-vis des chiffres affichés. Une hallucination LLM non
sourcée invalide le service.

### II. Multi-tenant strict avec Row-Level Security PostgreSQL (NON NÉGOCIABLE)

Toute table métier MUST porter une colonne `account_id` (UUID, non null).
Toute table métier MUST déclarer une politique RLS PostgreSQL :

```
USING (account_id = current_setting('app.current_account_id')::uuid)
```

Règles applicables sans exception :

- Un utilisateur PME ne MUST JAMAIS voir les données d'une autre PME : un
  accès cross-tenant retourne `404 Not Found`, jamais `403 Forbidden`, afin
  de ne pas révéler l'existence de la ressource.
- Seuls deux rôles applicatifs existent : `PME` et `Admin`. Aucun rôle
  `Intermediaire` ne MUST être créé (voir P7).
- L'application MUST définir `app.current_account_id` au début de chaque
  requête authentifiée, avant tout accès aux tables métier.
- Tout schéma de table métier oubliant `account_id` ou la politique RLS
  MUST être rejeté en review.

**Rationale** : la confidentialité inter-PME est une exigence contractuelle
et réglementaire (RGPD, UEMOA 20/2010). La RLS au niveau base est la seule
défense robuste contre les bugs applicatifs.

### III. Audit log append-only (NON NÉGOCIABLE)

Toute mutation effectuée par un humain, par le LLM, par un import batch ou
par un administrateur MUST être journalisée dans une table d'audit
append-only. Chaque entrée MUST contenir :

```
{user_id, account_id, timestamp, entity_type, entity_id,
 field, old_value, new_value,
 source_of_change: 'manual' | 'llm' | 'import' | 'admin'}
```

Règles applicables sans exception :

- Au niveau Postgres, les rôles applicatifs MUST avoir `INSERT` accordé sur
  la table d'audit, et `UPDATE` / `DELETE` **révoqués**.
- Aucune feature ne MUST contourner l'audit (pas de bulk update sans trace,
  pas de tâche cron silencieuse).
- Le champ `source_of_change` MUST être renseigné et provenir de l'enum
  fermé ci-dessus, sans valeur libre.

**Rationale** : la traçabilité conditionne l'audit externe par les fonds, la
défense en cas de litige et la confiance des régulateurs.

### IV. Versioning des Référentiels & Snapshot des Candidatures (NON NÉGOCIABLE)

Les entités `Référentiel`, `Indicateur`, `Critère`, `Formule`, `Seuil`,
`Facteur d'émission`, `Template de skill` MUST porter `version`,
`valid_from`, `valid_to` et conserver l'historique complet (pas
d'écrasement).

Règles applicables sans exception :

- Toute candidature, à la soumission, MUST stocker un `snapshot_json`
  immuable contenant : projet, critères de l'offre, référentiel actif,
  indicateurs et seuils utilisés, scores calculés, sources mobilisées.
- Un score MUST être recalculable à l'identique contre son `snapshot_json`
  jusqu'à 5 ans après la soumission, sans dépendre de la version courante
  des référentiels.
- Les modifications sur une version `valid` ne MUST pas être autorisées :
  toute évolution crée une nouvelle version avec `valid_from` postérieur.

**Rationale** : un fonds peut auditer une candidature des années plus tard ;
les référentiels (GCF, IFC, BOAD…) évoluent ; la reproductibilité des
décisions est une obligation prudentielle.

### V. Money typé partout (NON NÉGOCIABLE)

Toute valeur financière (montant, seuil, frais, intérêts, taux, garantie)
MUST être typée :

```
Money = { amount: Decimal, currency: ISO 4217 }
```

Règles applicables sans exception :

- Le peg FCFA-EUR est fixe à `655,957` (sourcé via une `Source` `verified`).
  Aucune feature ne MUST coder un autre taux pour ce peg.
- USD et autres devises non peggées MUST utiliser un snapshot quotidien
  stocké en table `fx_rate`, alimenté par `exchangerate-api.com`.
- L'UI PME MUST afficher le montant en parallèle dans la devise de la PME
  (généralement FCFA) et dans la devise de l'offre de financement
  (EUR / USD).
- Le simulateur de financement MUST rendre **explicite** le risque de
  change (scénarios bas / central / haut, avec dates et taux sourcés).
- Les calculs financiers MUST utiliser `Decimal` (jamais `float`).

**Rationale** : confondre 1 EUR ≈ 656 FCFA avec 1 USD ≈ 600 FCFA produit
des erreurs invalidantes en finance verte. Le typage explicite éteint
définitivement cette classe de bugs.

### VI. Mapping ESG via couche Indicateur unique (NON NÉGOCIABLE)

La couche `Indicateur` est le **pivot atomique** du modèle ESG. Toute donnée
ESG capturée auprès d'une PME MUST être stockée comme valeur d'un
`Indicateur`, et JAMAIS dupliquée par axe E/S/G ou par référentiel.

Règles applicables sans exception :

- Un `Référentiel` est une collection d'indicateurs + seuils + poids +
  sources ; il ne MUST pas posséder ses propres réponses utilisateur.
- Un `Critère d'Offre` est une expression logique paramétrable sur des
  indicateurs (par ex. `indicator('co2_intensity').value < threshold`).
- La grille E / S / G visible dans l'UI est une **projection pédagogique**
  (vue), pas une donnée séparée. Aucune feature ne MUST persister une
  réponse PME indexée par axe E/S/G.
- Une seule réponse PME MUST alimenter simultanément les scores ESG Mefali,
  GCF, IFC, BOAD, GRI, ODD… sans nouvelle saisie.

**Rationale** : sans pivot unique, la PME doit re-saisir les mêmes données
pour chaque référentiel, ce qui détruit l'expérience produit et multiplie
les sources d'incohérence.

### VII. Plateforme fermée aux intermédiaires (NON NÉGOCIABLE)

Aucun rôle utilisateur `Intermediaire`, `Bank`, `Fund` ou équivalent ne
MUST être créé dans la plateforme. Les intermédiaires accrédités sont
modélisés exclusivement comme **entités de catalogue**, gérées en CRUD par
les administrateurs.

Règles applicables sans exception :

- La PME MUST conserver le contrôle total du partage de ses données.
- Le partage vers un intermédiaire MUST passer par une **attestation
  vérifiable** : PDF signé Ed25519 + QR code pointant vers une page publique
  read-only `/verify/{id}` (sans login).
- Aucune feature ne MUST exposer de webhook automatique ou de flux push
  vers un intermédiaire.
- Aucune route applicative ne MUST renvoyer des données PME à un acteur
  externe sur la base d'un simple identifiant fonds/banque ; toute sortie
  de données passe par une attestation explicitement émise par la PME.

**Rationale** : l'asymétrie de pouvoir entre PME et intermédiaires impose
de garder la PME maîtresse du partage. Une plateforme ouverte aux
intermédiaires deviendrait un fournisseur B2B et perdrait sa promesse.

### VIII. Édition manuelle disponible + sync LLM bidirectionnelle (NON NÉGOCIABLE)

Tout champ alimenté par le LLM MUST être consultable et modifiable
manuellement par l'utilisateur via un formulaire dédié.

Règles applicables sans exception :

- Toute mutation manuelle d'un champ MUST être immédiatement reflétée dans
  le contexte LLM (pas de cache stale, invalidation à chaque modification).
- Toute mutation produite par un tool LLM MUST être propagée à l'UI en
  temps réel via EventBus (front) ou SSE (back→front).
- Aucune feature ne MUST introduire un champ LLM-only en lecture seule, ni
  un champ manuel non visible par le LLM.
- Le statut « source de vérité » d'un champ MUST être explicitement la
  base de données (pas le contexte LLM).

**Rationale** : la confiance se construit quand l'utilisateur peut corriger
le LLM. Un champ que l'IA peut modifier mais pas l'humain inverse la
relation et casse l'autonomie de la PME.

### IX. Tool-use LLM fiable (LangGraph + Pydantic + retry) (NON NÉGOCIABLE)

L'orchestration LLM MUST suivre l'architecture suivante :

```
classifier d'intention
   → sélecteur de sous-ensemble (≤ 10 tools concurrents, jamais plus)
   → LLM avec tools filtrés
   → validation Pydantic stricte (extra='forbid', enums fermés, bornes)
   → retry max 2 avec erreur structurée
   → fallback texte si échec persistant
```

Règles applicables sans exception :

- Chaque tool MUST porter un nom verbal sans ambiguïté (`create_project`,
  `cite_source`, `compute_score_gcf`…).
- Chaque tool MUST documenter explicitement « use when » et
  « don't use when », avec au moins un exemple positif et un exemple
  négatif dans son docstring.
- Chaque tool MUST déclarer un schéma Pydantic strict (`model_config =
  ConfigDict(extra='forbid')`, enums fermés, bornes numériques).
- Un tour LLM MUST exécuter au plus 1 à 2 skills (jamais une chaîne
  arbitraire).
- Aucune skill ne MUST être publiée sans avoir passé le **eval gating**
  (golden set ≥ 50 cas, voir Discipline Produit).
- Les erreurs tool MUST être structurées et retournées au LLM pour permettre
  le retry ; le retry MUST être limité à 2 tentatives.

**Rationale** : un tool-use non contraint produit des chaînes d'appels
divergentes, des hallucinations de paramètres et une dette de fiabilité
ingérable. La discipline LangGraph + Pydantic + retry est la seule
architecture éprouvée à notre échelle.

### X. UX bottom sheet — haut = LLM, bas = utilisateur (NON NÉGOCIABLE)

Les composants interactifs de réponse (radios, checkboxes, sélecteurs,
file upload, formulaires, sliders, datepickers) ne MUST JAMAIS être rendus
**inline** dans la bulle du LLM.

Règles applicables sans exception :

- Tout composant interactif MUST vivre dans un **bottom sheet** animé
  (gsap), à la place de l'input texte.
- Un bouton « Répondre librement » MUST rester visible dans le bottom
  sheet pour basculer en saisie texte libre.
- La bulle LLM (haut) ne MUST contenir que des sorties d'affichage
  (texte, KPI, graphiques, cartes, mermaid, comparateurs, tableaux,
  liens) et aucun champ de saisie.
- Convention de cohérence : « haut = ce que dit l'autre, bas = ce que je
  dis ou choisis ».

**Rationale** : mélanger les rôles (LLM qui « écrit » des inputs dans la
bulle utilisateur) brise la métaphore conversationnelle, complique les
tests E2E et provoque des bugs d'accessibilité. Le bottom sheet maintient
une frontière nette entre énoncé et réponse.

## Contraintes Techniques & Architecture

### Stack imposée

- **Frontend** : Nuxt 4 (Composition API), Pinia, TailwindCSS v4,
  chart.js, mermaid, Leaflet, gsap, driver.js, fontawesome,
  toast-ui/editor ; orchestration LLM front via LangGraph (LangChain en
  utilitaire).
- **Backend** : FastAPI, Python 3.12+, LangGraph côté backend,
  Pydantic v2 strict.
- **Base de données** : PostgreSQL avec extension pgvector ; RLS activée
  par défaut.
- **LLM** : `minimax-m2.7` via OpenRouter par défaut, interchangeable via
  les variables `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Aucune feature
  ne MUST hard-coder un endpoint ou un modèle dans le code applicatif.
- **Embeddings** : Voyage AI `voyage-3.5` (1024 dimensions, multilingue
  performant pour le français). Schéma : `embedding vector(1024)` côté
  pgvector.
- **Speech-to-Text** : Replicate (Whisper) — post-MVP, clé déjà en place
  (`REPLICATE_API_TOKEN`).

### Environnement local

- **Backend** : exécuté dans un `.venv` Python à la racine du dossier
  backend (gestion via `pip` ou `uv`). **Pas de conteneur backend en
  développement.**
- **PostgreSQL + pgvector** : **seul** service dockerisé, défini dans un
  `docker-compose.yml` à la racine du repo, image
  `pgvector/pgvector:pg16`, volume nommé pour la persistance, port 5432
  exposé.
- **Frontend** : `pnpm dev` en local, pas de conteneur frontend en
  développement.
- **Migrations** : Alembic exécuté depuis le `.venv` backend contre la
  Postgres dockerisée.

### Configuration & secrets

- Un `.env` à la racine MUST être gitignored ; un `.env.example` versionné
  MUST documenter toutes les variables.
- Variables minimales : `DB_PASSWORD`, `LLM_BASE_URL`, `LLM_API_KEY`,
  `LLM_MODEL`, `APP_URL`, `JWT_SECRET`, `VOYAGE_API_KEY`,
  `REPLICATE_API_TOKEN`.
- Aucun secret ne MUST être hardcodé dans le code source. Le démarrage de
  l'application MUST échouer explicitement si une variable obligatoire est
  manquante.

### Hébergement

- Hébergement de production : **Europe ou Afrique de l'Ouest uniquement**
  (OVH, Scaleway, AWS Cape Town, Africa Data Centres). Le déploiement aux
  États-Unis est **interdit** pour conformité RGPD européen + loi
  ivoirienne 2013-450 + règlement UEMOA 20/2010.

## Conformité Légale & Données Personnelles

- Conformité RGPD européen + loi ivoirienne 2013-450 + règlement UEMOA
  20/2010 MUST être atteinte dès le MVP, pas reportée.
- Une page **« Mes données »** MUST être disponible pour chaque PME, avec :
  consultation complète, export JSON, suppression de compte avec délai de
  grâce de 30 jours.
- Les consentements MUST être **granulaires par usage** : Mobile Money,
  photos d'exploitation, attestation publique, conservation longue, partage
  vers intermédiaires. Aucun consentement global non décomposable.
- TLS 1.3 MUST être appliqué sur tous les flux entrants et sortants.
- Le chiffrement at-rest MUST utiliser le mécanisme natif du Postgres
  managé en production.
- Une politique de confidentialité MUST être publiée publiquement et un
  point de contact `privacy@esg-mefali.com` MUST être joignable.

## Langue

- Français est la langue **par défaut** sur toute l'interface PME et tous
  les rapports générés.
- L'anglais MUST être disponible **uniquement** pour les dossiers de
  candidature aux Offres dont `accepted_languages` inclut `'en'`.
- Les langues locales (Wolof, Bambara, etc.) et les autres langues sont
  **post-MVP** ; aucune feature MVP ne MUST attendre leur disponibilité.

## Discipline Produit & Workflow Spec-Kit

- Toute feature MUST suivre l'enchaînement : `/speckit.specify` →
  `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` →
  `/speckit.implement`. Aucune feature ne MUST être implémentée sans
  spec, plan et tasks préalables.
- Le découpage en 35 features est documenté dans
  `docs_et_brouillons/features/00-INDEX.md` avec phasage et dépendances.
  L'ordre des dépendances MUST être respecté ; commencer une feature dont
  une dépendance est encore en `draft` est interdit.
- Chaque feature MUST lister explicitement son **hors-scope MVP**.
  Réintroduire un élément hors-scope sous prétexte d'opportunité MUST être
  rejeté en review.
- **Eval-driven development** pour le LLM : aucune skill, aucun tool, aucun
  prompt système ne MUST être publié sans avoir passé le golden set
  (≥ 50 cas, métriques de réussite documentées).
- Les modifications de la stack imposée (remplacement d'une bibliothèque
  majeure, migration de framework) requièrent un amendement constitutionnel
  (voir Governance).

## Governance

Cette constitution **supersède** toute autre pratique, convention ou
préférence individuelle dans le projet ESG Mefali.

**Vérification de conformité** :

- `/speckit-plan` MUST contenir une section « Constitution Check » qui
  évalue chacun des 10 principes pour la feature en cours, AVANT la
  recherche (Phase 0) et APRÈS le design (Phase 1).
- `/speckit-tasks` MUST inclure les tâches dérivées des principes
  applicables (RLS, audit, snapshot, etc.) et les marquer comme
  prérequis Phase 2 (Foundational) lorsque la feature les nécessite.
- `/speckit-analyze` MUST signaler toute incohérence entre `spec.md`,
  `plan.md`, `tasks.md` et la constitution comme bloquante.

**Justification d'écart** :

- Tout écart par rapport à un principe MUST être documenté dans la
  section « Complexity Tracking » du plan, avec : violation,
  pourquoi nécessaire, alternative simple rejetée et raison du rejet.
- Les principes marqués (NON NÉGOCIABLE) ne MUST PAS faire l'objet d'un
  écart, même justifié. Un besoin contradictoire déclenche un amendement
  constitutionnel, pas un contournement.

**Procédure d'amendement** :

- Un amendement MUST être proposé en pull request modifiant ce fichier
  et le `Sync Impact Report` en tête.
- Toute modification MUST faire évoluer la version selon les règles
  semver :
  - **MAJOR** : suppression ou redéfinition incompatible d'un principe ou
    d'une règle de gouvernance.
  - **MINOR** : ajout d'un principe ou expansion matérielle d'une
    section.
  - **PATCH** : clarifications, reformulations, corrections sans portée
    sémantique.
- Tout amendement MUST mettre à jour `LAST_AMENDED_DATE` (date ISO du
  jour) et propager les ajustements aux templates dépendants
  (`plan-template.md`, `spec-template.md`, `tasks-template.md`,
  `checklist-template.md`).

**Politique de versioning de la constitution** :

- `RATIFICATION_DATE` est gelée à la date d'adoption initiale et ne MUST
  pas être modifiée par les amendements ultérieurs.
- L'historique des versions est tracé dans le journal git de ce fichier ;
  un changelog interne n'est pas requis tant que les Sync Impact Reports
  successifs sont préservés.

**Guide de référence runtime** :

- `docs_et_brouillons/features/00-INDEX.md` documente l'ordre des
  features et les dépendances.
- `CLAUDE.md` à la racine pointe vers le plan courant pour le contexte
  d'exécution.

**Version**: 1.0.0 | **Ratified**: 2026-04-29 | **Last Amended**: 2026-04-29
