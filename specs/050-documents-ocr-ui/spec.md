# Feature Specification: Documents upload + OCR viewer UI (F50)

**Feature Branch**: `050-documents-ocr-ui`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "@docs_et_brouillons/features/50-documents-ocr-ui.md — UI dédiée à l'upload de documents PME (PDF, images, Excel, Word) avec retour OCR/extraction structurée, validation par l'utilisateur et alimentation des modules scoring (F46) et candidatures (F54). Source critique de données pour la plateforme."

## Clarifications

### Session 2026-05-05

- Q: Cardinalité du rattachement document ↔ projet en MVP ? → A: 0..N projets par document (relation many-to-many, partage sans duplication)
- Q: Fenêtre de rétention soft-delete avant purge dure ? → A: 30 jours, puis purge dure automatique (aligné RGPD)
- Q: Niveau cible d'accessibilité de l'UI F50 ? → A: WCAG 2.1 niveau AA
- Q: Politique sur les re-uploads identiques (doublons) ? → A: Détection par empreinte de contenu + avertissement et choix utilisateur (réutiliser / forcer nouveau)
- Q: Empty state quand le corpus documentaire est vide ? → A: Empty state illustré + texte d'accompagnement + CTA primaire « Téléverser mon premier document » (sur `/documents` et grille projet)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Téléverser des documents d'entreprise (Priority: P1)

Une PME dépose un ou plusieurs documents (bilan PDF, photo de terrain, fichier Excel d'effectifs) depuis la page `/documents`. Elle voit la progression de chaque fichier, peut annuler ou réessayer, et retrouve immédiatement les documents dans une liste consolidée propre à son compte.

**Why this priority** : Sans capacité fiable d'upload, aucun autre flux (extraction OCR, scoring, candidature) ne peut démarrer. C'est la fondation de F50 et un prérequis dur pour F46 et F54.

**Independent Test** : Glisser-déposer 3 PDF de moins de 20 Mo simultanément → barre de progression par fichier, file d'attente respectée (max 5 simultanés), entrées créées dans la liste avec statut « En traitement ».

**Acceptance Scenarios** :

1. **Given** une PME authentifiée sur `/documents`, **When** elle dépose 3 PDF (5 Mo, 12 Mo, 18 Mo) en drag & drop, **Then** chaque fichier affiche une barre de progression individuelle, l'upload se termine avec succès et 3 lignes apparaissent dans la liste avec statut OCR initial.
2. **Given** un upload en cours, **When** la connexion réseau échoue temporairement, **Then** le fichier passe en état « Échec » avec un bouton « Réessayer » qui relance le transfert sans dupliquer l'entrée.
3. **Given** une PME tente d'uploader un fichier `.exe` ou un PDF de 25 Mo, **When** elle confirme la sélection, **Then** le fichier est rejeté côté client avec un message clair (« Type non autorisé » ou « Taille maximale 20 Mo dépassée ») et n'apparaît pas dans la liste.
4. **Given** 6 fichiers sont sélectionnés simultanément, **When** l'upload démarre, **Then** seuls 5 fichiers sont transférés en parallèle et le 6ᵉ attend automatiquement la fin d'un transfert pour démarrer.

---

### User Story 2 — Recevoir et valider l'extraction OCR (Priority: P1)

Après upload, la PME visualise la progression de l'extraction (« Extraction en cours… »). Une fois prête, elle ouvre une fiche récapitulative présentant les champs extraits (raison sociale, effectifs, chiffre d'affaires, etc.) et peut **valider**, **corriger** ou **annuler** ces données. La validation propage les valeurs aux entités liées (entreprise, projet) et le document devient une source citable.

**Why this priority** : L'extraction validée est la **source vérifiée** (constitution P1) qui alimente le scoring ESG, les attestations et les candidatures. Sans ce flux, le document reste « brut » et inutilisable pour les modules avals.

