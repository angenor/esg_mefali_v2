# Phase 0 — Research: F51

**Branch**: `051-matching-candidatures-simulateur-ui` | **Date**: 2026-05-05

Toutes les `NEEDS CLARIFICATION` identifiées en planification ont été résolues ci-dessous. Ce document liste les **décisions techniques**, leur **rationnel**, et les **alternatives écartées**.

---

## 1. Sélecteur projet pour `/matching`

**Decision** : `/matching` consomme le projet « actif » de `useUserStore` (déjà disponible via F43). Si aucun projet n'est défini, la page affiche un empty state pédagogique (illustration + CTA « Créer un projet » → `/profil/projets/nouveau`). Un bouton secondaire « Voir toutes les offres » bascule en mode catalogue (non scoré) consommant `GET /me/offres`.

**Rationale** : Le backend F25 (`GET /me/projets/{projet_id}/matching`) exige un `projet_id`. Imposer une sélection projet aligne UX et API, évite un endpoint global supplémentaire pour le scoring (coûteux : matrice projet × offres pour tous les projets de la PME). L'endpoint `/me/offres` non scoré couvre la découverte hors projet.

**Alternatives considered** :

- *Liste globale agrégée scorée tous projets* — coût computationnel non justifié pour un MVP, ambigu UX (quelle offre va à quel projet ?).
- *Forcer le user à choisir un projet via modale* — friction inutile si un seul projet existe.

---

## 2. Audit log autosave

**Decision** : L'autosave d'un brouillon (PATCH `/me/candidatures/{id}/draft`) **ne génère pas** un audit par mutation. Seule la transition d'étape (`step_courant` change) ou la soumission émet un audit `record_audit(source_of_change='manual', entity='candidature', field='step_courant'|'submitted_at')`. Les frappes intermédiaires sont consolidées dans la colonne `draft_snapshot_json` mais n'apparaissent pas dans l'audit append-only.

**Rationale** : P3 exige journalisation des **mutations métier**, pas du buffer applicatif. Auditer chaque keystroke saturerait `audit_event` (10k+ lignes par wizard). Le passage d'étape est l'événement métier ; la soumission est l'événement juridique (P4).

**Alternatives considered** :

- *Audit par PATCH* — saturation de la table audit, perte de signal métier.
- *Pas d'audit du tout sur les drafts* — viole P3 (besoin de tracer qui a changé d'étape).

---

## 3. Filtres URL-persisted

