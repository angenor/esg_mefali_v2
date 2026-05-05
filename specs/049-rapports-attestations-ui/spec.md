# Feature Specification: Rapports PDF & Page publique /verify (UI F24 + F30)

**Feature Branch**: `049-rapports-attestations-ui`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "F49 — UI de gestion des rapports PDF (page PME `/rapports`) et page publique de vérification d'attestation `/verify/{id}` signée Ed25519. Vitrine produit majeure (banques, fonds)."

## Clarifications

### Session 2026-05-04

- Q: Mécanisme de feedback de progression pour la génération d'un rapport ? → A: Flux serveur (SSE) pendant la modale + rattrapage automatique au retour sur `/rapports` (état persisté côté serveur).
- Q: Stratégie de fraîcheur de `/verify/{id}` après révocation ? → A: SSR + cache CDN court (TTL ≤ 60 s) + invalidation explicite déclenchée à la révocation.
- Q: Le motif de révocation est-il obligatoire et public ? → A: Obligatoire, choisi dans une liste fermée de catégories prédéfinies, toujours affiché publiquement.
- Q: Sécurité multi-tenant de l'aperçu PDF inline ? → A: URL signée à durée de vie courte (≤ 5 min), vérifiée côté serveur, expirant après usage ou délai.
- Q: Portée du bilingue FR/EN sur `/verify/{id}` ? → A: Libellés statiques + valeurs énumérées contrôlées (type d'attestation, motif de révocation, libellés d'indicateurs standards) basculent ; les données saisies PME (raison sociale, valeurs, sources) restent inchangées.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Liste et téléchargement des rapports (Priority: P1)

Une PME authentifiée ouvre `/rapports` pour consulter et télécharger tous ses rapports PDF (Conformité, Carbone, Candidature) et ses attestations actives.

**Why this priority** : c'est la valeur de sortie tangible de la plateforme — la PME doit pouvoir récupérer ses livrables à tout moment pour les transmettre à des tiers (banque, fonds, audit).

**Independent Test** : un utilisateur connecté avec ≥1 rapport généré peut ouvrir `/rapports`, voir le rapport en table, le télécharger en PDF et l'ouvrir hors ligne.

**Acceptance Scenarios** :

1. **Given** une PME possédant 5 rapports et 2 attestations, **When** elle ouvre `/rapports`, **Then** elle voit deux tables (rapports / attestations) avec colonnes titre, type, date, taille, statut.
2. **Given** un rapport listé, **When** l'utilisateur clique « Télécharger », **Then** le PDF se télécharge avec le nom de fichier explicite (entreprise + type + date).
3. **Given** un clic sur une ligne de rapport, **When** la ligne s'ouvre, **Then** un panneau latéral droit affiche un aperçu PDF inline + métadonnées (référentiel, période, taille, hash).

---

### User Story 2 - Génération d'un nouveau rapport (Priority: P1)

La PME demande la génération d'un nouveau rapport (type, référentiel, période) et reçoit un retour de progression jusqu'au lien de téléchargement.

**Why this priority** : sans génération, la liste reste vide. C'est le déclencheur du cycle de production.

**Independent Test** : depuis `/rapports`, l'utilisateur ouvre la modale « Nouveau rapport », sélectionne un type + référentiel + période, valide, et obtient un lien de téléchargement actif à la fin.

**Acceptance Scenarios** :

1. **Given** la modale ouverte, **When** type et période sont vides, **Then** le bouton de validation est désactivé.
2. **Given** une demande soumise, **When** la génération est en cours, **Then** un indicateur de progression visuel reste visible et l'UI ne se fige pas.
3. **Given** la génération terminée, **When** elle réussit, **Then** un lien « Télécharger » apparaît et la liste des rapports se met à jour automatiquement.
4. **Given** une génération qui échoue, **When** l'erreur remonte, **Then** un message lisible explique le motif et propose « Réessayer ».

---

### User Story 3 - Partage et révocation d'attestation (Priority: P1)

La PME partage l'URL publique d'une attestation à une banque (ou la révoque si elle a été émise par erreur).

**Why this priority** : l'attestation est le canal de confiance entre la PME et un décideur financier (P7 : pas de webhook, uniquement partage manuel via URL/QR signée).