**Independent Test** : Uploader un bilan PDF simple, attendre le statut « Vérifier », ouvrir la fiche, corriger un champ erroné, valider → l'entreprise est mise à jour, le document apparaît marqué comme « Validé » et citable.

**Acceptance Scenarios** :

1. **Given** un PDF vient d'être uploadé, **When** la PME ouvre l'onglet `/documents`, **Then** le document affiche le statut « Extraction en cours… » qui se met à jour automatiquement (sans rechargement manuel) jusqu'à atteindre « Vérifier » ou « Échec ».
2. **Given** l'extraction est terminée, **When** la PME clique sur « Vérifier », **Then** une fiche récapitulative s'ouvre listant chaque champ extrait avec sa valeur, son niveau de confiance et un contrôle d'édition par champ.
3. **Given** la PME corrige le champ « Effectifs » de 12 à 18 et valide, **Then** la fiche d'entreprise est mise à jour avec la valeur corrigée, le document est lié comme source, et un événement d'audit est enregistré (qui, quand, ancienne/nouvelle valeur).
4. **Given** l'extraction prend plus de 60 secondes, **When** la limite est atteinte, **Then** le statut passe à « Délai dépassé », une notification informe l'utilisateur, et une action « Relancer extraction » devient disponible (ne bloque pas la session).
5. **Given** une PME valide l'extraction, **When** elle revient plus tard, **Then** le document apparaît avec le statut « Validé » et les champs ne sont plus modifiables sans repasser par une action explicite « Re-corriger ».

---

### User Story 3 — Prévisualiser un document (Priority: P1)

La PME ouvre un document depuis la liste pour le visualiser sans téléchargement : PDF rendu inline, images affichées en plein cadre, fichiers bureautiques (Excel, Word) proposés en téléchargement avec un message explicatif.

**Why this priority** : Vérifier visuellement le contenu avant validation est essentiel pour la confiance dans l'extraction. C'est aussi nécessaire en candidature pour confirmer la pièce jointe.

**Independent Test** : Cliquer sur un PDF dans la liste → drawer latéral s'ouvre avec le document rendu, navigation par pages, fermeture sans interrompre la liste.

**Acceptance Scenarios** :

1. **Given** un PDF dans la liste, **When** la PME clique sur « Prévisualiser », **Then** un panneau latéral s'ouvre avec le PDF affiché, navigation page par page, et bouton de fermeture.
2. **Given** une image (JPG ou PNG), **When** la PME ouvre la prévisualisation, **Then** l'image est affichée à taille adaptée avec zoom possible.
3. **Given** un fichier Excel ou Word, **When** la PME ouvre la prévisualisation, **Then** un message « Prévisualisation indisponible pour ce format » s'affiche avec un bouton de téléchargement direct.

---

### User Story 4 — Documents au niveau d'un projet (Priority: P1)

Dans `/profil/projets/[id]`, la PME consulte une grille des documents rattachés au projet (vignettes + nom + tags). Elle peut uploader directement depuis cette page, et chaque document est associé au projet courant.

**Why this priority** : Les candidatures (F54) et le scoring projet s'appuient sur cette association projet/document. Sans cela, la traçabilité par projet est perdue.

**Independent Test** : Sur un projet existant, uploader un document depuis la zone projet → il apparaît dans la grille projet **et** dans la liste globale `/documents` avec un tag projet visible.

**Acceptance Scenarios** :

1. **Given** la PME est sur la page d'un projet, **When** elle uploade un document via la zone dédiée, **Then** le document est rattaché au projet et apparaît dans la grille projet ainsi que dans la liste globale `/documents`.
2. **Given** un document existe au niveau entreprise, **When** la PME le rattache à un projet via une action « Lier au projet », **Then** le tag projet est ajouté et le document devient visible dans la grille projet.

---

### User Story 5 — Rechercher, filtrer et organiser (Priority: P1)

