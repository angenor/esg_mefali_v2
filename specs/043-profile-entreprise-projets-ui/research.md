# Phase 0 — Research (F43)

Décisions techniques résolvant les inconnues identifiées dans le plan, **avant** la Phase 1 design. Chaque entrée suit le format `Decision / Rationale / Alternatives considered`.

## R1 — Bibliothèque Decimal côté frontend

**Decision**: utiliser **`decimal.js`** (npm `decimal.js@^10`), déjà éprouvé, sans alternative type `bigdecimal-js` ni recours au natif `BigInt`.

**Rationale**:
- P5 interdit `Number` pour toute valeur monétaire ; `Number.toFixed` perd de la précision sur `0.1 + 0.2`.
- Le backend retourne et accepte `amount` en chaîne (Pydantic `Decimal` sérialisé en JSON string). Le front doit consommer la chaîne sans la passer par `parseFloat`.
- `decimal.js` est < 35 KB minified, supporte les arrondis bancaires, l'API est stable et documentée.
- Aucune autre lib (`bignumber.js`, `big.js`) n'apporte d'avantage notable ; rester sur l'écosystème existant.

**Alternatives considered**:
- `BigInt` natif : impose de fixer le nombre de décimales à la main (ex. centièmes de FCFA) ; plus risqué pour USD avec décimales et conversions.
- `bignumber.js` : équivalent fonctionnel, pas d'avantage net, switch coûteux.
- Conversion serveur seulement : impossible pour la conversion d'affichage live XOF↔EUR (NFR-001 exige < 1 s avec données affichées).

## R2 — Cohérence des statuts projet (clarification spec ↔ backend déployé)

**Decision**: la **source de vérité reste le backend** (5 statuts canoniques `brouillon`, `en_recherche_financement`, `finance`, `en_execution`, `cloture`). L'UI affiche des libellés FR clairs via `useT()` mais n'invente pas de nouveaux statuts. Les mots-clés introduits dans la clarification (`actif`, `en_candidature`, `abandonne`) sont retraités comme suit :
- `actif` → libellé interface affiché lorsque le statut canonique est **non terminal** (donc `en_recherche_financement` ou `en_execution`) selon le contexte. Décision finale : ne pas surcharger ; afficher directement le libellé canonique mais avec wording adouci :
  - `brouillon` → « Brouillon »
  - `en_recherche_financement` → « En recherche de financement »
  - `finance` → « Financé »
  - `en_execution` → « En exécution »
  - `cloture` → « Clôturé »
- `en_candidature` est une **vue dérivée** des candidatures (F26) — quand au moins une candidature `submitted` existe, la carte projet affiche un sous-badge « Candidature en cours » ; ce sous-badge n'est PAS un statut persisté.
- `abandonne` est exprimé via la **soft delete** existante (`deleted_at` non null + restauration possible 30 j, géré par F12-profile). Pas de nouveau statut à créer.

**Rationale**:
- Le backend F12-profile est déjà en production de spec (migrations 0001 + check constraints) ; toute extension d'enum implique : migration alembic + amendement F12 + re-eval F25 matching + re-eval F26 dossiers. Hors scope F43 « UI uniquement ».
- L'UX décrite (statut dans la carte) reste atteignable sans nouveaux statuts : le label « Candidature en cours » dérivé répond à la même intention.
- Cohérent avec P4 (versioning, pas d'écrasement) : ne pas étendre l'enum sans cycle de migration propre.

**Alternatives considered**:
- Étendre l'enum côté backend : génère une dette transverse (F25, F26, F12) et viole la promesse F43 « UI only ».
- Maintenir 6 statuts dans le spec et faire un mapping bidirectionnel front ↔ back : duplication d'enum, source de bugs, test combinatoire en plus.

**Action sur le spec.md**: la mise à jour de FR-011 et de Key Entities Projet sera faite en cohérence avec cette décision (post-research) — référence aux statuts canoniques backend, et sous-badge dérivé documenté en commentaire de FR-011.

## R3 — Validation de devises et peg XOF↔EUR

**Decision**: les devises autorisées côté UI sont strictement `XOF`, `EUR`, `USD`. Le peg XOF↔EUR `655.957` est codé comme **constante typée** (`PEG_XOF_EUR: Decimal`) dans `composables/useDecimal.ts`, accompagnée d'un `source_id` documenté pointant vers la `Source verified` BCEAO (référence : seed F03 catalog). USD est converti en lecture seule via la valeur courante exposée par le backend (`/me/fx/usd-xof` ou équivalent — à confirmer en R7) ; **aucune conversion USD locale** n'est calculée en l'absence de taux serveur.

**Rationale**:
- P5 exige la sourcing du peg ; coder en dur sans constante centrale rendrait le code non auditable.
- Le backend `entreprise/schemas.py` déclare déjà `ALLOWED_CURRENCIES` (cf. `MoneyIn._check_currency`) — le front doit refléter exactement la même liste.

**Alternatives considered**:
- Conversion USD locale via lib FX cliente : viole la promesse de sourcing et crée une dérive avec le calcul backend.
- Stocker le peg dans `runtime config` Nuxt : peu protecteur, n'évite pas le risque de divergence avec le backend (où le peg est aussi en constante).

## R7 — Endpoint FX USD côté backend

**Decision**: pour le MVP F43, **ne pas afficher de conversion USD live** si aucun endpoint FX consolidé n'est exposé. Le sélecteur de devise USD reste fonctionnel pour la **saisie** (l'utilisateur peut entrer un montant USD persistable comme `Money{amount, currency='USD'}`), mais l'affichage parallèle XOF/EUR est désactivé et remplacé par la mention « Conversion USD indisponible — saisie acceptée en USD ». Une issue de suivi sera créée pour exposer `/me/fx/usd-xof?date=YYYY-MM-DD` en tirant parti de la table `fx_rate` (cf. constitution P5).

