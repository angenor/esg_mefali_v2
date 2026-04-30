# Feature Specification: Extension Chrome — Détection sites & pré-remplissage IA

**Feature Branch**: `033-extension-detection-prefill`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Feature 33 : Extension Chrome — détection sites fonds/intermédiaires, observation SPA, pré-remplissage IA des formulaires, i18n FR/EN. MVP P1: US1 (login extension via JWT), US2 (détection URL via patterns backend), US3 (observation SPA), US4 (pré-remplissage formulaires avec code-couleur), US6 (suggestion IA par champ), US7 (i18n FR/EN), US8 (adaptation format intermédiaire). Backend endpoints: GET /extension/url-patterns, GET /extension/profile-summary, POST /extension/suggest-field. Squelette extension Chrome Manifest V3."

## Clarifications

### Session 2026-04-29

- Q: Format des patterns d'URL côté backend ? → A: les deux (wildcard simple + regex avancé), avec un champ `type` distinguant les deux modes côté admin.
- Q: Stratégie de stockage du jeton de session dans l'extension ? → A: stockage local persistant avec suivi de l'expiration et refresh implicite déclenché par un 401.
- Q: Périmètre de la projection profil PME exposée à l'extension ? → A: vue compactée (≤ 2 KB, 12-15 champs essentiels couvrant identité légale, secteur, pays, projet en cours, montant, description courte).
- Q: Mécanisme de mapping champ→profil par intermédiaire ? → A: heuristique générique + table backend optionnelle de mappings par intermédiaire (seed initiale 2-3 portails de référence).
- Q: Fréquence de rafraîchissement des patterns d'URL côté extension ? → A: au login, puis toutes les heures, avec invalidation manuelle disponible depuis le popup.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Connecter l'extension à mon compte ESG Mefali (Priority: P1)

En tant que PME, j'installe l'extension Chrome ESG Mefali et je m'authentifie avec mes identifiants. L'extension stocke un jeton de session local et affiche mon identité PME dans son popup.

**Why this priority**: Sans authentification, aucun appel personnalisé (profil, projets, suggestions) n'est possible. Bloquant pour toutes les autres user stories.

**Independent Test**: Installer l'extension non-empaquetée, ouvrir le popup, saisir email/mot de passe, vérifier que le popup affiche le nom de l'entreprise et que les appels back authentifiés réussissent.

**Acceptance Scenarios**:

1. **Given** une PME avec un compte valide, **When** elle saisit ses identifiants dans le popup, **Then** le jeton est stocké localement et le popup montre son nom d'entreprise.
2. **Given** une PME avec un jeton expiré, **When** un appel back échoue en 401, **Then** le popup propose une re-connexion sans perdre les préférences locales.
3. **Given** une PME non connectée, **When** elle ouvre une page de fonds, **Then** le bandeau invite à se connecter avant toute personnalisation.

---

### User Story 2 — Détecter automatiquement un site fonds ou intermédiaire (Priority: P1)

En tant que PME, je navigue sur un site partenaire (BOAD, GCF, AFD, Ecobank SUNREF, etc.). L'extension reconnaît l'URL via des patterns maintenus côté backend et affiche un bandeau discret indiquant l'Offre compatible détectée.

**Why this priority**: Cœur de la valeur — c'est le moment d'aide juste-à-temps qui fait que la PME utilise l'extension plutôt que de naviguer seule.

**Independent Test**: Créer un pattern d'URL côté admin, charger l'extension, naviguer sur l'URL ciblée, vérifier que le bandeau s'affiche avec le libellé de l'Offre.

**Acceptance Scenarios**:

1. **Given** un pattern actif `boad.org/*` lié à l'Offre "GCF via BOAD", **When** la PME ouvre boad.org/appels, **Then** un bandeau "Offre détectée" apparaît en haut de la page.
2. **Given** une URL hors patterns, **When** la PME y navigue, **Then** aucun bandeau n'est injecté.
3. **Given** un admin qui ajoute un nouveau pattern, **When** l'extension fait son fetch périodique, **Then** la nouvelle correspondance prend effet sans réinstallation.