La PME organise son corpus documentaire avec des **tags** éditables (ex. « Bilan 2024 », « Photo terrain », « Devis »), et retrouve rapidement un document par recherche par nom et filtres (type de fichier, plage de dates).

**Why this priority** : À 50+ documents, sans tag ni recherche, le corpus devient inutilisable. Tag est P1, filtres avancés P2.

**Independent Test** : Ajouter un tag « Bilan 2024 » à un PDF, rechercher « bilan » → le document apparaît en tête des résultats.

**Acceptance Scenarios** :

1. **Given** un document sans tag, **When** la PME ajoute le tag « Bilan 2024 » en édition inline, **Then** le tag est sauvegardé immédiatement et apparaît sur le document dans toutes les vues.
2. **Given** une liste de 50 documents, **When** la PME tape « bilan » dans le champ de recherche, **Then** seuls les documents dont le nom ou un tag contient « bilan » s'affichent (insensible à la casse et aux accents).
3. **Given** la PME applique un filtre « Type = PDF » et « Date entre 01/01/2026 et 30/04/2026 », **When** elle valide les filtres, **Then** la liste se restreint aux PDF dans la plage de dates indiquée.

---

### User Story 6 — Supprimer un document (Priority: P1)

La PME supprime un document obsolète. La suppression est confirmée par modal, est de type « soft » (récupérable côté admin), et le document disparaît immédiatement des listes.

