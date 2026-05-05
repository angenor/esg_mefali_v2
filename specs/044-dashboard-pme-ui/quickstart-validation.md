# F44 — Validation manuelle quickstart

**Date** : 2026-05-03
**Branche** : `044-dashboard-pme-ui`

Checklist de validation manuelle des 7 scénarios du `quickstart.md` en environnement local. À cocher après exécution réelle. Les fixtures backend (compte plein / vierge / etc.) sont à brancher post-MVP : marquer `[~]` si la pré-condition est simulée à la main.

| # | Scénario | Statut | Notes |
|---|----------|--------|-------|
| S1 | Compte plein → 6 cartes en < 1,5 s, navigation OK | [ ] | Mesurer LCP via DevTools |
| S2 | Compte vierge → 6 cartes en mode CTA (aucun "0" sec) | [ ] | |
| S3 | Cocher étape plan d'action → spinner < 1 s + persistance | [ ] | Vérifier audit log côté backend |
| S4 | Export RGPD → fichier `esg-mefali-export-AAAA-MM-JJ.json` | [ ] | Vérifier cloisonnement compte |
| S5 | Sync auto chat → carte ESG MAJ < 90 s entre onglets | [ ] | Cas A (même onglet) + cas B (autre onglet) |
| S6 | Erreur isolée carte intermédiaires → 6 cartes principales OK | [ ] | Mock 5xx via DevTools |
| S7 | Mobile 375 px → grille empilée, 60 fps au scroll | [ ] | DevTools mobile |

**Validation Constitution (re-check post-implémentation)** :
- [ ] P1 Sourçage : badge `<DashboardSourceList>` présent sur cartes ESG (TODO post-MVP : brancher source_ids quand F32 les expose).
- [ ] P2 RLS : aucun appel direct depuis le frontend sans `credentials: include` ; tous les endpoints sont sous `/me/*`.
- [ ] P5 Money : pas de Number arithmetic sur les valeurs monétaires (tco2e formaté en string).
- [ ] P8 Sync bidirectionnelle : EventBus `useDashboardBus` câblé pour les 9 events de la table `EVENT_TO_BLOCK_MAP`.

**Tests automatisés** :
- [ ] `pnpm vitest run` vert (≥ 80 % couverture sur le code F44).
- [ ] `pnpm playwright test tests/e2e/dashboard-*.spec.ts` vert (avec fixtures backend).
- [ ] `pnpm lint` sans warning sur les fichiers F44.

**Lighthouse mobile** :
- [ ] LCP < 1,5 s sur `/dashboard` plein (cf. SC-001).
- [ ] CLS < 0,1.
- [ ] Aucun warning a11y critique.
