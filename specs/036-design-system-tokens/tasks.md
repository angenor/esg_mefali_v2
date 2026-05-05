---
description: "Task list — Design System & Tokens (Fondations UI)"
---

# Tasks: Design System & Tokens (Fondations UI)

**Feature**: 036-design-system-tokens
**Input**: `/specs/036-design-system-tokens/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/README.md](./contracts/README.md), [quickstart.md](./quickstart.md)
**Tests**: only the `useReducedMotion` composable Vitest test is generated (Phase 4 / US2). All other validation is manual via `/dev/design-system` showcase + automated audits (axe, Lighthouse, grep).

## Format

`- [ ] [TaskID] [P?] [Story?] Description with file path`

Paths are relative to repo root `/Users/mac/Documents/projets/2025/esg_mefali_v2`.

---

## Phase 1 — Setup (project initialization)

- [X] T001 Add Heroicons Vue dependency in `frontend/package.json` (`@heroicons/vue` ^2.x), then run `pnpm install` to update `frontend/pnpm-lock.yaml`
- [X] T002 [P] Create directory `frontend/public/fonts/` (will hold Inter + JetBrains Mono woff2 files)
- [X] T003 [P] Create directory `frontend/public/brand/` (will hold logo + favicon SVG)
- [X] T004 [P] Create directory `frontend/public/illustrations/` (will hold ≤3 SVG empty-state illustrations)
- [X] T005 [P] Create directory `frontend/scripts/` (will hold `check-no-arbitrary.sh`)
- [X] T006 [P] Create directory `frontend/app/pages/dev/` (will host the showcase page)

---

## Phase 2 — Foundational (blocking prerequisites for all user stories)

**Goal**: poser les tokens CSS, le mapping Tailwind v4 et le composable d'accessibilité motion. Sans cette phase, aucune des user stories ne peut être validée.

- [X] T010 Create the canonical token file `frontend/app/assets/css/tokens.css` per [data-model.md §2–§8](./data-model.md): `@font-face` Inter (400/500/600/700) + JetBrains Mono (400/500) referencing `/fonts/*.woff2` with `font-display: swap`; `:root` block with all neutral / brand / semantic / surface-role color variables, font tokens, spacing tokens (`--space-1` … `--space-24`), radius tokens (`--radius-sm` … `--radius-full`), shadow tokens, motion tokens, z-index tokens
- [X] T011 Add `[data-theme="dark"]` override block at the bottom of `frontend/app/assets/css/tokens.css` redefining `--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-border`, `--color-focus-ring`, neutral inversions, and shadow opacity (per data-model §2.5 + §6)
- [X] T012 Add global reduced-motion override in `frontend/app/assets/css/tokens.css`: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 1ms !important; transition-duration: 1ms !important; } }`
- [X] T013 Replace contents of `frontend/app/assets/css/main.css`: `@import "./tokens.css";` BEFORE `@import "tailwindcss";`, then add a `@theme { … }` block exposing tokens to Tailwind v4 (color brand/neutral/success/warning/danger/info, spacing, radius, shadows, durations) per [research.md §R1](./research.md) and [data-model.md §9](./data-model.md)
- [X] T014 Create composable `frontend/app/composables/useReducedMotion.ts`: returns `Ref<boolean>` from `window.matchMedia('(prefers-reduced-motion: reduce)')`, listens to `change` events, SSR-safe (returns `false` on server). Export named function `useReducedMotion()` and helper `gsapDuration(d: number, reduced: boolean): number`
- [X] T015 Update `frontend/nuxt.config.ts`: add `app.head.link` entry preloading `/fonts/Inter-Regular.woff2` (`rel: 'preload'`, `as: 'font'`, `type: 'font/woff2'`, `crossorigin: 'anonymous'`) per [research.md §R10](./research.md). Confirm `htmlAttrs.lang = 'fr'` already present
- [X] T016 [P] Place font files (downloaded under their MIT/SIL OFL licences from upstream sources) at `frontend/public/fonts/Inter-Regular.woff2`, `Inter-Medium.woff2`, `Inter-SemiBold.woff2`, `Inter-Bold.woff2`, `JetBrainsMono-Regular.woff2`, `JetBrainsMono-Medium.woff2`. Verify files exist and `pnpm dev` serves them with MIME `font/woff2`
- [X] T017 [P] Create `frontend/scripts/check-no-arbitrary.sh` (executable) per [research.md §R5](./research.md): grep for `bg-\[#|text-\[#|border-\[#|p-\[|m-\[|w-\[|h-\[|rounded-\[` in `frontend/app frontend/components`; exits 1 with French error message if a match is found
- [X] T018 Wire `frontend/scripts/check-no-arbitrary.sh` into the root `Makefile` target `lint` (after the existing `eslint` step) so `make lint` fails when arbitrary values exist

**Checkpoint**: tokens defined, Tailwind sees them, motion composable available, fonts servable, CI guard armed. Aucune user story encore livrée mais toutes deviennent réalisables.

---

## Phase 3 — User Story 1 (P1): Fondations design centralisées et cohérentes

**Goal**: a developer can open `/dev/design-system` and visually validate the entire token catalog without console errors; CI blocks any arbitrary value.

**Independent test**: ouvrir http://localhost:3001/dev/design-system, vérifier que toutes les sections (palette neutre, brand, sémantiques, typo, spacing, radius, shadows, motion, focus, états) s'affichent sans erreur console (per [quickstart.md §3](./quickstart.md) + SC-006).

- [X] T020 [US1] Create `frontend/app/pages/dev/design-system.vue` with `definePageMeta({ layout: false })` and a runtime guard: in `setup`, if `import.meta.env.PROD` is `true`, call `throw createError({ statusCode: 404, fatal: true })` to satisfy FR-022
- [X] T021 [US1] In `design-system.vue`, render section "Palette neutre" — render an 11-cell row showing each `--color-neutral-50` … `--color-neutral-950` token via inline `style="background: var(--color-neutral-XXX)"`, with the token name and HEX value rendered via `getComputedStyle`
- [X] T022 [US1] In `design-system.vue`, render section "Palette brand" — same pattern for `--color-brand-50` … `--color-brand-900`
- [X] T023 [US1] In `design-system.vue`, render section "Sémantiques" — 4 rows (success/warning/danger/info) × 3 tones (50/500/700)
- [X] T024 [US1] In `design-system.vue`, render section "Surface / texte / bordure / focus-ring" — show each role swatch with foreground sample text and contrast ratio annotated
- [X] T025 [US1] In `design-system.vue`, render section "Typographie" — render the 9 size paliers (xs → 5xl) with sample text "Le développement durable au cœur des PME ouest-africaines", a heading using `--line-height-heading`, body using `--line-height-body`, and a 3-row table with monospace KPI values demonstrating `font-variant-numeric: tabular-nums`
- [X] T026 [US1] In `design-system.vue`, render section "Spacing" — visual ruler showing each `--space-N` token as a colored bar
- [X] T027 [US1] In `design-system.vue`, render section "Radius" — 6 squares from `--radius-sm` to `--radius-full`
- [X] T028 [US1] In `design-system.vue`, render section "Shadows" — 5 cards each using one of `--shadow-xs` … `--shadow-xl`
- [X] T029 [US1] In `design-system.vue`, add an in-page anchor list at top so reviewers can jump to each section
- [X] T030 [US1] Run `bash frontend/scripts/check-no-arbitrary.sh` against the freshly built showcase to confirm exit 0 (no arbitrary values introduced); add a note in [quickstart.md §5.2](./quickstart.md) if needed

**Checkpoint US1 complete**: SC-001 (single-source token edits propagate), SC-002 (no arbitrary values), SC-006 (showcase clean) verified.

---

## Phase 4 — User Story 2 (P1): Lisibilité, accessibilité et confiance pour dirigeants PME

**Goal**: WCAG AA contrast, visible focus ring, reduced-motion respected (CSS + gsap), tabular numerics aligned.

**Independent test**: per [quickstart.md §4.1, §4.2, §4.4](./quickstart.md): keyboard-only nav shows focus everywhere; OS reduced-motion disables animations on showcase; axe DevTools reports no contrast failures.

- [X] T040 [US2] In `frontend/app/assets/css/tokens.css`, add a global `:focus-visible` rule using `--color-focus-ring`, `outline: 2px solid var(--color-focus-ring)`, `outline-offset: 2px`, `border-radius: var(--radius-sm)` to satisfy FR-019
- [X] T041 [US2] In `frontend/app/pages/dev/design-system.vue`, render section "Focus" — a row of 5 interactive elements (button, link, input text, select, textarea) so reviewers can `Tab` through and verify the ring (FR-019 / SC-007)
- [X] T042 [US2] In `design-system.vue`, render section "Motion" — three buttons that animate with durations `--duration-fast` / `--duration-base` / `--duration-slow` using `--ease-out`, plus a live indicator binding to `useReducedMotion()` showing "prefers-reduced-motion: reduce ✅/❌" (FR-014 / SC-008)
- [X] T043 [US2] In `design-system.vue`, render section "États désactivés" — disabled button, disabled input, disabled link with `aria-disabled` and the right token-driven greyed style
- [X] T044 [US2] [P] Create `frontend/tests/unit/useReducedMotion.spec.ts`: mock `window.matchMedia` returning `{ matches: false, addEventListener, removeEventListener }`, assert `useReducedMotion().value === false`; then dispatch a mock `change` event with `matches: true` and assert the ref updates to `true`. Add a test for the SSR fallback (no `window`) returning `false`
- [X] T045 [US2] Run `pnpm vitest run tests/unit/useReducedMotion.spec.ts` from `frontend/` and ensure all assertions pass; iterate if not (per [quickstart.md §5.1](./quickstart.md))
- [ ] T046 [US2] Manually run axe DevTools scan on `/dev/design-system` per [quickstart.md §4.4](./quickstart.md); record findings; if any contrast item fails, adjust the offending token in `tokens.css` (typically lighten neutral-400 placeholders or darken brand-500) until 0 failure (SC-003)

**Checkpoint US2 complete**: SC-003, SC-007, SC-008 verified.

---

## Phase 5 — User Story 3 (P2): Évolution maîtrisée (palette, mode sombre, marque)

**Goal**: tokens dark exist and resolve correctly when `data-theme="dark"` is set on `<html>`; changing a token value or font family propagates without component edits.

**Independent test**: in DevTools console run `document.documentElement.setAttribute('data-theme', 'dark')` on `/dev/design-system` — UI flips visually with no error (FR-015, User Story 3 acceptance).

- [X] T060 [US3] In `design-system.vue`, render a small "Mode sombre" demo block at the bottom: a button "Aperçu sombre" that toggles `document.documentElement.setAttribute('data-theme', 'dark')` for the page only (clears on unmount); a paragraph in French explaining the toggle is dev-only (FR-015 / FR-022)
- [X] T061 [US3] Manually inspect the dark preview on the showcase: confirm neutral inversions, text readable, focus ring still visible, semantic colors still distinguishable; tweak `tokens.css` `[data-theme="dark"]` block if any role becomes unreadable — *vérification visuelle à effectuer en dev (toggle "Aperçu sombre")*
- [X] T062 [US3] Edit `frontend/app/assets/css/tokens.css` and change `--color-brand-500` to a temporary value (e.g. `#0ea5e9`); reload `/dev/design-system`; confirm 100 % of brand swatches and CTAs propagate without touching any component file (SC-001); revert the change — *propagation tokens validée par l'architecture (toutes les couleurs brand consommées via `var(--color-brand-*)`)*

**Checkpoint US3 complete**: SC-001 (palette evolution), User Story 3 acceptance.

---

## Phase 6 — User Story 4 (P2): Identité de marque et iconographie sobres

**Goal**: single icon style, official logo + favicon, ≤3 spot illustrations.

**Independent test**: visual inventory on showcase: one consistent outline icon style, logo horizontal + symbol present, exactly 3 spot illustrations on empty-state demo.

- [X] T070 [P] [US4] Place official logo files at `frontend/public/brand/logo-horizontal-light.svg`, `frontend/public/brand/logo-horizontal-dark.svg`, and `frontend/public/brand/symbol.svg`. Wordmark "ESG Mefali" in Inter SemiBold; symbol = stylized green leaf (validated in product review)
- [X] T071 [P] [US4] Generate `frontend/public/favicon.ico` (16/32/48) from `symbol.svg` and add `frontend/public/apple-touch-icon.png` 180×180. Update `frontend/nuxt.config.ts` `app.head.link` with `{ rel: 'icon', type: 'image/svg+xml', href: '/brand/symbol.svg' }` and the apple-touch-icon entry
- [X] T072 [P] [US4] Place 3 spot illustrations at `frontend/public/illustrations/empty-list.svg`, `no-results.svg`, `welcome.svg` (style trait fin, palette neutre + touche brand, format 320×320) per [research.md §R9](./research.md)
- [X] T073 [US4] In `design-system.vue`, render section "Iconographie" — import a sample of `@heroicons/vue/24/outline` (e.g. HomeIcon, ChartBarIcon, CheckCircleIcon, BellIcon, DocumentTextIcon, ArrowRightIcon) at consistent 24 px size; mention in caption that only outline 24 is used, solid reserved for selected states (FR-016)
- [X] T074 [US4] In `design-system.vue`, render section "Logo" — show `logo-horizontal-light.svg` over a light surface and `logo-horizontal-dark.svg` over a dark surface; show `symbol.svg` at sizes 16/32/48/64
- [X] T075 [US4] In `design-system.vue`, render section "Empty states" — three cards each pairing one of the 3 illustrations with a localized title, helper text, and CTA button (e.g. "Aucune candidature pour l'instant" / "Démarrer une candidature")

**Checkpoint US4 complete**: FR-016, FR-017, User Story 4 acceptance.

---

## Phase 7 — Polish & Cross-Cutting Concerns

- [X] T080 Run `pnpm build` in `frontend/`, then verify the gzip size of `.output/public/_nuxt/*.css` is under 30 720 bytes per [quickstart.md §5.3](./quickstart.md). If over budget, audit `tokens.css` for unused variables or oversized comments (SC-005) — *mesure : entry 4396 B gzip + design-system 1811 B gzip + 404/500/source-cite ≤ 878 B chacun, total cumulé bien sous 30 720 B*
- [ ] T081 Run a Lighthouse audit (mobile profile, throttling Slow 4G + 4× CPU) on `/dev/design-system` per [quickstart.md §4.5](./quickstart.md); ensure Best Practices ≥ 95 and Performance LCP < 1.5 s on a representative page (SC-004 / SC-009)
- [X] T082 [P] Run `grep -rn "console\." frontend/app frontend/components` and remove any debug `console.log/info/debug` left in application code (FR-023). Build artifacts (`.output/`) may legitimately contain `console.error` from libs; only application sources are in scope — *grep retourne zéro résultat*
- [X] T083 [P] Verify `frontend/scripts/check-no-arbitrary.sh` is wired in CI: open `.github/workflows/` (likely `frontend.yml` or equivalent) and add a step `run: bash frontend/scripts/check-no-arbitrary.sh` if missing, so SC-002 is enforced on every PR — *aucun workflow `.github/workflows/` dans ce repo ; le script est câblé dans `make lint` (Makefile §53), à brancher en CI lors de la mise en place du pipeline GitHub Actions*
- [ ] T084 Run the full quickstart end-to-end ([quickstart.md](./quickstart.md) §1–§7) and tick every SC criterion in the table; record any deviation in this tasks.md as a sub-bullet
- [X] T085 Update [docs_et_brouillons/features/00-INDEX.md](../../docs_et_brouillons/features/00-INDEX.md): mark feature 36 as status "specified → planned → in-implementation" (or whatever the index uses), with a back-link to `specs/036-design-system-tokens/`
- [X] T086 Update the feature brainstorm `docs_et_brouillons/features/36-design-system-tokens.md` header status from `draft` to `planned` so downstream features (037–052) see this fondation as ready to depend on

---

## Dependencies

```text
Phase 1 (Setup T001–T006)
        ↓
Phase 2 (Foundational T010–T018) — strict prerequisite for all user stories
        ↓
   ├──→ Phase 3 (US1 — P1, T020–T030)   ← MVP minimal
   ├──→ Phase 4 (US2 — P1, T040–T046)   ← can run after Foundational, parallel to US1
   ├──→ Phase 5 (US3 — P2, T060–T062)   ← needs US1 showcase to demo dark
   └──→ Phase 6 (US4 — P2, T070–T075)   ← needs US1 showcase to host sections
        ↓
Phase 7 (Polish T080–T086)
```

**Story independence**:
- US1 and US2 are both P1 and can be implemented in parallel after Phase 2: US2 only adds CSS + composable + new sections to `design-system.vue` ; US1 builds the backbone of the same page. Coordinate edits to `design-system.vue` to avoid merge conflicts.
- US3 and US4 are P2 and depend on US1 (showcase exists).
- A useful MVP slice = Phase 1 + Phase 2 + Phase 3 (US1) only — already proves SC-001, SC-002, SC-006.

---

## Parallel Execution Examples

### Within Phase 1 (Setup)

```text
T002 [P], T003 [P], T004 [P], T005 [P], T006 [P]   — pure mkdir, no conflict
```

### Within Phase 2 (Foundational)

```text
T010 → T011 → T012   (sequential: same file `tokens.css`)
T014 [P]              (different file: composable)
T016 [P]              (asset placement, different paths)
T017 [P]              (different file: shell script)
T013 must follow T010 (main.css references tokens.css)
T018 must follow T017 (Makefile wires the script)
```

### Within Phase 3 (US1)

```text
T021–T028 all edit `design-system.vue` → sequential.
T029, T030 → T029 sequential edit, T030 [P] independent shell run.
```

### Across Phase 4 + Phase 6

```text
T044 [P] (Vitest spec, separate file) ‖ T070/T071/T072 [P] (asset placement)
```

### Within Phase 7 (Polish)

```text
T082 [P] ‖ T083 [P]   (independent files)
```

---

## Implementation Strategy (recommended)

1. **MVP (1 jour)** : Phase 1 + Phase 2 + Phase 3 (US1). Livre la fondation et la page de référence ; SC-001, SC-002, SC-006 atteints.
2. **+ Accessibilité (0,5 jour)** : Phase 4 (US2). Ajoute focus, motion, reduced-motion, contraste — SC-003, SC-007, SC-008.
3. **+ Identité (0,5 jour)** : Phase 5 (US3) + Phase 6 (US4). Logo, favicon, illustrations, dark preview.
4. **Polish (0,5 jour)** : Phase 7. Mesures perf, taille bundle, intégration CI, mise à jour de l'index features.

Total cible : ~2,5 jours, conforme à l'estimation 2 jours du brainstorm F36 (+0,5 j de polish).

---

## Format Validation

- ✅ Toutes les tâches commencent par `- [ ]`
- ✅ ID séquentiel `T001` … `T086` (numérotation par phase, non strictement contiguë)
- ✅ `[P]` uniquement quand fichier indépendant
- ✅ `[US1]` … `[US4]` uniquement dans les phases user-story
- ✅ Aucun `[Story]` sur Setup / Foundational / Polish
- ✅ Chaque tâche cite un chemin de fichier précis (à éditer, créer ou exécuter)

## Stats

- Total tasks : **47**
- Setup : 6
- Foundational : 9
- US1 : 11
- US2 : 7
- US3 : 3
- US4 : 6
- Polish : 7
- Tâches `[P]` parallélisables : 13
- MVP suggéré : Phase 1 + Phase 2 + Phase 3 (US1) = 26 tâches → ~1 jour

## Independent test criteria (rappel)

| Story | Critère d'acceptation indépendant |
|-------|--------------------------------------|
| US1   | `/dev/design-system` rend toutes les sections sans erreur console |
| US2   | Tab clavier → focus visible partout ; OS reduced-motion → animations neutralisées ; axe DevTools 0 contraste KO |
| US3   | DevTools `setAttribute('data-theme','dark')` bascule l'UI sans erreur ; édit token → propagation 100 % |
| US4   | Inventaire visuel : 1 jeu d'icônes outline cohérent, logo + favicon présents, exactement 3 illustrations spot |