**Why this priority** : Hygiène du corpus documentaire et respect du RGPD (droit à l'effacement). Soft delete préserve la traçabilité audit.

**Independent Test** : Supprimer un document, confirmer la modal → disparition immédiate de toutes les listes (entreprise et projet) ; le scoring qui le citait conserve une référence historique horodatée.

**Acceptance Scenarios** :

1. **Given** un document dans la liste, **When** la PME clique sur « Supprimer » et confirme la modal, **Then** le document disparaît des listes (entreprise et projets liés) et un événement d'audit est enregistré.
2. **Given** un document servait de source à un indicateur scoring, **When** il est supprimé, **Then** l'indicateur conserve l'horodatage de sa dernière source mais signale que la source n'est plus disponible.
3. **Given** la PME ouvre la modal de confirmation, **When** elle annule, **Then** le document reste intact et aucun événement n'est enregistré.

---

### User Story 7 — Synchronisation avec le chat conversationnel (Priority: P1)

Quand le chat (F41) demande un fichier via le bottom sheet `ask_file_upload`, le document uploadé est ajouté au corpus de la PME, visible immédiatement dans `/documents` sans rechargement.

**Why this priority** : Le chat est l'entrée principale de la plateforme. Une rupture entre upload chat et liste `/documents` casserait la cohérence (P8 sync bidirectionnelle).

**Independent Test** : Depuis le chat, uploader un fichier via le bottom sheet → ouvrir `/documents` dans un autre onglet → le fichier est présent sans recharger la page.

**Acceptance Scenarios** :

1. **Given** la PME est en conversation avec l'IA, **When** elle dépose un fichier via le bottom sheet `ask_file_upload`, **Then** le fichier apparaît dans `/documents` en moins de 3 secondes, avec le même statut OCR que pour un upload direct.
2. **Given** une extraction se termine sur un document uploadé via chat, **When** le statut change, **Then** la liste `/documents` reflète le nouveau statut sans rechargement manuel.

---

### User Story 8 — Relancer une extraction OCR (Priority: P2)

Si l'OCR retourne un résultat médiocre ou échoue, la PME peut « Relancer l'extraction » depuis la fiche document.

**Why this priority** : Améliore le taux de réussite final mais n'est pas bloquant : la correction manuelle reste possible.

**Independent Test** : Sur un document avec extraction « Échec » ou « Faible confiance », cliquer « Relancer extraction » → le statut repasse à « En cours » puis à un nouveau résultat.

**Acceptance Scenarios** :

1. **Given** un document avec un statut « Faible confiance », **When** la PME clique sur « Relancer extraction », **Then** le statut passe à « Extraction en cours… » et un nouveau résultat est produit.
2. **Given** un document validé, **When** la PME tente de relancer, **Then** une confirmation est demandée (« La validation actuelle sera invalidée ») avant relance.

---

### Edge Cases

- **Fichier corrompu ou illisible** → upload OK mais OCR échoue ; statut « Extraction impossible » avec recommandation « Re-uploader le fichier ».
- **Nom de fichier dangereux** (`../../etc/passwd.pdf`, caractères Unicode invisibles) → assainissement côté client ET côté serveur, nom affiché nettoyé, fichier stocké sous identifiant interne.
- **MIME spoofing** (`.exe` renommé `.pdf`) → la validation côté serveur lit la signature du fichier ; rejet avec message clair côté client si la signature ne correspond pas.
- **Connexion 4G instable pendant l'upload** → reprise sur le même fichier sans duplication ; barre de progression conservée.
- **OCR très long (> 60 s)** → statut « Délai dépassé », notification non bloquante, possibilité de relancer plus tard.
- **Liste de 200+ documents** → virtualisation de la table pour conserver la fluidité.
- **Fuite inter-tenant** → un document d'un autre compte ne doit jamais être visible ou récupérable, même via URL directe ou ID deviné (réponse de type « non trouvé », pas « interdit »).
- **Sécurité** : pas de prévisualisation d'un document non scanné par l'antivirus côté backend (statut « Analyse en cours » jusqu'à validation).
- **Document supprimé puis cherché par recherche** → n'apparaît plus dans les résultats utilisateur.
- **Tag avec caractères spéciaux** (emojis, accents, ponctuation) → accepté mais limité à 40 caractères ; pas de tag vide.
- **Re-upload du même fichier** → la plateforme calcule une empreinte de contenu côté client et côté serveur ; si une entrée non supprimée du même compte présente la même empreinte, l'utilisateur est averti **avant transfert** avec deux choix explicites : « Réutiliser le document existant » (aucun nouvel envoi) ou « Forcer un nouvel envoi » (création d'une entrée distincte assumée). En cas de « réutilisation », un éventuel rattachement projet de la session courante est ajouté à l'entrée existante.

## Requirements *(mandatory)*

### Functional Requirements

#### Upload et gestion du corpus

- **FR-001** : Le système DOIT permettre à une PME authentifiée d'uploader un ou plusieurs documents simultanément depuis la page `/documents` et depuis la zone projet `/profil/projets/[id]` via glisser-déposer ou sélection de fichiers.
- **FR-002** : Le système DOIT accepter uniquement les types de fichiers suivants : PDF, JPG, PNG, XLSX, DOCX. Tout autre type DOIT être rejeté côté client (UX immédiate) et côté serveur (sécurité).
- **FR-003** : Le système DOIT rejeter tout fichier dont la taille dépasse 20 Mo avec un message clair indiquant la limite.
- **FR-004** : Le système DOIT afficher une barre de progression individuelle par fichier pendant l'upload, avec actions « Annuler » et « Réessayer ».
- **FR-005** : Le système DOIT limiter le nombre d'uploads simultanés à 5 ; les fichiers supplémentaires DOIVENT être mis en file d'attente et démarrés automatiquement.
- **FR-006** : Le système DOIT assainir les noms de fichiers à la réception (suppression des chemins, caractères de contrôle, séquences `..`) côté client ET côté serveur, et stocker le fichier sous un identifiant interne.
- **FR-006b** : Avant chaque envoi, le système DOIT calculer une empreinte de contenu du fichier ; si une entrée non supprimée du même compte présente la même empreinte, l'utilisateur DOIT être averti et DOIT choisir explicitement entre « Réutiliser le document existant » (pas de nouvel envoi, rattachement projet de la session courante ajouté à l'entrée existante) ou « Forcer un nouvel envoi » (création d'une entrée distincte). Sans choix, l'envoi N'EST PAS effectué.
- **FR-007** : Le système DOIT afficher la liste des documents de l'entreprise sous forme de table virtualisée présentant : nom, type, date d'upload, statut OCR, taille, actions (prévisualiser, supprimer, gérer tags).
- **FR-007b** : Si la liste de documents de l'entreprise est vide, la page `/documents` DOIT afficher un **empty state** structuré comprenant une illustration sobre, un texte d'accompagnement explicatif (« Téléversez vos premiers documents pour démarrer votre profil ESG »), et un **CTA primaire « Téléverser mon premier document »** qui ouvre immédiatement la zone d'upload.
- **FR-008** : Le système DOIT afficher dans `/profil/projets/[id]` une grille (vignettes + nom + tags) des documents rattachés au projet et permettre l'upload directement depuis cette page.
- **FR-008b** : Si aucun document n'est rattaché au projet courant, la grille DOIT afficher un **empty state** propre au projet (illustration, texte d'accompagnement contextualisé au projet, CTA primaire « Téléverser un document pour ce projet ») même si l'entreprise a déjà des documents au niveau global.
- **FR-009** : Le système DOIT permettre de rattacher un document existant à un ou plusieurs projets et de retirer chaque rattachement indépendamment ; un même document peut figurer simultanément dans la grille de plusieurs projets sans duplication du fichier sous-jacent.

