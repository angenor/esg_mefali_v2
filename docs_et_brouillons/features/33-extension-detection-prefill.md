# F33 — Extension Chrome — Détection sites, observation SPA, pré-remplissage IA, i18n

**Phase** : 11 — Extension Chrome (Module 8)
**Modules brainstorm** : 8.1 (Détection Automatique), 8.2 (Pré-remplissage Intelligent), 8.7 (Multilingue)
**Dépendances** : F11, F12, F25
**Estimation** : 3 jours

## Contexte et objectif

Une extension Chrome qui **accompagne la PME** quand elle navigue sur les sites des **fonds source ET des intermédiaires** (souvent là où les formulaires réels se remplissent : portails BOAD, plateformes SUNREF banques, formulaires GCF, etc.).

> **Important** : pas un point d'accès pour les intermédiaires — c'est un outil **pour la PME** qui va sur leurs portails.

Cette feature livre :
- Détection automatique des sites pertinents (fonds + intermédiaires),
- Observation SPA pour les sites modernes,
- Bandeau de notification discret quand une Offre compatible est détectée,
- Pré-remplissage IA des formulaires depuis le profil,
- i18n FR/EN.

F34 livrera le panneau latéral de guidage, suivi candidatures, notifications, recommandations.

## User Stories

### US1 — Installer et connecter l'extension (P1)
**En tant que** PME,
**je veux** installer l'extension Chrome (depuis le Web Store ou via fichier `.crx` MVP) et me connecter avec mes identifiants ESG Mefali (JWT issu de F02),
**afin de** lier l'extension à mon compte.

**Test indépendant** : popup extension propose login → API `/auth/login` → JWT stocké en `chrome.storage.local`.

### US2 — Détecter automatiquement un site fonds/intermédiaire (P1)
**En tant que** PME,
**je veux** que l'extension détecte automatiquement les URLs de fonds (gcf.org, afdb.org, boad.org, afd.fr…) et d'intermédiaires (ecobank.com/sunref, nsia.com, plateformes PNUD…) et affiche un bandeau discret en haut de page : "ESG Mefali : Offre 'GCF via BOAD' détectée — Voir détails".
**afin de** être guidée pile au moment où je navigue.

**Mécanisme** : patterns d'URL configurables côté backend, fetch périodique par l'extension.

### US3 — Observation des SPA (P1)
**En tant que** PME naviguant sur un portail moderne (Vue/React/Angular),
**je veux** que l'extension détecte les changements de route SPA (sans reload),
**afin de** que le bandeau s'adapte à la sous-page (ex : page "appel à projets" vs "soumission").

**Implémentation** : MutationObserver + `history.pushState` hooks.

### US4 — Pré-remplissage automatique des formulaires (P1)
**En tant que** PME,
**je veux** sur un formulaire détecté, un bouton "Tout remplir automatiquement" qui :
- analyse les champs (label, name, type),
- mappe avec mes données profil entreprise (F11) + projet (F12),
- remplit les champs reconnus, code-couleur :
  - **vert** : auto-rempli avec valeur exacte du profil,
  - **bleu** : suggéré par IA (ex : description projet adaptée au format),
  - **orange** : à remplir manuellement (pas de match).

**afin de** gagner un temps fou.

### US5 — Remplissage séquentiel animé (P2)
**En tant que** PME,
**je veux** voir le remplissage se faire **champ par champ** avec une légère animation (gsap),
**afin de** comprendre ce qui s'est passé (vs un remplissage instantané intimidant).

### US6 — Suggestions IA contextuelles par champ (P1)
**En tant que** PME sur un champ "Description du projet (1500 caractères max)",
**je veux** un mini-bouton "Suggérer un texte" qui invoque le LLM avec contexte projet + offre + format → génère une description adaptée,
**afin de** rédiger en un clic.

### US7 — i18n FR/EN (P1)
**En tant que** PME,
**je veux** une interface extension en français (par défaut) ou anglais (selon préférence ou détection langue OS),
**afin de** travailler dans ma langue.

**Stack** : `chrome.i18n` API.

### US8 — Adaptation au format de l'intermédiaire (P1)
**En tant que** PME sur le portail SUNREF Ecobank vs sur un portail PNUD,
**je veux** que les suggestions IA s'adaptent au format spécifique de l'intermédiaire (ton, longueur, vocabulaire),
**afin de** chaque dossier soit pertinent.