**Independent Test** : ouvrir le menu d'une attestation active, copier le lien `/verify/{id}`, télécharger le QR PNG, puis exécuter une révocation et vérifier que le statut bascule.

**Acceptance Scenarios** :

1. **Given** une attestation active, **When** l'utilisateur clique « Partager », **Then** une modale affiche l'URL `/verify/{id}` copiable et un QR code téléchargeable en PNG.
2. **Given** une attestation active, **When** l'utilisateur clique « Révoquer » et confirme, **Then** l'attestation passe au statut « révoquée » avec date du jour et motif.
3. **Given** une attestation révoquée, **When** l'utilisateur revient sur la liste, **Then** le statut révoqué est visible et l'action « Partager » est désactivée.

---

### User Story 4 - Vérification publique sans login (Priority: P1)

Un décideur (banquier, investisseur) ouvre `/verify/{id}` depuis un QR code ou un lien direct, sans compte, et obtient un verdict de signature clair en moins de 1,2 s.

**Why this priority** : page vitrine produit, première impression côté financeur. Si elle échoue ou est lente, la confiance s'effondre.

**Independent Test** : ouvrir l'URL `/verify/{id-valide}` en navigation privée → la page s'affiche avec badge ✓, raison sociale, type d'attestation, dates, contenu lisible. Aucun login requis. Aucun lien retour vers l'app PME.

**Acceptance Scenarios** :

1. **Given** une attestation valide, **When** un visiteur non authentifié ouvre l'URL, **Then** la page affiche un badge ✓ « Signature valide », la raison sociale, le type d'attestation, les dates émission/expiration.
2. **Given** une attestation révoquée, **When** la page est ouverte, **Then** un badge rouge « RÉVOQUÉE le YYYY-MM-DD » + motif s'affiche au-dessus du contenu.
3. **Given** une attestation à signature invalide ou inexistante, **When** la page est ouverte, **Then** un badge ✗ explicite est rendu (pas un crash) avec un message sobre.
4. **Given** l'arrêt du backend, **When** la page est demandée, **Then** une page d'erreur sobre est rendue (pas de crash, pas de leak technique).

---

### User Story 5 - Détails contenus, sources et sobriété (Priority: P1)

La page `/verify/{id}` permet au décideur de lire en détail les KPI attestés et les sources, en lecture seule, dans un design sobre et professionnel sans branding intrusif.

**Why this priority** : c'est ce qui transforme la simple « preuve cryptographique » en « décision pouvant être prise ».

**Independent Test** : sur une attestation valide, vérifier qu'on lit les KPI, qu'on peut consulter chaque source attachée, qu'aucun lien ne ramène vers l'app authentifiée, et que le footer affiche les mentions légales + RGPD + lien `/about`.

**Acceptance Scenarios** :

1. **Given** une attestation valide, **When** la page est rendue, **Then** la charge utile (KPI, indicateurs) est lisible avec un repère de source pour chaque assertion.
2. **Given** un visiteur sur la page, **When** il scrute la page, **Then** il voit un en-tête avec logo, un footer avec mentions légales / RGPD / lien `/about`, et **aucun** lien retour vers l'app PME.
3. **Given** la page chargée, **When** le visiteur lit, **Then** un encart « Qu'est-ce qu'une attestation ESG Mefali ? » fournit un contexte avec lien doc.

---

### User Story 6 - Bilingue FR/EN sur la page publique (Priority: P2)

Un visiteur anglophone (banque internationale) bascule en EN via un sélecteur visible.

**Why this priority** : élargit l'audience aux financeurs non francophones, mais le MVP fonctionne en FR seul si nécessaire.

**Independent Test** : sur `/verify/{id}`, cliquer sur le sélecteur FR/EN → l'ensemble du contenu statique de la page change de langue. La donnée attestée (raison sociale, KPI) reste inchangée.

**Acceptance Scenarios** :

1. **Given** la page en français, **When** l'utilisateur clique « EN », **Then** les libellés statiques passent en anglais et la préférence est persistée pour la session.

---

### Edge Cases