#### OCR et extraction structurée

- **FR-010** : Le système DOIT afficher pour chaque document un statut d'extraction OCR : « Extraction en cours… », « Vérifier », « Validé », « Faible confiance », « Échec », « Délai dépassé ».
- **FR-011** : Le système DOIT mettre à jour le statut OCR à l'écran sans rechargement manuel de la page (par interrogation périodique au plus toutes les 2 s, plafond global 60 s).
- **FR-012** : Le système DOIT, à l'expiration du délai de 60 s, présenter un statut « Délai dépassé » avec notification non bloquante et action « Relancer extraction ».
- **FR-013** : Le système DOIT, à l'état « Vérifier », ouvrir une fiche récapitulative listant les champs extraits (raison sociale, effectifs, chiffre d'affaires, etc.) avec le niveau de confiance par champ.
- **FR-014** : La PME DOIT pouvoir éditer chaque champ extrait, valider l'ensemble, ou annuler la validation depuis la fiche.
- **FR-015** : À la validation, le système DOIT propager les valeurs aux entités liées (entreprise, projet selon le rattachement) et lier le document comme **source citable** des valeurs persistées.
- **FR-016** : Toute mutation d'entité (création, correction, validation) issue de l'extraction DOIT générer un événement d'audit append-only précisant l'utilisateur, l'horodatage, le champ, l'ancienne valeur, la nouvelle valeur et la source du changement.
- **FR-017** : La PME DOIT pouvoir relancer une extraction OCR à tout moment ; sur un document déjà validé, la relance DOIT exiger une confirmation explicite et invalider la validation précédente.

#### Prévisualisation

- **FR-018** : Le système DOIT proposer une prévisualisation inline pour les PDF (navigation par pages) et pour les images (JPG, PNG) dans un panneau latéral.
- **FR-019** : Pour les formats Excel et Word, le système DOIT afficher un message d'indisponibilité de prévisualisation et proposer un téléchargement direct.
- **FR-020** : La prévisualisation DOIT être chargée de manière paresseuse (le moteur de rendu PDF n'est chargé qu'à l'ouverture d'un PDF).

#### Recherche, tags, suppression