**Rationale**:
- Le backend stocke déjà USD via `fx_rate` (P5) mais aucun endpoint d'API publique n'est référencé dans `app/api/routes/`. Implémenter cet endpoint relèverait d'un changement backend hors scope F43.
- Le besoin utilisateur immédiat est de **saisir** un montant en USD pour les offres internationales — la conversion d'affichage est secondaire.

**Alternatives considered**:
- Hard-coder un taux USD↔XOF : viole P5 (sourcing) et crée une dérive d'une journée à l'autre.
- Bloquer USD : régression vs F11 qui l'autorise déjà.

## R4 — Stratégie autosave & concurrence optimiste

**Decision**: composable `useEntrepriseProfile` (et `useProjet`) avec :
1. `debounce(800ms)` par champ. Toute nouvelle saisie réinitialise le timer.
2. À l'expiration du timer, déclenche `PATCH` avec corps minimal `{ <field>: value, version: <currentVersion> }` et `AbortController` partagé sur la section : si une nouvelle modification arrive AVANT la réponse, la requête en cours est annulée (`abort()`) et un nouveau timer démarre.
3. Réponse 200 → mise à jour locale `version = current_version + 1` + toast « Enregistré ».
4. Réponse 409 → ouverture `ConflictDialog` (US Story 4 / FR-020) avec les valeurs `current` (backend) et `your` (locale).
5. Réponse 5xx ou erreur réseau → bannière persistante « Modifications non sauvegardées » + retry exponentiel (250 ms, 500, 1000, 2000, 4000, abandon ; total ≤ 8 s) ; tant que l'utilisateur reste sur la page, la valeur locale est préservée.

**Rationale**:
- Le backend F11/F12 retourne déjà `409 ConflictOut { code, current_version, your_version }` selon `entreprise/schemas.py` et `projets/schemas.py` — le mécanisme côté front n'a qu'à le consommer.
- L'`AbortController` évite la course « ancienne requête PATCH lente écrase la valeur fraîche » (a happened sur F42 avec `/me/preferences`).
- Le délai 800 ms vient directement de la spec (US 1 acceptance scenario 2).

**Alternatives considered**:
- `PATCH` plein objet : plus simple mais multiplie les conflits faux-positifs sur les sections à plusieurs champs ; rejeté.
- Last-write-wins (sans `version`) : viole P8 (perte silencieuse) ; rejeté.
- Polling périodique côté UI : superflu puisqu'on a déjà l'EventBus chat et que l'utilisateur ne change pas de session entre deux modifications.

## R5 — Wiring sync chat ↔ profil

**Decision**: réutiliser l'`EventBus` front existant (`composables/useChatEventBus.ts`). À la réception d'un évènement `entity_updated` portant un payload `{ entity: 'entreprise' | 'projet', entity_id, fields_changed[] }`, le composable `useEntrepriseProfile` / `useProjet` :
1. Compare `fields_changed` avec les champs actuellement en cours d'édition non sauvegardés.
2. Si aucun chevauchement → re-fetch silencieux + flash « Mis à jour par le chat ».
3. Si chevauchement → ouvrir `ConflictDialog` immédiatement (sans attendre le prochain autosave) avec `your` = valeur locale, `current` = nouvelle valeur backend obtenue par re-fetch ciblé.

**Rationale**:
- Le backend pousse déjà l'évènement via `useChatToolBridge` (F41 chat conversational layer) lors de l'appel d'un tool mutation. Ce signal est synchrone (côté front, à la fin du tool result rendering).
- Les SSE backend (`/me/entreprise/events`, `/me/projets/events`) restent une option **post-MVP** pour synchroniser plusieurs onglets entre eux ; en MVP F43 ils ne sont pas consommés (un onglet, un utilisateur, un chat actif). Réduit la surface de bug.

**Alternatives considered**:
- Consommer SSE directement : surcharge le réseau, complique la gestion offline, et duplique le canal `useChatToolBridge` qui suffit pour le cas chat → profil.
- Polling 5 s : énergivore, latence > 2 s contradictoire avec SC-003.

## R6 — Wizard projet : library vs custom

**Decision**: composant **custom** `ProjetWizard.vue` avec 4 sous-composants `ProjetWizardStep{1..4}.vue`. Transitions `gsap` 200 ms (translateX). Validation par étape via un schéma Zod par step (`zod` est déjà présent en F38). Pas de lib externe type Headless UI Wizard.