**Mécanisme** : utilise les Skills `skill_dossier_*` (F21) selon l'Offre détectée.

## Exigences fonctionnelles

- **FR-001** : Structure extension Chrome (Manifest V3) :
  - `manifest.json`,
  - `background.js` (service worker),
  - `content.js` (injecté dans pages),
  - `popup.html` (popup extension),
  - `panel.html` (panneau latéral, livré en F34),
  - dossiers i18n `_locales/fr/messages.json`, `_locales/en/messages.json`.
- **FR-002** : Backend endpoints dédiés extension :
  - `GET /extension/url-patterns` → liste des patterns d'URL fonds/intermédiaires + Offres associées (consomme F08).
  - `GET /extension/profile-summary` → version compactée du profil (cohérent F18 compaction).
  - `POST /extension/suggest-field` body `{field_label, field_max_length, projet_id, offre_id}` → texte suggéré par LLM.
- **FR-003** : Module `url_pattern_matcher.js` côté extension : compare l'URL courante contre les patterns, retourne l'Offre/Fonds/Intermédiaire détecté.
- **FR-004** : Module `field_mapper.js` côté extension : analyse les champs du formulaire (DOM), tente un mapping :
  - heuristique sur `label`, `name`, `placeholder`, `type`,
  - mapping prédéfini par intermédiaire (extensible côté backend `field_mapping_intermediaire` table) — recommandé MVP : 2-3 mappings principaux (BOAD, PNUD, SUNREF Ecobank).
- **FR-005** : Code-couleur (US4) appliqué via overlay CSS (pas de modif intrusive du DOM original).
- **FR-006** : Animation séquentielle via gsap (déjà disponible côté Nuxt — réutiliser le bundle ou re-importer).
- **FR-007** : Bouton "Suggérer" sur champ : appelle `POST /extension/suggest-field`, insère le texte avec animation.
- **FR-008** : SPA observation : `MutationObserver` + hooks `pushState` + listener `popstate`. Re-évaluation à chaque changement de route.
- **FR-009** : Stockage local (`chrome.storage.local`) : JWT, dernière Offre détectée, préférences i18n.
- **FR-010** : Sécurité : pas d'injection de script tiers, CSP strict, JWT envoyé via Bearer header sur les endpoints extension.

## Exigences non-fonctionnelles

- **NFR-001** : L'extension n'ajoute pas plus de 50ms à la navigation utilisateur.
- **NFR-002** : Aucune fuite de données : tout passe par les endpoints `/extension/*` authentifiés.
- **NFR-003** : Compatible Chrome, Edge, Brave (Chromium-based). Firefox post-MVP (manifest V2).
- **NFR-004** : Suggestions IA en < 3s.

## Entités clés

- Pas de nouvelles tables côté backend principal.
- Possible table `field_mapping_intermediaire` (`id, intermediaire_id, mapping_json`) — admin maintenance.

## Success Criteria

- **SC-001** : Extension installée + login → JWT stocké, popup affiche identité PME.
- **SC-002** : Naviguer sur boad.org → bandeau "Offre détectée".
- **SC-003** : Sur formulaire SUNREF Ecobank → "Tout remplir" remplit 70%+ des champs avec code-couleur correct.
- **SC-004** : Bouton "Suggérer" génère un texte adapté.
- **SC-005** : i18n FR/EN switchable.

## Hors-scope MVP (livré en F34)

- Panneau latéral de guidage,
- Suivi candidatures,
- Notifications et rappels,
- Recommandations d'Offres.

## Risques et points de vigilance

- **Patterns d'URL fragiles** : un site refait son design → patterns cassent. Mitigation : maintenir patterns côté backend (admin) + monitoring des erreurs détection.
- **Field mapping difficile** : les portails ont des champs très divers. MVP : couvrir 2-3 portails à 90%, le reste à 50%. Documenter pour user.
- **CORS** : les endpoints `/extension/*` doivent autoriser l'origine extension (`chrome-extension://...`).
- **CSP des sites tiers** : certains bloquent l'injection de scripts. Tester sur les portails réels.
- **JWT expiré** : flow refresh dans l'extension (cohérent F02).
- **Approval Web Store** : Chrome Web Store impose review. MVP : distribuer en mode dev (`.crx` ou unpacked).
