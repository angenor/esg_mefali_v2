# F51 — Matching offres + Wizard candidature + Simulateur (UI de F25/F26/F27)

**Phase** : F — Matching, candidatures, simulateur
**Modules brainstorm** : 5.0 matching + 5.1 dossiers candidature + 5.3 simulateur
**Dépendances** : F36, F37, F38, F39, F40, F25/F26/F27 backend
**Estimation** : 5 jours

## Contexte et objectif

Trois pages métier liées par le parcours "trouver un financement vert" :

1. **`/matching`** — découverte d'offres compatibles. Cards + filtres + comparateur + carte Leaflet.
2. **`/candidatures`** — wizard multi-étapes pour générer un dossier complet, submit, suivi statut.
3. **`/simulateur`** — outil interactif "qu'est-ce que je peux financer ?" sliders + résultats temps réel.

Toutes consomment intensément `<ChatBottomSheet>` F39 et `<Viz*>` F40.

## User Stories

### `/matching`

- **US1 Liste offres recommandées (P1)** — cards triées par compat (F25), nom intermédiaire, montant, type, durée. Click → drawer détail.
- **US2 Filtres (P1)** — type, montant min/max, durée, intermédiaire, secteur. URL persisté.
- **US3 Carte Leaflet (P2)** — `<VizLeafletMap>` F40, pins par intermédiaire, click → cards.
- **US4 Comparateur (P1)** — "Ajouter au comparateur" 2-3 offres → `/matching/compare` table side-by-side.
- **US5 Drawer détail offre (P1)** — conditions, documents requis, lien externe, CTA "Préparer ma candidature" → `/candidatures/new?offre_id=...`.

### `/candidatures`

- **US6 Liste candidatures (P1)** — table : nom offre, statut (5 valeurs), date maj, % complétion. Click → détail.
- **US7 Wizard nouvelle candidature (P1)** — 5 étapes : (1) offre + projet, (2) snapshot data PME read-only + bouton "Modifier dans profil", (3) documents requis (upload F50 + checklist), (4) réponses libres via chat F41 contextuel, (5) récap + soumission.
- **US8 Sauvegarde brouillon (P1)** — autosave entre étapes, "Reprendre plus tard" persisté `candidature.snapshot_json`.
- **US9 Soumission (P1)** — confirm modal "Snapshot intangible (P4) — ne plus modifier après envoi", `POST /me/candidatures/{id}/submit`.
- **US10 Suivi statut (P1)** — timeline transitions, commentaires intermédiaire si reçus.
- **US11 Documents manquants (P1)** — banner si checklist incomplète, lien upload F50.

### `/simulateur`

- **US12 Sliders (P1)** — montant, durée, type d'investissement, part subvention. Output : mensualités, coût total, économie estimée, impact CO2 évité.
- **US13 Charts résultats (P1)** — `<VizBarChart>` mensualités, `<VizLineChart>` cumul intérêts, `<VizPieChart>` décomposition.
- **US14 Sauvegarde simulation (P2)** — "Sauvegarder cette simulation" → `/simulateur/historique`.
- **US15 Lien matching (P1)** — "Trouver des offres compatibles" → `/matching?montant=X&duree=Y`.

## Exigences fonctionnelles

- **FR-001** : Pages `pages/matching/*, /candidatures/*, /simulateur/*`.
- **FR-002** : Composants `components/matching/{OffreCard,FiltresPanel,CompareTable}, candidatures/{Wizard,DocumentsChecklist,SubmissionModal}, simulateur/{SliderPanel,ResultsCharts}`.
- **FR-003** : Pinia `useMatchingStore, useCandidaturesStore, useSimulateurStore`.
- **FR-004** : Wizard transitions 200 ms gsap, validation par étape, autosave 800 ms debounce.
- **FR-005** : Simulateur recalcule via `POST /me/simulateur/calculate` debounced 300 ms.
- **FR-006** : Comparateur max 3 offres, persist localStorage.
- **FR-007** : Soumission candidature : double confirm (modal + checkbox), audit F04.

## Exigences non-fonctionnelles

- **NFR-001** : Wizard complétable < 15 min sur 5 PME testées.
- **NFR-002** : Simulateur recalcul < 200 ms perçu.
- **NFR-003** : Matching liste 50 offres LCP < 2 s.
- **NFR-004** : Mobile-first.

## Success Criteria

- **SC-001** : Filtrer "subvention + < 100k EUR" → 5 cards.
- **SC-002** : Wizard 5 étapes complétées + autosave → soumission OK.
- **SC-003** : Simulateur slider → charts updates fluide.
- **SC-004** : Comparateur 3 offres → table side-by-side claire.
- **SC-005** : Lien "Trouver offres compatibles" depuis simulateur → matching pré-filtré.

## Hors-scope MVP

- Match scoring custom (poids ajustables admin) → P2.
- Notifications push acceptation → P7 interdit (pas d'intermédiaire automatisé), statut maj manuelle PME.
- Multi-currency simulateur → MVP FCFA + EUR.
- Co-signature (CFO + CEO) → post-MVP.

## Risques et points de vigilance

- Wizard long : sauvegarde robuste, ne pas perdre data sur reload.
- Snapshot intangible : warning très clair avant soumission.
- Carte Leaflet sans data : empty state "Aucun intermédiaire dans cette zone".
- Simulateur math : vérifier formules + tests 10 cas avec analyste.
- Comparateur 3 : message clair sinon UX confuse.
