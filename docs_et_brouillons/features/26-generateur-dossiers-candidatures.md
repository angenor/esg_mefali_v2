# F26 — Générateur de Dossiers de Candidature (via Skills, multilingue, multi-offres)

**Phase** : 6 — Conseiller Financement (Module 3)
**Modules brainstorm** : 3.3 (Générateur de Dossiers de Candidature), 11.6 (Lien fort Skills ↔ dossiers)
**Dépendances** : F21 (skills MVP), F25
**Estimation** : 3 jours

## Contexte et objectif

> **C'est le cas d'usage le plus critique des Skills** (du brainstorming Module 11.6) : chaque template de dossier est associé à **une skill `skill_dossier_<offre>` dédiée** qui encode sections obligatoires, ton imposé par l'intermédiaire, langue (FR/EN selon `accepted_languages`), longueur cible, vocabulaire métier, anti-patterns rédactionnels.

Cette feature livre :
- **Templates de dossier par Offre** (gérés via F09 + F20),
- Pré-remplissage automatique à partir du profil entreprise + projet + scores ESG,
- Génération de **sections narratives** par la skill associée à l'Offre,
- **Multilingue** : FR par défaut, EN optionnel selon `accepted_languages` de l'Offre (F08),
- **Génération en parallèle** pour plusieurs Offres ciblant le même projet (réutilisation des contenus narratifs avec adaptations par offre),
- **Checklist documentaire** = union des documents requis fonds + intermédiaire,
- Export Word et/ou PDF selon exigences de l'intermédiaire,
- Inclusion de l'**attestation ESG Mefali** (F30) si la PME le souhaite.

## User Stories

### US1 — Lancer la génération depuis une candidature (P1)
**En tant que** PME,
**je veux** sur la page d'une candidature, un bouton "Générer le dossier" qui invoque la skill associée à l'Offre,
**afin de** obtenir un dossier pré-rédigé en quelques minutes.

**Test indépendant** : candidature GCF×BOAD → bouton → progress bar → dossier généré téléchargeable + visible dans `/profil/candidatures/[id]/dossier`.

### US2 — Pré-remplissage automatique (P1)
**En tant que** PME,
**je veux** que les sections "Identité de l'entreprise", "Description du projet", "Indicateurs d'impact", "Plan de financement" soient pré-remplies depuis mon profil (F11), mes projets (F12), et mes scores (F23),
**afin de** ne pas réécrire ce qui est déjà saisi.

### US3 — Sections narratives générées par la skill (P1)
**En tant que** PME,
**je veux** que les sections subjectives ("Théorie du changement", "Justification de l'impact paradigmatique GCF", "Conformité aux sauvegardes ESS BOAD") soient rédigées par la skill associée à l'Offre,
**afin de** professionnalisme.

**Mécanisme** : la skill reçoit en contexte le profil + projet + scores, et génère le texte section par section avec citations sources (F03).

### US4 — Édition manuelle des sections (P1)
**En tant que** PME,
**je veux** pouvoir éditer chaque section générée avant export,
**afin de** ajuster le ton ou ajouter des éléments propres.

**UI** : éditeur markdown (toast-ui/editor déjà installé F01) section par section, avec aperçu + bouton "Re-générer cette section".

### US5 — Multilingue FR/EN selon Offre (P1)
**En tant que** PME,
**je veux** que la langue de génération soit déterminée par `accepted_languages` de l'Offre (F08), avec choix UI si plusieurs sont acceptées,
**afin de** ne pas envoyer un dossier français à un intermédiaire qui ne le supporte pas.

**Scénarios** :
1. Offre `accepted_languages=['fr']` → génération FR uniquement.
2. Offre `accepted_languages=['en']` → génération EN uniquement.
3. Offre `accepted_languages=['fr','en']` → choix utilisateur, défaut FR.

### US6 — Génération multi-offres pour un même projet (P2)
**En tant que** PME,
**je veux** sélectionner 2-3 candidatures de mon projet et lancer la génération en parallèle,
**afin de** obtenir des dossiers adaptés à chaque Offre tout en réutilisant le contenu commun.

**Mécanisme** : pour chaque candidature, sa skill associée est invoquée. Le contenu commun (description PME, projet, scores) est partagé ; le contenu spécifique (sections narratives, ton) est généré par chaque skill séparément.

### US7 — Checklist documentaire union (P1)
**En tant que** PME,
**je veux** voir la liste des documents requis (union fonds + intermédiaire), avec statut (✓ uploadé, ○ manquant) et lien direct vers l'upload,
**afin de** compléter avant soumission.

### US8 — Inclusion attestation ESG Mefali (P2)
**En tant que** PME,
**je veux** une option "Inclure mon attestation ESG Mefali (F30)" qui :
- génère l'attestation si pas déjà fait,
- l'attache au dossier comme annexe.

**afin de** crédibiliser le dossier.

### US9 — Export Word et PDF (P1)
**En tant que** PME,
**je veux** exporter le dossier en :
- **Word** (.docx) — éditable par l'intermédiaire,
- **PDF** — pour archivage,
selon le format demandé par l'intermédiaire.

### US10 — Annexe sources auto-générée (P1)
**En tant que** PME,
**je veux** que toutes les sources mobilisées dans le dossier soient listées en annexe (cohérent F03 / F24),
**afin de** crédibilité.

## Exigences fonctionnelles

