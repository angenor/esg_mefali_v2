# F43 — Profile Entreprise & Projets UI (UI de F11 + F12-profile)

**Phase** : C — Onboarding & profil
**Modules brainstorm** : 0.5 (Profil entreprise) + 0.6 (Projets) — UI frontend
**Dépendances** : F36, F37, F38, F39, F11 backend, F12-profile-projets backend, F22 documents
**Estimation** : 4 jours

## Contexte et objectif

Pages **`/profil/entreprise`** et **`/profil/projets`**. Coexistence stricte avec le chat (P8 sync bidirectionnel) : modifier un champ ici **invalide le contexte LLM** ; mutation LLM via tools `update_entreprise` / `update_projet` pousse via EventBus → la page se rafraîchit.

Style : formulaires sectionnés, autosave silencieux (debounce 800 ms), feedback discret "Enregistré il y a 2 s", mode lecture/édition par section, indicateur de complétion en haut.

## User Stories

- **US1 Profil entreprise vue (P1)** — `/profil/entreprise` lit `GET /me/entreprise`, sections : Identité, Taille (CA, effectifs), Localisation, Gouvernance, Pratiques. Click section → édition.
- **US2 Édition section autosave (P1)** — `<UiFormField>`, debounce 800 ms `PATCH /me/entreprise`, toast "Enregistré".
- **US3 Money typé (P1)** — `<UiNumber>` + selector currency (XOF/EUR/USD), conversion live. Décimal côté client jamais float (P5).
- **US4 Multi-pays opération (P1)** — `<UiMultiSelect>` ISO2, search, cluster Afrique de l'Ouest en haut.
- **US5 Indicateur complétion (P1)** — barre progress en haut, % via `GET /me/entreprise/completion`, tooltip champs manquants.
- **US6 Liste projets (P1)** — `/profil/projets` cards : nom, statut, secteur, dernière maj, score ESG (badge couleur). Bouton "Nouveau projet".
- **US7 Détail projet (P1)** — `/profil/projets/[id]` : Identité, Description, Localisation, Budget (Money), Documents (F50), Score (lien F47).
- **US8 Création projet (P1)** — wizard modal 4 étapes : nom + description, secteur + impact_type (E/S/G), localisation, budget + horizon. Validation zod.
- **US9 Suppression soft (P1)** — bouton "Supprimer" → confirm modal → `DELETE` (soft, `deleted_at`). Réversible 30 j (P2).
- **US10 Documents projet (P1)** — section liste docs (F50), bouton "Téléverser" → `<UiFileUpload>`, preview thumbnails.
- **US11 Sync bidirectionnel chat (P1)** — `useChatEventBus` listen `entity_updated` → reload section + flash "Mis à jour par le chat".
- **US12 Conflit édition (P1)** — modif locale + push backend simultanés → modal "Vos changements ou ceux du chat ?" preview les deux.
- **US13 Audit visibility (P2)** — bouton "Historique" par section ouvre drawer `GET /me/audit-log?entity=...` (F04).
- **US14 Empty state (P1)** — pas de projet → grande illu + "Créez votre premier projet" CTA.

## Exigences fonctionnelles

- **FR-001** : `pages/profil/entreprise.vue, pages/profil/projets/index.vue, pages/profil/projets/[id].vue, components/profil/*`.
- **FR-002** : Pinia stores `useEntrepriseStore, useProjetsStore`, subscribe chat EventBus.
- **FR-003** : Autosave : debounce 800 ms, abort si nouvelle modif (AbortController).
- **FR-004** : Conflict via `version` (optimistic concurrency F04). `version` reçu < courant → modal merge.
- **FR-005** : Wizard projet : transitions 200 ms gsap, validation par étape.
- **FR-006** : `useEntrepriseCompletion()` + `GET /me/entreprise/completion`.
- **FR-007** : Tous champs accessibles clavier (tab order strict).

## Exigences non-fonctionnelles

- **NFR-001** : `/profil/entreprise` affichée < 1 s avec données (SSR + pinia hydrate).
- **NFR-002** : Autosave ne perd jamais de données (test taper rapidement, reload, modifs présentes).
- **NFR-003** : 80 % couverture vitest stores + composants.
- **NFR-004** : Erreurs `aria-describedby`.

## Success Criteria

- **SC-001** : Modifier raison sociale → `PATCH` < 1 s, toast confirmé.
- **SC-002** : LLM mutation via chat → page refresh instantané.
- **SC-003** : Créer projet wizard → projet listé immédiatement.
- **SC-004** : Complétion 30 % → 80 % en 5 champs.

## Hors-scope MVP

- Multi-projets actifs simultanés : MVP 1 projet "principal" ; all-projets P2.
- Comparateur projets → post-MVP.
- Rich-text editor toast-ui → P2.
- Drag-reorder → post-MVP.

## Risques et points de vigilance

- Conflit chat ↔ formulaire : tester scénario réel.
- Autosave + erreurs réseau : banner "Modifs non sauvegardées", retry auto.
- Money decimal precision : `decimal.js`, jamais arithmétique Number.
- Zones d'opération : ISO2 backend, pas noms libres.