---

### User Story 3 — Suivre les changements de page sur un site SPA (Priority: P1)

En tant que PME naviguant un portail moderne (Vue/React/Angular), je veux que le bandeau et la détection s'adaptent quand l'URL change sans rechargement complet.

**Why this priority**: Sans observation SPA, la majorité des portails modernes (notamment les portails fonds/intermédiaires récents) seraient mal couverts.

**Independent Test**: Charger une page SPA de test avec navigation `pushState`, vérifier que la détection se ré-évalue à chaque changement de route.

**Acceptance Scenarios**:

1. **Given** une SPA avec `history.pushState`, **When** la route change vers une URL ciblée, **Then** le bandeau se met à jour avec la nouvelle Offre.
2. **Given** une SPA quittant une URL ciblée, **When** la route change vers une URL non couverte, **Then** le bandeau disparaît.

---

### User Story 4 — Pré-remplir un formulaire avec code-couleur (Priority: P1)

En tant que PME sur un formulaire d'un portail intermédiaire, je clique sur un bouton "Tout remplir automatiquement". L'extension analyse les champs, les mappe à mon profil entreprise et projet, et remplit avec un code-couleur :
- vert : valeur exacte du profil,
- bleu : valeur suggérée par IA,
- orange : à compléter manuellement.

**Why this priority**: Premier gain de temps tangible. Démontre la valeur de la combinaison profil + IA.

**Independent Test**: Sur un formulaire test reproduisant les champs SUNREF/BOAD, lancer "Tout remplir", vérifier ≥70 % de couverture et le code-couleur correct.

**Acceptance Scenarios**:

1. **Given** une PME connectée avec profil complet, **When** elle clique "Tout remplir", **Then** au moins 70 % des champs reconnus sont remplis et leur code-couleur reflète l'origine de la valeur.
2. **Given** un champ sans correspondance, **When** "Tout remplir" termine, **Then** le champ reste vide et est marqué orange.
3. **Given** une PME non connectée, **When** elle tente "Tout remplir", **Then** l'extension affiche un message demandant la connexion.

---

### User Story 5 — Suggérer un texte sur un champ libre (Priority: P1)

En tant que PME sur un champ "Description du projet", j'utilise un mini-bouton "Suggérer" qui appelle l'IA avec le contexte projet et offre, et insère un texte adapté à la longueur maximale.

**Why this priority**: Bénéfice clé sur les champs libres difficiles. Réutilise les capacités IA existantes (skills) sans re-développement.

**Independent Test**: Ouvrir un champ texte avec longueur max, cliquer "Suggérer", vérifier qu'une suggestion respectant la limite est insérée en moins de 3 secondes.

**Acceptance Scenarios**:

1. **Given** un champ "Description" sur un site reconnu, **When** la PME clique "Suggérer", **Then** un texte adapté s'insère dans le champ.
2. **Given** un champ avec longueur max de 500 caractères, **When** une suggestion est demandée, **Then** la suggestion ne dépasse pas la limite.
3. **Given** un échec backend (IA indisponible), **When** la suggestion échoue, **Then** un message d'erreur clair s'affiche sans planter la page.

---

### User Story 6 — Interface bilingue FR/EN (Priority: P1)

En tant que PME, j'utilise l'extension dans ma langue (FR par défaut, EN sur préférence ou détection langue OS).

**Why this priority**: Audience PME UEMOA + bailleurs anglophones (GCF, AfDB). Sans bilinguisme, l'adoption est freinée.

**Independent Test**: Changer la langue dans les préférences, vérifier que tous les libellés (popup, bandeau, boutons) basculent.

**Acceptance Scenarios**:

1. **Given** un OS configuré en anglais, **When** la PME ouvre l'extension la première fois, **Then** l'interface s'affiche en EN.
2. **Given** la PME en FR, **When** elle bascule en EN dans les préférences, **Then** tous les libellés basculent immédiatement.

---

