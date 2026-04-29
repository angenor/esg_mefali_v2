# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.
Mark each gate as ✅ pass / ⚠ deferred / ❌ violated. Any ❌ on a NON
NEGOTIABLE principle blocks the plan and requires either redesign or a
constitutional amendment — never a workaround in `Complexity Tracking`.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? Les nouveaux champs catalogue ont-ils `source_id NOT NULL` ? | |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + politique RLS ? Les accès cross-tenant retournent-ils 404 ? | |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée avec `source_of_change` ∈ {manual, llm, import, admin} ? | |
| P4 | Versioning + snapshot candidatures | Les nouveaux référentiels/critères/formules portent-ils `version`, `valid_from`, `valid_to` ? Les candidatures stockent-elles un `snapshot_json` immuable ? | |
| P5 | Money typé | Toute valeur monétaire utilise-t-elle `Money = {amount: Decimal, currency}` ? Le risque de change est-il rendu explicite ? | |
| P6 | Pivot Indicateur unique | Les données ESG sont-elles stockées comme valeurs d'`Indicateur` (pas par axe E/S/G ni dupliquées par référentiel) ? | |
| P7 | Plateforme fermée aux intermédiaires | La feature évite-t-elle tout rôle utilisateur Intermédiaire/Bank/Fund ? Les sorties externes passent-elles par attestation Ed25519 + QR ? | |
| P8 | Édition manuelle + sync LLM | Tout champ alimenté par le LLM est-il modifiable manuellement ? La mutation manuelle invalide-t-elle le contexte LLM en temps réel ? | |
| P9 | Tool-use LLM fiable | Nouveaux tools : nom verbal, "use when / don't use when", schéma Pydantic strict (`extra='forbid'`), ≤ 10 tools concurrents par tour, eval gating planifié ? | |
| P10 | UX bottom sheet | Les composants interactifs vivent-ils dans le bottom sheet (jamais inline dans la bulle LLM) ? Bouton "Répondre librement" présent ? | |

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via
  OpenRouter (interchangeable par env) ; embeddings Voyage `voyage-3.5`
  (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé,
  frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement
  (jamais USA).
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP.
- Langue : français par défaut ; anglais uniquement pour dossiers vers
  offres `accepted_languages = 'en'`.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
