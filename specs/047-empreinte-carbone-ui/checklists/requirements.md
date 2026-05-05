# Specification Quality Checklist: Empreinte carbone UI (F47)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-04
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- Quelques mentions techniques (`tCO2e`, `kWh`, `tabular-nums`, `entity_updated{carbon_footprint}`, `show_form`) sont conservées : ce sont des conventions métier (unités GHG Protocol), des contrats d'évènements ou des composants UX déjà nommés dans la constitution / les features amont (F39, F40, F41). Elles ne sont pas considérées comme des détails d'implémentation au sens de la checklist.
- Mentions de référentiels (ADEME 2024, IPCC AR6) : ce sont des **standards métier** que la PME reconnaît, pas des choix techniques.
