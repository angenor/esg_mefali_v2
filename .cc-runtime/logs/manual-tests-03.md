# F03 — Tests manuels (à exécuter pour validation visuelle / browser / PDF)

Tâches couvertes par tests automatisés (pytest + vitest) — non listées ici.

## US4 — Composant SourceCite (UI)

- [x] T039 — page démo `/demo/source-cite-demo` : ✅ 2026-04-30 agent-browser. Fix appliqué dans `frontend/app/middleware/auth.global.ts` (skip SSR via `if (import.meta.server) return`). 3 instances `<SourceCite>` visibles (verified/pending/outdated) ; clic picto ouvre le bottom sheet "Sources" avec bouton Fermer ; affiche "Failed to fetch" car UUIDs `11111111-...` factices (attendu, conforme commentaire du code).
- [ ] T041 — E2E Playwright `frontend/tests/e2e/source-cite.spec.ts` (post-MVP) : nécessite que des UUIDs réels soient seedés en DB ; à activer une fois F07 (catalog-sources-management) livré
- [ ] T038 — animation gsap slide-up : ouvrir bottom sheet et vérifier visuellement la fluidité (gsap pas encore intégré, fallback CSS pour MVP)

## US5 — Annexe PDF

- [ ] T042 — vérifier visuellement le markdown généré injecté dans un export PDF F24 (helper `to_pdf_section` est passthrough — sera branché quand F24 livrera son moteur WeasyPrint)

## Audits SQL

- [ ] T049 — exécuter `psql ... -f backend/scripts/audit_unsourced_catalog.sql` après seed catalogue (F07/F09) ; doit retourner 0 lignes une fois le backfill effectué
- [ ] T050 — planifier l'exécution hebdomadaire de `backend/scripts/audit_double_validation.sql` (cron) ; doit toujours retourner 0 lignes
