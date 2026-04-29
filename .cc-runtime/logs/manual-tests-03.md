# F03 — Tests manuels (à exécuter pour validation visuelle / browser / PDF)

Tâches couvertes par tests automatisés (pytest + vitest) — non listées ici.

## US4 — Composant SourceCite (UI)

- [ ] T039 — page démo `/demo/source-cite-demo` : `cd frontend && pnpm dev` puis ouvrir `http://localhost:3000/demo/source-cite-demo` ; vérifier visuellement les 3 instances avec picto cliquable
- [ ] T041 — E2E Playwright `frontend/tests/e2e/source-cite.spec.ts` (post-MVP) : nécessite que des UUIDs réels soient seedés en DB ; à activer une fois F07 (catalog-sources-management) livré
- [ ] T038 — animation gsap slide-up : ouvrir bottom sheet et vérifier visuellement la fluidité (gsap pas encore intégré, fallback CSS pour MVP)

## US5 — Annexe PDF

- [ ] T042 — vérifier visuellement le markdown généré injecté dans un export PDF F24 (helper `to_pdf_section` est passthrough — sera branché quand F24 livrera son moteur WeasyPrint)

## Audits SQL

- [ ] T049 — exécuter `psql ... -f backend/scripts/audit_unsourced_catalog.sql` après seed catalogue (F07/F09) ; doit retourner 0 lignes une fois le backfill effectué
- [ ] T050 — planifier l'exécution hebdomadaire de `backend/scripts/audit_double_validation.sql` (cron) ; doit toujours retourner 0 lignes