### User Story 7 — Adaptation au format de l'intermédiaire (Priority: P1)

En tant que PME sur le portail SUNREF Ecobank vs PNUD, je veux que le pré-remplissage et les suggestions IA s'adaptent au format spécifique (ton, longueur, vocabulaire) de l'intermédiaire détecté.

**Why this priority**: Valeur métier — différentier d'un simple form-filler. Tire parti des Skills existants (F21).

**Independent Test**: Sur deux portails différents, comparer la suggestion d'un même champ "Description" et constater des sorties distinctes en ton/format.

**Acceptance Scenarios**:

1. **Given** un site identifié comme "SUNREF Ecobank", **When** la PME demande une suggestion, **Then** le contexte d'appel inclut le profil de l'intermédiaire pour adapter le ton.
2. **Given** un site sans intermédiaire identifié, **When** la PME demande une suggestion, **Then** une suggestion générique reste produite.

---

### Edge Cases

- Site avec Content-Security-Policy bloquant l'injection : l'extension ne doit pas casser la page, et logguer une erreur silencieuse côté extension.
- Formulaire dont les champs n'ont pas de `label`/`name` exploitable : marquer tous les champs orange, ne rien remplir.
- Jeton expiré au moment d'un appel `suggest-field` : retour 401 propre, popup propose la reconnexion.
- Pattern d'URL qui matche mais Offre archivée côté backend : le bandeau ne s'affiche pas.
- Page très longue avec MutationObserver lourd : limiter la fréquence de ré-évaluation (debounce).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: L'extension MUST permettre à une PME de se connecter via email/mot de passe et de stocker un jeton de session localement, lié à son identité ESG Mefali.
- **FR-002**: L'extension MUST récupérer la liste des patterns d'URL fonds/intermédiaires actifs et les Offres associées depuis le backend au login, puis toutes les heures, avec une option d'invalidation manuelle exposée dans le popup.
- **FR-003**: L'extension MUST détecter, sur chaque chargement de page et sur chaque changement de route SPA, si l'URL courante correspond à un pattern connu, et afficher un bandeau d'information non intrusif lorsque c'est le cas.
- **FR-004**: L'extension MUST observer les changements de route SPA (`pushState`, `replaceState`, `popstate`) et la mutation du DOM pour ré-évaluer la détection sans rechargement.
- **FR-005**: L'extension MUST proposer un bouton "Tout remplir" qui analyse les champs visibles d'un formulaire (label, name, type, placeholder), les mappe au profil entreprise et au projet courant de la PME, et remplit les valeurs trouvées en signalant l'origine via un code-couleur (vert/bleu/orange).
- **FR-006**: L'extension MUST proposer, à côté de chaque champ texte long détecté, un bouton "Suggérer" qui appelle le backend avec contexte (champ, longueur max, projet, offre, intermédiaire) et insère le texte renvoyé dans le champ.
- **FR-007**: L'extension MUST supporter FR et EN, avec sélection automatique selon la langue OS au premier lancement et bascule manuelle persistée localement.
- **FR-008**: Le backend MUST exposer un endpoint qui retourne la liste des patterns d'URL actifs avec, pour chaque pattern, son `type` (`wildcard` ou `regex`), la référence à l'Offre, au Fonds et à l'Intermédiaire associés.
- **FR-009**: Le backend MUST exposer un endpoint qui retourne une vue compactée (≤ 2 KB, 12 à 15 champs : identité légale, secteur, pays, montant projet, description courte, etc.) du profil entreprise et du projet courant de la PME authentifiée.
- **FR-010**: Le backend MUST exposer un endpoint qui produit une suggestion textuelle pour un champ donné, en tenant compte du libellé du champ, de sa longueur maximale, et du contexte projet/offre/intermédiaire.
- **FR-011**: Tous les endpoints extension MUST exiger une authentification valide (jeton porteur) et appliquer la séparation des données entre PME (RLS).
- **FR-012**: Le backend MUST tracer dans le journal d'audit chaque appel aux endpoints extension (qui, quand, quel endpoint), conformément aux invariants Module 0.
- **FR-013**: L'extension MUST ne jamais transmettre de données sensibles vers une origine autre que le backend ESG Mefali.
- **FR-014**: Le backend MUST permettre à un administrateur de gérer les patterns d'URL et les liaisons aux Offres (création, mise à jour, désactivation), réutilisant le workflow existant sources/offres.
- **FR-015**: L'extension MUST gérer les jetons expirés en proposant une reconnexion claire et non bloquante pour les autres pages.
- **FR-016**: L'extension MUST stocker le jeton de session dans le stockage local persistant de l'extension, conserver la date d'expiration, et déclencher une procédure de refresh sur 401 sans perdre les préférences locales (langue, dernière Offre vue).
- **FR-017**: Le backend MUST proposer une table optionnelle de mappings champ→attribut profil par intermédiaire (`field_mapping_intermediaire`), seed initialement avec 2 à 3 portails de référence, exploitée par l'endpoint `profile-summary` ou un endpoint annexe pour guider l'extension.