- Identifiant `/verify/{id}` malformé ou inexistant → page d'erreur 404 sobre, pas de stack trace.
- Aucun rapport ni attestation pour la PME → empty state explicite avec call-to-action « Générer mon premier rapport ».
- Génération de rapport qui dépasse une durée raisonnable (>5 min) → l'UI doit rester non bloquante et l'utilisateur peut quitter `/rapports` puis revenir voir l'état final.
- Aperçu PDF impossible (PDF corrompu) → l'aperçu affiche un message dédié et garde le bouton « Télécharger » actif.
- Visiteur public désactive JavaScript → l'essentiel de `/verify/{id}` reste lisible (verdict signature, raison sociale, dates, KPI principaux).
- Attestation appartenant à une autre PME → `/verify/{id}` ne doit jamais exposer plus que les champs explicitement publics.
- Tentative de scan QR sur écran à mauvaise résolution → le QR doit rester scannable jusqu'à 4 cm de côté.

## Requirements *(mandatory)*

### Functional Requirements

#### Page `/rapports` (PME authentifiée)

- **FR-001** : `/rapports` affiche une table des rapports (titre, type ∈ {Conformité, Carbone, Candidature}, date, taille, statut) avec actions « Télécharger » et « Régénérer ».
- **FR-002** : Cliquer sur une ligne ouvre un panneau latéral droit avec un aperçu PDF inline + métadonnées (référentiel, période, hash, source). L'aperçu utilise une URL signée à durée de vie courte (≤ 5 min) émise à la demande, vérifiée côté serveur contre la session PME, et expirant après usage ou délai (aucune URL d'aperçu permanente ou partageable n'est exposée au navigateur).
- **FR-003** : Une action « Nouveau rapport » ouvre une modale (type, référentiel, période) et déclenche la génération côté serveur ; la progression est livrée via un flux serveur (SSE) tant que la modale est ouverte, et le système persiste l'état de la demande pour permettre un rattrapage si l'utilisateur quitte la page.
- **FR-003a** : Au retour sur `/rapports`, toute demande de génération encore en cours est automatiquement reconnectée (re-souscription au flux serveur) et toute demande achevée pendant l'absence est visible dans la table avec son lien de téléchargement.
- **FR-004** : `/rapports` affiche une seconde table des attestations (mini-QR, type, statut ∈ {active, expirée, révoquée}, dates) avec actions « Partager » et « Révoquer ».
- **FR-005** : L'action « Partager » ouvre une modale avec l'URL `/verify/{id}` copiable + QR PNG téléchargeable.
- **FR-006** : L'action « Révoquer » exige une confirmation explicite et bascule l'attestation en « révoquée » (date du jour + motif **obligatoire** choisi dans une liste fermée : `erreur_emission`, `donnees_invalidees`, `demande_pme`, `expiration_anticipee`, `autre`).
- **FR-007** : `/rapports` exige une session PME authentifiée et n'expose jamais les données d'une autre PME.

#### Page publique `/verify/{id}`

