# Feature Specification: Générateur de Dossiers de Candidature (via Skills, multilingue, multi-offres)

**Feature Branch**: `026-generateur-dossiers-candidatures`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F26 — Générateur de Dossiers de Candidature (via Skills, multilingue FR/EN, multi-offres). Source brief: docs_et_brouillons/features/26-generateur-dossiers-candidatures.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Générer un dossier depuis une candidature (Priority: P1)

Une PME ouvre une de ses candidatures (par exemple GCF×BOAD) et clique sur "Générer le dossier". Le système invoque la skill associée à l'offre, pré-remplit les sections factuelles depuis le profil entreprise / projet / scores ESG, fait rédiger les sections narratives par la skill et restitue un dossier complet, multi-sections, prêt à être édité et exporté.

**Why this priority**: c'est le cas d'usage central de la feature — sans lui, la valeur métier (réduction du temps de rédaction d'un dossier de candidature de plusieurs jours à quelques minutes) n'existe pas.

**Independent Test**: pour une candidature GCF×BOAD existante, déclencher la génération via API ; vérifier qu'un dossier persisté apparaît dans la base avec toutes les sections obligatoires non vides, langue conforme à l'offre, citations sources sur les sections narratives chiffrées, et qu'il peut être relu via l'endpoint de consultation.

**Acceptance Scenarios**:

1. **Given** une candidature GCF×BOAD avec un projet, un profil PME et des scores ESG complets, **When** la PME lance la génération, **Then** un dossier en français est créé avec toutes les sections du template (auto + narratif) renseignées et statut `genere`.
2. **Given** une candidature dont l'offre accepte uniquement l'anglais, **When** la PME lance la génération sans préciser de langue, **Then** le dossier est rédigé en anglais.
3. **Given** une candidature dont l'offre n'a pas de skill associée, **When** la PME lance la génération, **Then** le système refuse avec un message clair et n'écrit pas de dossier.

---

### User Story 2 — Pré-remplissage automatique des sections factuelles (Priority: P1)

La PME veut que les sections "Identité de l'entreprise", "Description du projet", "Indicateurs d'impact", "Plan de financement" soient remplies automatiquement depuis son profil, ses projets et ses scores ESG, sans réécrire ce qu'elle a déjà saisi.

**Why this priority**: c'est ce qui transforme la génération d'un exercice de copier-coller en un service à valeur ajoutée. Sans ce pré-remplissage, le générateur n'apporte qu'un gain marginal.

**Independent Test**: créer une PME avec profil complet et projet renseigné ; lancer la génération ; vérifier que les sections de type "auto" du dossier reflètent fidèlement les données du profil/projet/scores (raison sociale, secteur, indicateurs ESG, montant demandé, etc.) et qu'aucun champ obligatoire n'est laissé vide quand la donnée existe.

**Acceptance Scenarios**:

1. **Given** un profil entreprise renseigné, **When** la génération s'exécute, **Then** la section "Identité de l'entreprise" reprend la raison sociale, le secteur, l'effectif et l'adresse sans intervention humaine.
2. **Given** un projet avec montant demandé en XOF, **When** la génération s'exécute, **Then** la section "Plan de financement" affiche le montant typé (montant + devise) sans erreur d'unité.
3. **Given** un profil incomplet (champ effectif manquant), **When** la génération s'exécute, **Then** la section concernée signale explicitement le champ manquant et reste générée pour les autres données.

---

### User Story 3 — Sections narratives via la skill associée à l'offre (Priority: P1)

La PME veut que les sections subjectives ("Théorie du changement", "Justification de l'impact paradigmatique", "Conformité aux sauvegardes ESS") soient rédigées par la skill spécifique à l'offre (ton, vocabulaire métier, longueur cible), avec des citations sources pour les chiffres.

**Why this priority**: la qualité rédactionnelle est ce qui distingue un dossier acceptable d'un dossier rejeté par les fund officers. Sans skill dédiée, les sections narratives manquent de crédibilité.

**Independent Test**: lancer une génération sur une offre dont la skill est seedée (ex. `skill_dossier_gcf_via_boad`) ; vérifier que les sections narratives sont rédigées en respectant le ton attendu, la longueur cible (±20%), et que toute mention chiffrée est accompagnée d'au moins une citation source du registre F03.

**Acceptance Scenarios**:

1. **Given** la skill `skill_dossier_gcf_via_boad` activée pour l'offre, **When** la section "Théorie du changement" est générée, **Then** elle contient un texte structuré (problème, solution, impact mesurable) dans la fourchette de longueur définie par la skill.
2. **Given** une section narrative qui mentionne un chiffre issu d'un référentiel, **When** la génération se termine, **Then** la sortie inclut au moins une citation source de type F03 (id de Source) pointant sur la donnée mobilisée.
3. **Given** une skill qui interdit certains anti-patterns ("ne jamais promettre un impact non quantifié"), **When** la sortie de la génération est validée, **Then** la section ne contient aucun anti-pattern listé.

---

### User Story 4 — Édition manuelle et regénération section par section (Priority: P1)

La PME veut éditer manuellement chaque section générée, ou demander une regénération ciblée d'une section sans relancer le dossier complet.

**Why this priority**: aucun dossier généré automatiquement n'est envoyé tel quel. Sans édition / regénération ciblée, le dossier est inutilisable.

**Independent Test**: après génération, modifier le contenu d'une section via l'API d'édition, vérifier la persistance ; déclencher une regénération ciblée d'une autre section et vérifier que seule celle-ci change, les autres restant intactes.

**Acceptance Scenarios**:

1. **Given** un dossier généré, **When** la PME envoie une mise à jour du contenu d'une section, **Then** la section est mise à jour et le statut du dossier passe à `en_revision`.
2. **Given** un dossier généré, **When** la PME demande la regénération d'une section narrative, **Then** seule cette section est ré-écrite par la skill et les autres sections restent inchangées.

---

### User Story 5 — Multilingue FR/EN selon l'offre (Priority: P1)

La PME veut que la langue de génération soit déterminée par les langues acceptées par l'intermédiaire de l'offre. Si plusieurs langues sont acceptées, la PME peut choisir.

**Why this priority**: envoyer un dossier dans une langue non acceptée garantit le rejet. C'est un pré-requis fonctionnel.

**Independent Test**: pour trois offres avec respectivement `accepted_languages=['fr']`, `['en']`, `['fr','en']`, vérifier que la génération produit FR / EN / FR-par-défaut, et que demander une langue non acceptée échoue avec un message clair.

**Acceptance Scenarios**:

1. **Given** une offre `accepted_languages=['fr']`, **When** la PME demande EN, **Then** le système refuse et propose FR.
2. **Given** une offre `accepted_languages=['fr','en']`, **When** la PME ne précise pas de langue, **Then** la génération se fait en FR (défaut).
3. **Given** une offre `accepted_languages=['en']`, **When** la PME lance sans préciser, **Then** la génération se fait en EN.

---

### User Story 6 — Checklist documentaire union (Priority: P1)

La PME veut voir la liste consolidée (union fonds + intermédiaire) des documents requis pour une candidature, avec leur statut (uploadé ou manquant) et un lien direct vers l'upload.

**Why this priority**: même un dossier narrativement parfait est rejeté si une pièce justificative manque. La checklist est indispensable au cycle de soumission.

**Independent Test**: pour une candidature liée à un fonds + un intermédiaire qui exigent au total 7 documents distincts, vérifier que l'endpoint checklist retourne 7 entrées dédupliquées avec un drapeau précis "présent" / "absent" basé sur les uploads existants.

**Acceptance Scenarios**:

1. **Given** un fonds exigeant 4 documents et un intermédiaire en exigeant 5 (dont 2 communs), **When** la PME consulte la checklist, **Then** elle voit 7 entrées uniques.
2. **Given** la PME a uploadé 3 des documents requis, **When** elle consulte la checklist, **Then** ces 3 entrées sont marquées "présent" et les 4 autres "absent".

---

### User Story 7 — Export Word et PDF (Priority: P1)

La PME veut exporter le dossier final en Word (éditable) et/ou PDF (archivage) selon le format demandé par l'intermédiaire.

**Why this priority**: la soumission au portail intermédiaire se fait toujours via fichier ; sans export, le dossier reste inutilisable hors plateforme.

**Independent Test**: après génération, déclencher un export Word puis un export PDF ; vérifier que les fichiers sont produits, ouvrent dans des outils standards (Word, LibreOffice, lecteur PDF) et contiennent toutes les sections.

**Acceptance Scenarios**:

1. **Given** un dossier généré complet, **When** la PME demande l'export Word, **Then** un fichier .docx valide est produit, contenant tous les titres et le contenu de chaque section.
2. **Given** un dossier généré complet, **When** la PME demande l'export PDF, **Then** un fichier PDF valide est produit, paginé, contenant le contenu de toutes les sections.

---

### User Story 8 — Annexe sources auto-générée (Priority: P1)

La PME veut que toutes les sources (registre F03) mobilisées dans le dossier soient listées en annexe avec référence (titre, URL ou identifiant), pour la crédibilité du dossier.

**Why this priority**: la traçabilité est un invariant constitutionnel (P1 — sourçage anti-hallucination). C'est non négociable.

**Independent Test**: générer un dossier dont les sections narratives citent au moins 3 sources distinctes ; vérifier que l'annexe sources liste exactement ces 3 sources, dédupliquées et ordonnées.

**Acceptance Scenarios**:

1. **Given** des sections citant 5 sources distinctes (avec doublons internes), **When** la dernière section "Annexe sources" est générée, **Then** elle liste les 5 sources uniques.

---

### User Story 9 — Génération multi-offres pour un même projet (Priority: P2)

La PME sélectionne 2 ou 3 candidatures de son projet et lance la génération ; le système réutilise le contenu commun (descriptif PME, projet, scores) et génère seulement les contenus spécifiques par chaque skill.

**Why this priority**: utile pour les projets ciblant plusieurs financeurs, mais pas bloquant pour le MVP.

**Independent Test**: créer un projet avec 3 candidatures actives ; lancer la génération multi-candidatures ; vérifier 3 dossiers distincts produits, sections "Identité PME" identiques entre dossiers, sections narratives spécifiques par offre.

**Acceptance Scenarios**:

1. **Given** un projet avec 3 candidatures, **When** la PME lance la génération batch, **Then** 3 dossiers sont créés et la section "Identité de l'entreprise" est strictement identique entre les 3.

---

### User Story 10 — Inclusion attestation ESG (Priority: P2)

La PME peut cocher "Inclure mon attestation ESG Mefali" pour l'attacher en annexe du dossier (généré à la volée si manquant).

**Why this priority**: option de crédibilité, désirable mais non bloquante en MVP.

**Independent Test**: cocher l'option ; vérifier que l'export Word/PDF inclut une annexe "Attestation ESG" avec le contenu attendu.

**Acceptance Scenarios**:

1. **Given** une PME ayant déjà une attestation ESG valide, **When** la génération inclut l'attestation, **Then** elle apparaît en annexe du dossier exporté.

---

### Edge Cases

- L'offre ne possède pas de skill associée → la génération est refusée explicitement, aucun dossier persisté.
- Le profil PME ou le projet est incomplet → les sections "auto" mentionnent les champs manquants ; les sections narratives basées sur ces champs sont générées en signalant l'incomplétude (sans inventer).
- La langue demandée n'est pas dans `accepted_languages` → erreur de validation explicite.
- Re-génération d'une section déjà éditée manuellement → la section éditée est remplacée par la nouvelle génération ; un avertissement est retourné dans la réponse.
- Offre avec `accepted_languages` vide ou nul → fallback FR par défaut, signalé en assumption.
- Génération concurrente de deux dossiers pour la même candidature → seule la première s'exécute, la seconde reçoit un conflit ou la version courante.
- Un document requis figurant dans le fonds ET dans l'intermédiaire → dédupliqué par identifiant logique (slug).
- Les exports Word/PDF échouent (erreur de rendu) → le dossier reste consultable, l'erreur d'export est retournée explicitement et journalisée.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système doit gérer un Template de dossier par Offre (sections ordonnées, type `auto`/`narratif`/`document`, longueur cible, identifiant de section dans la skill).
- **FR-002**: Le système doit permettre à l'admin de créer/lire/mettre à jour/désactiver un template de dossier rattaché à une offre (workflow draft → published cohérent F06).
- **FR-003**: Le système doit générer un dossier à partir d'une candidature donnée, en chargeant la skill liée à l'offre, en remplissant les sections `auto` depuis profil/projet/scores et en faisant générer les sections `narratif` par la skill.
- **FR-004**: Le système doit persister le dossier produit dans une table dédiée avec sections markdown, langue, statut (`en_generation`, `genere`, `en_revision`, `exporte`), version simple incrémentale, horodatage.
- **FR-005**: Le système doit exposer des endpoints PME pour : lancer la génération, consulter l'état du dossier, éditer une section, regénérer une section, exporter Word/PDF, consulter la checklist documentaire.
- **FR-006**: Le système doit refuser une demande de génération si l'offre n'a pas de skill associée, et journaliser l'incident.
- **FR-007**: Le système doit valider la langue demandée contre `accepted_languages` de l'offre, avec FR par défaut si plusieurs langues sont acceptées et qu'aucune n'est précisée.
- **FR-008**: Le système doit produire une annexe automatique listant les Sources mobilisées (registre F03), dédupliquées par identifiant.
- **FR-009**: Le système doit produire une checklist documentaire = union des documents requis (fonds + intermédiaire), dédupliquée par slug, marquant chaque ligne `present`/`absent` selon les uploads existants pour la candidature.
- **FR-010**: Le système doit générer un export Word (.docx) lisible par Word/LibreOffice et un export PDF paginé.
- **FR-011**: Le système doit garantir le sourçage anti-hallucination : chaque section narrative qui mentionne un chiffre ou un critère sectoriel doit inclure au moins une citation Source (P1 constitution).
- **FR-012**: Le système doit garantir la sécurité multi-tenant : une PME ne peut générer/consulter que les dossiers de ses propres candidatures (RLS active).
- **FR-013**: Le système doit auditer toute création, édition manuelle, regénération, export d'un dossier (audit append-only, F04).
- **FR-014**: Le système doit fournir un Tool LLM `generate_dossier(candidature_id, language?)` permettant à l'orchestrateur conversationnel d'invoquer la génération.
- **FR-015**: Le système doit permettre une génération multi-candidatures pour un même projet, en partageant le contenu commun (identité PME, projet) et en générant le contenu spécifique par skill (US9, P2).
- **FR-016**: Le système doit permettre l'inclusion optionnelle de l'attestation ESG en annexe (US10, P2).

### Key Entities

- **TemplateDossier**: gabarit de structure d'un dossier rattaché à une offre. Attributs clés : nom, langue cible, structure ordonnée des sections (titre, type, identifiant de section dans la skill, longueur cible), statut de publication, version, source d'origine.
- **Dossier**: instance de dossier produite pour une candidature. Attributs clés : référence à la candidature, langue effective, sections (markdown par section), statut, fichier Word généré (chemin), fichier PDF généré (chemin), version, horodatage de génération.
- **SectionDossier** (logique, embarquée dans `Dossier`): un titre, un type (`auto`/`narratif`/`document`), un contenu markdown, un éventuel ensemble d'identifiants Source mobilisés.
- **ChecklistEntry** (logique, calculée): un slug de document requis, son origine (fonds/intermédiaire), son statut (`present`/`absent`), un lien d'upload associé.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: pour une candidature GCF×BOAD complète, un dossier de 10–15 sections est généré et persisté en moins de 90 secondes (séquentiel) — vérifié par test d'intégration mesurant la durée.
- **SC-002**: 100 % des sections narratives contenant un chiffre incluent au moins une citation Source (mesuré par règle de validation au moment de la persistance).
- **SC-003**: 100 % des dossiers générés respectent la langue effective imposée par l'offre (test multilingue FR/EN couvrant les trois cas `['fr']`, `['en']`, `['fr','en']`).
- **SC-004**: l'export Word produit un fichier .docx valide ouvert sans erreur par LibreOffice headless ; l'export PDF produit un fichier paginé sans erreur de rendu (test smoke automatisé).
- **SC-005**: 100 % des accès PME respectent l'isolement multi-tenant (test de sécurité : une PME ne peut pas accéder au dossier d'une autre).
- **SC-006**: 100 % des actions critiques (création, édition, regénération, export) génèrent une ligne d'audit append-only (vérifié par test d'intégration).
- **SC-007**: la checklist documentaire pour une candidature avec N exigences fonds + M exigences intermédiaire produit exactement |union(N, M)| entrées uniques (vérifié par test).