### Key Entities *(include if feature involves data)*

- **UrlPattern** : motif d'URL reconnu comme appartenant à un fonds ou un intermédiaire ; attributs : motif (`pattern`), type de syntaxe (`wildcard` | `regex`), nature (fonds|intermédiaire), références Fonds/Intermédiaire/Offre, état actif, langue préférée.
- **FieldMappingIntermediaire** : table optionnelle reliant un intermédiaire à un dictionnaire `{field_label_pattern → profile_attribute}` pour guider le pré-remplissage ; seed initiale 2-3 portails (BOAD, SUNREF Ecobank, PNUD).
- **ExtensionProfileSummary** : projection du profil entreprise + projet en cours pour la PME connectée, agrégée pour le pré-remplissage (raison sociale, secteur, pays, montant projet, description projet, etc.).
- **FieldSuggestionRequest** : entrée d'appel "suggérer" — libellé du champ, longueur max, identifiants projet/offre/intermédiaire optionnels, langue.
- **FieldSuggestionResult** : sortie — texte suggéré, longueur effective, source (skill utilisé), métadonnées audit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME peut installer l'extension et se connecter en moins de 2 minutes (du chargement de l'extension à l'affichage de son identité dans le popup).
- **SC-002**: Sur les sites fonds/intermédiaires couverts par les patterns initiaux, la détection affiche le bandeau correct dans 95 % des navigations testées.
- **SC-003**: Sur les portails de référence (BOAD, SUNREF Ecobank, PNUD) avec patterns + mappings configurés, le bouton "Tout remplir" couvre au moins 70 % des champs reconnus avec un code-couleur juste.
- **SC-004**: Une suggestion IA est rendue en moins de 3 secondes sur le 95e percentile.
- **SC-005**: Le changement de langue FR↔EN est reflété sur l'ensemble des libellés visibles en moins d'une seconde.
- **SC-006**: Aucune régression mesurable de la performance de navigation : impact moyen < 50 ms par chargement de page sur les sites couverts.
- **SC-007**: 100 % des appels endpoints extension figurent dans le journal d'audit.

## Assumptions

- L'authentification existante (F02) émet des jetons utilisables par l'extension sans modification de schéma.
- Les profils entreprise (F11) et projets (F12) exposent les attributs nécessaires au pré-remplissage ; sinon une vue compactée minimale est dérivée des modèles existants.
- Les Offres (F08) fournissent les identifiants Fonds/Intermédiaires nécessaires aux patterns d'URL.
- Les skills existants (F21) couvrent les besoins de suggestion IA sans nouveau modèle.
- L'audit log (F04) est étendu pour accepter les évènements `extension.*` sans nouvelle table dédiée.
- La distribution MVP se fait en mode "unpacked" / `.crx` interne ; la publication Web Store est hors scope.
- Le RLS multi-tenant en place sur PME s'applique automatiquement aux nouveaux endpoints via la session authentifiée.
- Firefox / Manifest V2 sont hors scope MVP (Chrome/Edge/Brave seulement).