- **FR-021** : La PME DOIT pouvoir éditer des tags sur un document en édition inline ; chaque tag fait au maximum 40 caractères et ne peut pas être vide.
- **FR-022** : Le système DOIT proposer une recherche par nom de document, insensible à la casse et aux accents, retournant les résultats en moins d'une seconde sur un corpus de 200 documents.
- **FR-023** : Le système DOIT proposer des filtres par type de fichier et par plage de dates d'upload.
- **FR-024** : La suppression d'un document DOIT être confirmée par une modal explicite et appliquer un effacement de type « soft » : le document disparaît immédiatement des listes utilisateur et reste récupérable côté admin pendant **30 jours** à compter de la suppression. À l'issue de ces 30 jours, une **purge dure automatique** supprime définitivement le fichier et ses extractions associées (l'événement d'audit, lui, est conservé).
- **FR-025** : Le système DOIT enregistrer un événement d'audit pour chaque suppression.

#### Synchronisation chat

- **FR-026** : Tout document uploadé via le chat (bottom sheet `ask_file_upload`) DOIT apparaître dans `/documents` en moins de 3 secondes sans rechargement, avec son statut OCR à jour.
- **FR-027** : Tout changement de statut OCR survenant côté backend DOIT se refléter automatiquement dans toutes les vues ouvertes (liste, fiche, grille projet).

#### Accessibilité

- **FR-A11Y-001** : L'ensemble de l'UI F50 (page `/documents`, grille projet, drawer de prévisualisation, fiche d'extraction, modals de confirmation, bottom sheet d'upload chat) DOIT respecter **WCAG 2.1 niveau AA** : contrastes textuels ≥ 4.5:1 (≥ 3:1 pour les éléments graphiques et grands textes), navigation clavier complète sans piège, focus visible, ordre de tabulation logique, libellés ARIA pour tous les contrôles non textuels (drag & drop, barres de progression, statuts OCR, actions de la table virtualisée).
- **FR-A11Y-002** : Les statuts OCR dynamiques et les changements de barre de progression DOIVENT être annoncés aux technologies d'assistance via des régions ARIA `live` appropriées (polite pour les progrès, assertive pour les erreurs et l'expiration de délai).
- **FR-A11Y-003** : Le drag & drop d'upload DOIT proposer un parcours alternatif clavier/bouton équivalent pour les utilisateurs ne pouvant pas faire de drag & drop à la souris ou au tactile.

#### Sécurité et isolation