**Rationale**:
- Le wizard est simple (4 étapes, état linéaire), aucune branche conditionnelle. Une lib (vue-stepper, etc.) introduit du couplage pour peu de bénéfice.
- Cohérent avec F37 (UI primitives custom) et F39 (bottom sheet engine custom).
- Zod déjà installé pour les autres formulaires (cf. F42 register wizard).

**Alternatives considered**:
- `vue-form-wizard` : abandonné (peu maintenu Vue 3).
- `formkit` : surdimensionné pour un wizard 4 étapes.

## R8 — Localisation projet : précision géographique

**Decision**: aligner la persistance F43 sur les champs déjà offerts par F12-profile :
- `localisation_pays_iso2` (string ISO 3166-1 alpha-2, validé serveur).
- `localisation_region` (string libre, optionnel ; à exposer côté UI comme « Région / Commune »).
- `localisation_lat` / `localisation_lng` (Decimal, optionnels) — si déjà présents au schéma F12. À vérifier en implémentation : si absents, **différer** lat/lng à un correctif backend mineur ou les omettre du wizard MVP. Décision MVP : exposer **pays + région libre obligatoires**, **lat/lng optionnels uniquement si le schéma F12 les supporte déjà** ; sinon, masquer ces deux champs au MVP et les rouvrir en post-MVP via un correctif F12.

**Rationale**:
- Le clarif Q5 a retenu Option A (pays + région + lat/lng optionnels). La compatibilité avec F12 doit être vérifiée à l'implémentation pour éviter une migration intempestive.
- Pas de référentiel administratif fermé par pays au MVP (dimension trop coûteuse).

**Alternatives considered**:
- Référentiel administratif fermé (Option C de la clarif) : non viable au MVP, exigerait une table `regions_administratives` multi-pays.
- Pays seul : régression vs UX décrite.

## R9 — Documents projet & entreprise : alignement contrainte UI ↔ backend

**Decision**: la contrainte UI (FR-017 : PDF/JPG/PNG/DOCX/XLSX, 25 Mo) est **strictement un sous-ensemble** de la whitelist déjà appliquée par les validators backend :
- `app/projets/validators.py::ALLOWED_MIME_TYPES` accepte aussi `application/msword`, `application/vnd.ms-excel`, `image/webp` (variantes legacy + WebP). MAX = 25 Mo (`MAX_DOC_SIZE_BYTES`).
- `app/entreprise/documents_validators.py::ALLOWED_MIME_TYPES` accepte en plus `image/heic` (photos iPhone). MAX = 25 Mo (`MAX_FILE_BYTES`).

L'UI applique donc une **validation cliente plus restrictive** alignée sur la spec FR-017 (PDF, JPG, PNG, DOCX, XLSX) sans descendre la limite serveur. Si l'utilisateur dépose un fichier accepté backend mais hors liste UI (par ex. `.doc` legacy), le client refuse explicitement. La taille max est synchronisée via une constante partagée `MAX_UPLOAD_BYTES = 25 * 1024 * 1024` (mirror de la valeur backend).

**Rationale**:
- Cohérent avec la clarification Q3 : 5 formats clés + 25 Mo.
- Pas besoin de modifier le backend pour cette restriction UI.
- Le HEIC entreprise reste accessible via la route `entreprise_documents` mais ne sera pas exposé par cette UI MVP (peut être rouvert post-MVP sans nouveau backend).

**Alternatives considered**:
- Synchroniser parfaitement UI ↔ backend (admettre `.doc`, `.xls`, `.webp`, `.heic`) : élargit la surface de support sans bénéfice utilisateur clair sur cible PME ouest-africaine.

## R10 — Pages legacy `pages/projets/`

**Decision**: déplacer le contenu de `pages/projets/index.vue` (placeholder existant) vers `pages/profil/projets/index.vue` et **supprimer** `pages/projets/`. Une redirection Nuxt (`definePageMeta({ redirect: { to: '/profil/projets' } })`) est inutile si la page legacy est vraiment un placeholder ; un audit rapide en début d'implémentation tranche.

**Rationale**:
- Deux URLs (`/projets` et `/profil/projets`) pour le même contenu fragmente la navigation.
- L'arborescence de la sidebar (F38) pointe déjà vers `/profil/...` selon le brouillon ; à confirmer.

**Alternatives considered**:
- Garder les deux et faire un alias serveur : maintenance.

## R11 — i18n des chaînes

**Decision**: étendre `frontend/app/locales/fr.ts` (déjà créé en F42) avec un namespace `profil.*` et `projets.*`. Aucune lib i18n nouvelle ; on conserve l'approche `useT()` déjà en place. Anglais non couvert pour cette feature (la dirigeante PME utilise le français par défaut, et l'anglais est réservé aux dossiers de candidature — F26).

**Rationale**:
- Cohérence F42 ; aucune dépendance externe ajoutée.
- Constitution exige FR par défaut.

**Alternatives considered**:
- `@nuxtjs/i18n` : introduit un module Nuxt lourd pour un seul namespace ; reporté post-MVP.