- **FR-001** : Table `template_dossier` (déjà esquissée en F01) enrichie : `id, offre_id, name, language, structure_json, source_id, version, status`. Une `structure_json` liste les sections (titre, type:'auto'|'narratif'|'document', skill_section_id, longueur_cible).
- **FR-002** : CRUD admin de `template_dossier` (cohérent F06/F08, ajouté ici car spécifique aux Offres).
- **FR-003** : Service backend `DossierGeneratorService` :
  - `generate(candidature_id, language) -> Dossier`,
  - charge la skill associée à l'Offre (F19/F21),
  - itère les sections du template,
  - pour chaque section `auto`, remplit avec données profil/projet/scores,
  - pour chaque section `narratif`, invoque le LLM avec contexte ciblé,
  - assemble + génère Word et PDF.
- **FR-004** : Table `dossier` : `id, candidature_id, language, sections_json (markdown par section), status ENUM('en_generation','genere','en_revision','exporte'), word_file_path NULL, pdf_file_path NULL, generated_at, version`.
- **FR-005** : Endpoints :
  - `POST /me/candidatures/{id}/dossier` body `{language?}` → lance génération, renvoie `dossier_id`.
  - `GET /me/candidatures/{id}/dossier` → état + sections.
  - `PATCH /me/candidatures/{id}/dossier/sections/{section_id}` → édition manuelle.
  - `POST /me/candidatures/{id}/dossier/sections/{section_id}/regenerate`.
  - `POST /me/candidatures/{id}/dossier/export?format=word|pdf`.
  - `GET /me/candidatures/{id}/dossier/checklist` → liste docs requis avec statut.
- **FR-006** : Page Vue `/profil/candidatures/[id]/dossier` :
  - Vue par sections (table des matières latérale),
  - Édition inline avec toast-ui/editor,
  - Statut de progression de la génération,
  - Checklist docs,
  - Boutons Export Word / PDF.
- **FR-007** : Génération multi-candidatures (US6) : endpoint `POST /me/projets/{id}/dossiers-batch` body `{candidature_ids:[]}` qui orchestre N générations en parallèle (workers async ou en synchrone séquentiel MVP).
- **FR-008** : Génération Word via `python-docx` ; PDF via `weasyprint` (cohérent F24).
- **FR-009** : Tool LLM `generate_dossier(candidature_id, language)` (cohérent F17 FR-001) qui appelle ce service.
- **FR-010** : Streaming d'avancement : SSE event par section générée pour UI progress bar.

## Exigences non-fonctionnelles

- **NFR-001** : Génération d'un dossier complet (10–15 sections) en < 90s (séquentiel) avec un LLM moyen.
- **NFR-002** : Le contenu généré est en français correct (orthographe, accents) ou anglais correct (selon langue).
- **NFR-003** : Aucune section narrative n'est publiée sans citations sources si elle mentionne des chiffres/critères (cohérent F03).
- **NFR-004** : Le format Word respecte les styles attendus (titres, listes, tableaux, page de garde).
- **NFR-005** : Re-génération idempotente : re-lancer une génération sur une candidature inchangée donne un résultat similaire (le seed du LLM est plus ou moins déterministe, mais la skill encadre).

## Entités clés

- **TemplateDossier** (FR-001, étend F01).
- **Dossier** (FR-004).

## Success Criteria

- **SC-001** : Dossier GCF×BOAD pour une PME complète généré en < 90s, 15 sections, 20-30 pages.
- **SC-002** : Édition d'une section + re-génération d'une autre fonctionnelle.
- **SC-003** : Export Word ouvre dans Word/LibreOffice avec styles préservés.
- **SC-004** : Multilingue FR/EN testé sur 2 candidatures (BOAD FR, SUNREF EN).
- **SC-005** : Multi-candidatures : 3 dossiers générés en parallèle pour un projet, contenus différents adaptés.

## Hors-scope MVP

- Templating WYSIWYG (post-MVP).
- Co-édition multi-utilisateurs (post-MVP).
- Suggestions d'amélioration LLM après génération (post-MVP).
- Conversion automatique entre formats Word ↔ PDF avec mise en page exacte (en MVP, deux générations distinctes sont OK).
- Versioning fin des dossiers (post-MVP — version simple suffit).
- Soumission directe au portail intermédiaire (impossible vu la diversité des portails).

## Risques et points de vigilance

- **Qualité du contenu généré** : les fund officers ne pardonnent pas les erreurs grossières. Investir dans la skill (F21) — `prompt_expert` riche, sources, anti-patterns.
- **Anti-patterns rédactionnels** : "ne jamais promettre un impact non quantifié", "ne pas surévaluer la maturité du projet". À encoder dans `skill_expert_prompt`.
- **Coût LLM** : 15 sections × LLM call = 15 appels. Avec minimax-m2.7 ~ quelques cents par dossier. OK budget MVP.
- **Cohérence multi-offres** : si un projet candidate à 3 Offres, certaines sections (descriptif PME) doivent être identiques pour ne pas faire bizarre si le fund officer compare. Le service doit cacher le contenu commun et le réutiliser.
- **Mise en forme Word** : python-docx est limité côté style. Pour des dossiers avec mise en page complexe (tableaux, schémas), préférer un template Word maître (.dotx) que python-docx remplit. Plus stable.
- **Langue** : la skill `skill_dossier_*` doit pouvoir générer en FR ou EN. Soit deux skills (FR/EN) — recommandé pour cohérence, soit une skill bilingue (plus complexe).