- **FR-010** : `/verify/{id}` est accessible **sans authentification** et n'expose **aucun lien** vers l'app PME ni vers une autre attestation.
- **FR-011** : La page affiche un verdict de signature clair (badge ✓ « valide » ou ✗ « invalide »), la raison sociale, le type d'attestation, les dates d'émission et d'expiration.
- **FR-012** : Si l'attestation est révoquée, un bandeau rouge « RÉVOQUÉE le YYYY-MM-DD » avec le motif (libellé issu de la liste fermée, jamais de texte libre) sont affichés en haut, above-the-fold.
- **FR-013** : La page affiche la charge utile lisible (KPI, indicateurs) avec un repère de source pour chaque assertion attestée (cohérent avec l'invariant P1 Sourcing).
- **FR-014** : La vérification de signature est faite côté serveur ; aucune cryptographie n'est exécutée côté navigateur.
- **FR-015** : La page est rendue côté serveur pour l'indexation, le partage social et la résilience sans JavaScript ; un cache CDN à TTL court (≤ 60 s) est autorisé, et la révocation d'une attestation déclenche une invalidation explicite de l'entrée correspondante afin que le statut révoqué apparaisse aux nouveaux visiteurs en quelques secondes.
- **FR-016** : Le contenu essentiel (verdict, raison sociale, dates, KPI) reste lisible sans JavaScript activé.
- **FR-017** : La page est mobile-first et s'affiche correctement sur écrans de 320 px à 1920 px.
- **FR-018** : Si le service de vérification est indisponible, une page d'erreur sobre est rendue (pas de crash, pas de stack trace, pas de fuite technique).
- **FR-019** : La page expose les balises de partage social adaptées (titre, image OG, description) et un schéma structuré décrivant l'organisation et la certification.
- **FR-020** : Un en-tête contient uniquement le logo et un sélecteur FR/EN ; un pied de page contient mentions légales + lien RGPD + lien `/about`.
- **FR-021** : Un encart pédagogique « Qu'est-ce qu'une attestation ESG Mefali ? » est présent avec un lien vers la documentation publique.
- **FR-022** : Le sélecteur FR/EN bascule (a) les libellés statiques de la page (en-tête, footer, badges, encart pédagogique, libellés de dates) **et** (b) les valeurs énumérées contrôlées (type d'attestation, motif de révocation, libellés d'indicateurs standards) entre les deux langues. Les données saisies par la PME (raison sociale, valeurs numériques, libellés de sources externes) ne sont jamais traduites. La préférence est persistée pour la session.

### Key Entities

- **Rapport** : livrable PDF généré pour une PME — type (Conformité / Carbone / Candidature), référentiel, période, date de génération, taille, statut, hash. Lié à une PME unique (multi-tenant).
- **Attestation** : objet vérifiable cryptographiquement signé — identifiant public opaque, raison sociale émettrice, type, dates émission/expiration, statut (active / expirée / révoquée), motif de révocation (catégorie issue d'une liste fermée), charge utile (KPI + sources).
- **Demande de génération** : déclenchée par la PME — type, référentiel, période, état (en cours / réussi / échoué), résultat (lien rapport).
- **Source** : référence justifiant un KPI affiché dans une attestation, exposée publiquement sur `/verify/{id}` mais sans jamais leaker au-delà du périmètre de l'attestation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Sur `/rapports`, une PME ayant ≥1 rapport peut le télécharger en moins de 2 clics depuis l'arrivée sur la page.
- **SC-002** : 95 % des générations de rapport aboutissent à un lien de téléchargement opérationnel dans une session ou notification d'achèvement, sans rechargement manuel répété.
- **SC-003** : Sur `/verify/{id-valide}`, le visiteur voit le verdict ✓ et les détails essentiels en moins de 1,2 s sur connexion 4G de référence.
- **SC-004** : Sur `/verify/{id-révoqué}`, le bandeau de révocation est visible sans défilement (above-the-fold) sur écran 320×568 px.
- **SC-005** : Le score Lighthouse de `/verify/{id}` est ≥ 95 sur les axes Performance, Accessibilité, Bonnes Pratiques et SEO en mobile.
- **SC-006** : QR code scannable au premier essai sur 5 modèles de téléphones courants (3 Android + 2 iOS) à une distance de 30 cm.
- **SC-007** : 0 incident de fuite multi-tenant : aucune URL `/verify/{id}` ne révèle de données d'une PME tierce.
- **SC-008** : La page publique reste lisible (verdict + identité + dates) avec JavaScript désactivé, vérifiable manuellement par audit.
- **SC-009** : Sur révocation par la PME, l'effet est visible publiquement sur `/verify/{id}` en moins de 60 s pour tout nouveau visiteur, grâce à l'invalidation explicite du cache CDN couplée au TTL court.

## Assumptions

- Les endpoints backend de génération de rapport (F24) et de vérification d'attestation (F30) sont disponibles et stables, y compris la signature Ed25519 et la lecture publique.
- Le layout public et les primitives UI (F36, F37, F38, F40) sont disponibles : `/verify/{id}` réutilise le layout `public.vue` sans dépendance auth.
- L'identifiant public d'attestation est un opaque non-énumérable (pas un entier séquentiel), évitant l'énumération.
- Le QR code encode l'URL absolue de `/verify/{id}` (pas un payload signé localement) — la confiance vient de la vérification serveur.
- La langue par défaut de la plateforme est le français ; l'anglais est limité à la page publique et n'affecte pas l'app PME.
- L'aperçu PDF inline est un confort utilisateur : si le navigateur ne sait pas l'afficher, le bouton de téléchargement reste suffisant.
- Les progrès de génération longue peuvent être livrés par poll ou flux serveur — l'UX exige uniquement « non-bloquant » et « état final fiable ».
- L'expiration d'attestation est calculée côté serveur ; le front affiche l'état renvoyé sans recalcul local.
- L'audit append-only et la traçabilité de la révocation sont gérés par le backend (P3).