- **FR-028** : Tout document DOIT être strictement isolé par compte ; tout accès cross-tenant (URL directe, ID deviné) DOIT renvoyer une réponse de type « non trouvé » (sans révéler l'existence de la ressource dans un autre compte).
- **FR-029** : Le système DOIT bloquer la prévisualisation et le téléchargement de tout document qui n'a pas passé l'étape de scan antivirus côté backend ; un statut intermédiaire « Analyse en cours » est affiché.
- **FR-030** : Toute saisie déclenchée dans un échange conversationnel (notamment l'upload depuis le chat) DOIT s'effectuer dans un bottom sheet animé, et non en ligne dans la bulle de l'IA. Une option « Répondre librement » DOIT toujours être disponible pour basculer en saisie texte.

### Key Entities *(include if feature involves data)*

- **Document** : pièce déposée par la PME (PDF, image, fichier bureautique). Attributs principaux : nom affiché, nom assaini, type MIME, taille, identifiant de stockage interne, date d'upload, auteur, statut antivirus, statut OCR, projet de rattachement éventuel, tags, indicateur soft-delete.
- **Extraction OCR** : résultat structuré associé à un document, contenant un ensemble de champs extraits avec niveau de confiance, statut (en cours, prêt, validé, échec, expiré), horodatages de début/fin, source du moteur d'extraction.
- **Validation** : trace immuable de la validation d'une extraction par la PME, incluant l'ensemble des champs validés ou corrigés, l'horodatage, l'auteur, et les entités impactées.
- **Tag** : étiquette textuelle libre rattachée à un document.
- **Lien projet** : association explicite entre un document et un projet de la PME ; relation **many-to-many** — un document peut être lié à 0..N projets, et chaque rattachement est créé/retiré indépendamment.
- **Événement d'audit** : trace append-only liée à toute mutation (upload, validation, correction, suppression, relance OCR).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME peut téléverser 3 PDF de 5 à 18 Mo simultanément sur un réseau 4G (~5 Mbps montants) en moins de 60 secondes par fichier, avec progression visible en continu.
- **SC-002** : 95 % des extractions OCR sur un PDF de moins de 5 pages aboutissent à un statut « Vérifier » en moins de 30 secondes ; le statut s'affiche à l'utilisateur sans rechargement manuel.
- **SC-003** : 90 % des PME parviennent à valider l'extraction d'un bilan en moins de 2 minutes lors de leur première utilisation (mesuré par session utilisateur).
- **SC-004** : Aucun document d'un autre compte n'est jamais accessible (taux de fuite inter-tenant = 0 sur l'ensemble des tests d'autorisation et des audits).
- **SC-005** : Sur un corpus de 200 documents, la liste reste fluide (interaction perçue sous 100 ms) et la recherche par nom retourne des résultats en moins d'une seconde.
- **SC-006** : Un document supprimé disparaît des listes utilisateur en moins de 500 ms après confirmation et n'apparaît plus dans la recherche ni dans la grille projet.
- **SC-007** : Un document uploadé depuis le chat apparaît dans `/documents` en moins de 3 secondes sans rechargement.
- **SC-008** : 100 % des fichiers déposés dont le type ou la taille ne respectent pas les contraintes sont rejetés avec un message explicite avant transfert réseau.
- **SC-009** : Un audit automatisé d'accessibilité des pages et composants F50 ne révèle **aucune violation WCAG 2.1 AA** de niveau « serious » ou « critical ». Les parcours principaux (upload, validation extraction, prévisualisation, suppression) sont entièrement réalisables au clavier seul.

## Assumptions

- Les fonctionnalités backend de stockage et de pipeline OCR (F22) sont opérationnelles et exposent les endpoints nécessaires (upload, statut OCR, payload extraction, suppression soft, scan antivirus).
- Les composants transverses sont disponibles : `<UiFileUpload>` (F37), `<ShowSummaryCard>` (F39), bottom sheet engine (F39), design tokens (F36), shell de navigation (F38), couche conversationnelle (F41), page projets (F43).
- Le moteur OCR est paramétré pour le français par défaut ; le multilingue (arabe, langues locales) est explicitement hors-scope MVP.
- Le scan antivirus côté backend est assuré (par exemple via clamav ou un service tiers) ; aucune exposition utilisateur tant que l'analyse n'est pas terminée.
- Rétention soft-delete fixée à **30 jours** côté admin avant purge dure automatique du fichier et de ses extractions ; les événements d'audit liés sont conservés au-delà selon la politique d'audit globale.
- Un document peut être lié simultanément à plusieurs projets (relation many-to-many) ; le fichier sous-jacent reste unique et n'est pas dupliqué lors du rattachement.
- L'authentification PME est gérée par le système d'auth existant ; cette spécification n'introduit pas de nouveau mécanisme.
- Volumes attendus en MVP : jusqu'à 200 documents par PME ; au-delà, la pagination/virtualisation reste fonctionnelle mais n'est pas optimisée pour le scroll infini illimité.

## Hors-scope MVP

- Annotation collaborative sur les PDF.
- Comparaison de versions de documents.
- OCR multilingue avancé (arabe, langues locales).
- Signature électronique des documents.
- Reprise d'upload segmentée pour très gros fichiers > 20 Mo.

## Dependencies

- **Backend F22** : pipeline storage + OCR (upload, polling statut, payload extraction, suppression, scan antivirus).
- **F36** Design tokens, **F37** UI primitives (notamment `<UiFileUpload>`), **F38** App shell & navigation.
- **F39** Bottom sheet engine + `<ShowSummaryCard>`.
- **F40** Bibliothèque de visualisation (vignettes).
- **F41** Couche conversationnelle (intégration `ask_file_upload`).
- **F43** Page profil entreprise/projets (point d'embed pour la grille projet).