## Assumptions

- Les skills `skill_dossier_*` (au moins `skill_dossier_gcf_via_boad`) sont seedées et activées via F19/F21. Pour le MVP, FR uniquement est obligatoire ; EN peut être livré comme fonctionnalité différée.
- Le Module 0 et les fondations F01–F25 sont stables (RLS, audit `record_audit`, money typé, sourçage F03, profil F11, projets F12, candidatures F25, scoring F23).
- L'attestation ESG (F30) n'est pas encore livrée ; l'option d'inclusion (US10) sera implémentée en mode "feature flag off" tant que F30 n'est pas dispo, et reste P2.
- Les exports Word/PDF utilisent des bibliothèques côté serveur déjà présentes ou installables sans modifier `pyproject.toml` au-delà des dépendances usuelles.
- Pour le MVP, la génération est synchrone (réponse une fois le dossier produit) ; le streaming SSE par section est différé en P2.
- L'UI Vue (`/profil/candidatures/[id]/dossier`) est différée — le MVP se concentre sur le backend (API + service + persistance + exports). Le frontend est marqué `[DEFERRED]`.
- La génération multi-candidatures (US9) en MVP peut s'exécuter de façon séquentielle (boucle synchrone), pas en workers parallèles.
- La cohérence "contenu commun identique entre dossiers du même projet" est obtenue en réutilisant la même source de données (profil/projet/scores) — aucune mémoire partagée additionnelle requise.
- Le quota et le coût LLM par dossier sont supposés couverts par le budget global du projet (F18 / scoring) ; aucune nouvelle table de pricing n'est introduite dans cette feature.