**Decision** : `useMatchingFilters` synchronise bidirectionnellement le store Pinia avec `useRoute().query` via un `watch` profond + `navigateTo({ query, replace: true })`. Au mount, le store hydrate depuis l'URL ; à chaque changement de filtre, l'URL est mise à jour (replace, pas push, pour ne pas polluer l'historique).

**Rationale** : Permet le partage d'URL et la restauration au reload, alignement avec FR-002 spec. `replace: true` évite que chaque toggle filtre ne crée une entrée dans `history`.

**Alternatives considered** :

- *Query params manuels* — boilerplate dans chaque composant.
- *Hash fragment (`#filter=...`)* — pas indexable et casse les `nuxt-link`.

---

## 4. Comparateur localStorage

**Decision** : Clé `mefali:matching:comparator:v1` ; valeur = tableau d'objets `{offre_id, snapshot_label, snapshot_montant, snapshot_devise, snapshot_intermediaire, added_at, projet_id}`. Cap **3 strict** (4ème offre → toast « Maximum 3 offres comparables »). Le store écoute `storage` events pour synchro multi-onglets. Changement de projet actif = vidage.

**Rationale** : Hors-scope MVP : multi-device. localStorage couvre le besoin (Assumptions spec). Le snapshot d'attributs au moment de l'ajout évite un appel API au render de `/matching/compare`. Vidage cross-projet évite la confusion (offres de projets différents non comparables).

**Alternatives considered** :

- *Backend `comparator` table* — surdimensionné pour MVP, hors-scope assumptions.
- *URL state* — limite de longueur URL, fragile.

---

## 5. Carte Leaflet (chunk async)

**Decision** : Import dynamique `const L = (await import('leaflet')).default` à l'ouverture de l'onglet « Carte » sur `/matching`. Tile OpenStreetMap public (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`). Clustering via `leaflet.markercluster` (chunk additionnel, lazy). Empty state si aucune offre n'a de `geolocation` côté intermédiaire (`{lat, lng}` NULL).

**Rationale** : Pas d'abonnement payant nécessaire au MVP (Assumptions). Le chunk async évite d'inclure ~150 ko de Leaflet sur le LCP de `/matching`. SC-001 LCP < 2 s respectée.

**Alternatives considered** :

- *Mapbox/Google Maps* — dépendance externe payante hors-scope.
- *Inclusion synchrone Leaflet* — pénalise le LCP de la liste cards.

---

## 6. Wizard transitions gsap

**Decision** : `gsap.timeline()` 200 ms ease `power2.out` pour les transitions entre étapes (slide-in horizontal). Respect `prefers-reduced-motion: reduce` → transitions instantanées (`gsap.set` au lieu de `gsap.from`).

**Rationale** : FR-004 spec demande 200 ms gsap. WCAG 2.1 AA exige le respect de `prefers-reduced-motion` (cohérent avec F50 SC-009).

**Alternatives considered** :

- *Vue `<Transition>` natif* — moins fluide pour transitions complexes (sortie + entrée + slide).
- *Pas de transition* — UX dégradée vs. attentes spec.

---

## 7. Autosave robuste hors-ligne

**Decision** : `useWizardAutosave` :

1. Debounce 800 ms sur tout `change` du draft.
2. PATCH `/me/candidatures/{id}/draft` ; en cas d'échec (timeout, 5xx, offline détecté via `navigator.onLine`), on bufferise dans `localStorage` (clé `mefali:wizard:draft:{candidature_id}`).
3. Indicateur UI : « ✓ enregistré il y a Ns », « ⏳ sauvegarde… », « ⚠ hors-ligne — sauvegarde en attente ».
4. Au retour `online` (event listener), flush du buffer et synchro.

**Rationale** : SC-007 (reprise brouillon 100 % des cas) exige une robustesse face aux coupures réseau, courantes en Afrique de l'Ouest.

**Alternatives considered** :

- *Service worker IndexedDB* — overkill MVP, hors-scope PWA (Assumptions).
- *Pas de buffer* — perte garantie en cas de coupure 4G temporaire.

---

## 8. Snapshot intangible (soumission)

**Decision** : Service `candidatures.service.submit_with_snapshot(candidature_id, account_id, user_id, confirmed: bool)` :

1. Vérifie `confirmed === True` (double-confirm côté serveur).
2. Vérifie `submitted_at IS NULL` (idempotence).
3. Construit `submitted_snapshot_json` en lisant l'**état figé** des entités liées : `entreprise`, `projet`, `offre`, `skills` (avec `version + valid_from + valid_to`), `indicateurs` (idem), `draft_snapshot_json` final, et liste des `document_link_projet` joints.
4. UPDATE atomique : `submitted_at=now(), submitted_snapshot_json=:snap, statut='soumise', step_courant=5, progression_pct=100` `WHERE id=:id AND submitted_at IS NULL`.
5. Audit `record_audit(field='submitted_at', old=NULL, new=ts, source_of_change='manual')`.
6. Trigger DB `candidature_no_mutation_after_submit` interdit toute UPDATE de `submitted_snapshot_json` ou `draft_snapshot_json` quand `submitted_at IS NOT NULL` (sauf colonnes statut/version qui restent mutables par admin via F34).

**Rationale** : P4 — reproductibilité 5 ans. La double colonne `draft_snapshot_json` / `submitted_snapshot_json` simplifie la contrainte (vs. flag applicatif). Le trigger DB élimine le risque applicatif.

**Alternatives considered** :

- *Une seule colonne `snapshot_json` + flag `is_submitted`* — viole P4 (mutabilité applicative possible).
- *Table séparée `candidature_snapshot`* — surdimensionné, ajoute une jointure pour chaque détail.

---

## 9. Debounce simulateur (300 ms + AbortController)

**Decision** : Composable `useSimulateurDebounce(300)` :

- Tout changement de slider déclenche un timer 300 ms.
- Lors d'un nouveau changement avant expiration, le timer est reset et la requête en vol annulée via `AbortController`.
- Pendant le calcul, les charts conservent les dernières données valides (pas de flash blanc), avec un indicateur discret (skeleton sur la zone résultat ou opacity 70 %).

**Rationale** : SC-003 perception < 200 ms. La debounce 300 ms côté input + AbortController évite une accumulation de requêtes ; le maintien des données précédentes évite le flicker.

**Alternatives considered** :

- *Calcul client local* — duplique la logique métier (formules ESG/financières) déjà côté backend, viole single-source-of-truth.
- *Debounce > 500 ms* — perception laggy.

---

## 10. Charts F40 (chart.js)

**Decision** : Réutilisation de `<VizBarChart>` (mensualités), `<VizLineChart>` (cumul intérêts), `<VizPieChart>` (décomposition coûts) déjà fournis par F40. Les composants prennent un prop `data` reactive ; chart.js gère ses propres transitions (option `animation.duration: 200` alignée).

**Rationale** : F40 est dépendance directe ; pas de réinvention. Les transitions chart.js sont fluides, pas besoin de gsap pour les charts.

**Alternatives considered** :

- *D3.js* — surdimensionné pour 3 charts standards.
- *Static SVG* — pas d'animation à l'update.

---

## 11. Comparateur 3 offres en table side-by-side

**Decision** : Composant `<CompareTable>` Tailwind v4 :

- Desktop : grille `grid-cols-[12rem_repeat(3,_1fr)]`, première colonne sticky avec les labels (Type, Montant, Durée, Intermédiaire, Conditions, Documents requis, Lien externe), 3 colonnes data.
- Mobile : layout en cartes empilées avec scroll horizontal sur la zone data (la première colonne reste fixe). Bouton « Retirer du comparateur » sur chaque colonne.

**Rationale** : SC-005 — 100 % des participants identifient les différences sans aide. La grille tabulaire est le format le plus lisible. Le layout mobile (sticky col label + scroll horizontal data) reste lisible sur écran ≥ 360 px.

**Alternatives considered** :

- *Cards juxtaposées sans grille* — différences moins évidentes.
- *Tableau HTML pur* — moins flexible Tailwind v4 et sticky col plus fragile.

---

## 12. Formatage Money

**Decision** : Util frontend `formatMoney({amount, currency}, locale='fr-FR')` :

- `currency='XOF'` : `Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', maximumFractionDigits: 0 })` (FCFA n'a pas de centimes).
- `currency='EUR'` : `Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 })`.
- Conversion XOF↔EUR via parité figée `655.957` (P5 sourcée) — fonction utilitaire `convertMoney(money, target_currency)`.
- `amount` toujours reçu et émis en `string` (Decimal.toString) pour éviter `Number` (P5).

**Rationale** : P5 strict — pas de `float`. `Intl.NumberFormat` gère les locales et formats devise. La parité 655.957 est figée par traité UEMOA, sourcée dans le système.

**Alternatives considered** :

- *`amount: number`* — viole P5.
- *Bibliothèque `dinero.js`* — ajout dépendance non justifié pour 2 devises.

---

## Synthèse

Toutes les décisions sont compatibles avec la constitution v1.0.0. La feature ajoute :

- 5 colonnes sur `candidature`, 1 trigger DB, 1 nouvelle table `simulation_savee` (1 migration `0051`).
- 4 endpoints HTTP nouveaux (1 matching, 3 candidatures, 3 simulation, 1 listing offres = 8 au total). Aucun endpoint existant cassé.
- 3 domaines de pages frontend (matching, candidatures, simulateur) + ~25 composants + 5 composables + 3 stores.
- Tests : 80 %+ coverage backend (pytest), unit Vitest + E2E Playwright frontend.

Aucun nouveau tool LLM, aucun nouveau référentiel, aucun nouveau rôle utilisateur.
