# Quickstart — Tester F44 Dashboard PME UI localement

**Date** : 2026-05-03
**Audience** : développeur frontend implémentant ou revoyant la feature.

## Prérequis

- Avoir suivi la mise en route de base (`make setup`, `make db-reset`, `make migrate`).
- Trois terminaux ouverts comme décrit dans `CLAUDE.md` : `make db-up`, `make backend`, `make frontend`.
- Un compte PME de test (créer via `/register` puis basculer en mode connecté). Idéalement deux comptes pour valider le cloisonnement RLS.

## Scénarios de test manuel

### S1 — PME pleine de données (parcours principal)

1. Avec votre compte PME, compléter le profil entreprise à ≥ 50 % (utiliser F43 — `/profil/entreprise`).
2. Lancer un scoring depuis `/scoring` (F47) — au moins 1 référentiel calculé.
3. Saisir un bilan carbone depuis `/carbone` (F48) — au moins 1 année.
4. Calculer un score crédit depuis `/credit-score` (F49).
5. Créer une candidature depuis `/candidatures`.
6. Générer un rapport depuis `/rapports`.
7. Générer une attestation depuis `/rapports/{id}/attestation`.
8. Ouvrir `/dashboard`. Attendu : six cartes peuplées, bandeau avec raison sociale, bouton "Discuter avec l'IA".
9. Vérifier qu'aucune carte n'affiche d'écran blanc à aucun moment (dégrader le réseau dans devtools pour tester les squelettes).

### S2 — Compte vierge (état vide intelligent — US3)

1. Créer un nouveau compte PME, compléter le profil ≥ 50 % mais ne lancer aucun calcul.
2. Ouvrir `/dashboard`. Attendu :
   - Carte Scoring → CTA "Lancez votre premier diagnostic ESG" (lien vers `/scoring`).
   - Carte Carbone → CTA "Saisir mon premier bilan carbone".
   - Carte Crédit → CTA "Calculer mon score crédit".
   - Carte Candidatures → CTA "Découvrir les financements".
   - Carte Rapports → CTA "Générer mon premier rapport".
   - Carte Plan d'action → CTA "Construire mon plan d'action".
   - Carte Intermédiaires masquée (pas de projet).
3. Aucune carte ne doit afficher "0" sec ou "—" sec.

### S3 — Cocher une étape de plan d'action (US2)

1. PME avec ≥ 4 étapes pending dans le plan d'action.
2. `/dashboard`. La carte plan d'action liste les 3 prochaines étapes prioritaires.
3. Cocher la première : voir mini-spinner < 1 s, puis l'étape disparaît, la 4ᵉ apparaît.
4. Recharger la page : la modification a persisté.
5. Vérifier l'audit log côté backend : `SELECT * FROM audit_log WHERE field = 'status' AND entity_type = 'action_plan_step' ORDER BY ts DESC LIMIT 1;` doit montrer `source_of_change = 'manual'`.

### S4 — Export de données (US4)

1. Cliquer sur "Exporter mes données" en haut à droite.
2. Vérifier le fichier téléchargé : nom `esg-mefali-export-AAAA-MM-JJ.json`, contenu JSON valide, présence des clés `entreprise`, `projets`, `candidatures`, `scores`, …, `exported_at`.
3. Vérifier qu'aucune donnée d'un autre compte n'apparaît (créer un second compte avec données et faire la même opération — comparer).
4. Cliquer deux fois rapidement sur le bouton — un seul téléchargement doit être déclenché (FR-021).

### S5 — Sync chat (US8)

1. PME avec dashboard ouvert sur `/dashboard`, score ESG = X.
2. Ouvrir `/chat` dans un second onglet, demander au LLM "Recalcule mon score GCF".
3. Une fois le tool result reçu (vérifier dans les logs front : event `scoring:computed`).
4. **Cas A — même onglet** : retourner sur `/dashboard`, le score doit être à jour en < 2 s.
5. **Cas B — autres onglets** : laisser le dashboard ouvert > 60 s (jusqu'au prochain polling). Le score doit se mettre à jour automatiquement.

### S6 — Échec d'une carte sans casser le reste (US — edge)

1. Dans devtools, intercepter `/me/dashboard/summary` et faire échouer la requête. Recharger.
2. Toutes les cartes affichent l'état d'erreur global (`store.blockErrors['*']`).
3. Cliquer "Réessayer" — succès.
4. Pour tester l'isolation par carte (si implémentée par bloc) : intercepter `/me/matching/recommendations` (carte intermédiaires) et faire échouer. Les six cartes principales restent fonctionnelles, seule la carte intermédiaires affiche "Réessayer".

### S7 — Mobile (SC-008)

1. Devtools → mode responsive 375×667.
2. `/dashboard` : les cartes s'empilent en 1 colonne, scroll fluide.
3. Vérifier qu'aucune carte ne déborde horizontalement, que les mini-charts sont lisibles.

## Commandes de test automatisé

```bash
# Frontend — unit + components
cd frontend
pnpm vitest run app/composables/__tests__/useDashboardSummary.test.ts
pnpm vitest run app/composables/__tests__/useDataExport.test.ts
pnpm vitest run app/stores/__tests__/dashboard.test.ts
pnpm vitest run app/lib/__tests__/mapSummaryToCardViewModels.test.ts
pnpm vitest run tests/components/dashboard/

# Frontend — E2E
pnpm playwright test tests/e2e/dashboard-full-data.spec.ts
pnpm playwright test tests/e2e/dashboard-empty-account.spec.ts
pnpm playwright test tests/e2e/dashboard-action-plan-toggle.spec.ts
pnpm playwright test tests/e2e/dashboard-export.spec.ts
pnpm playwright test tests/e2e/dashboard-export-double-click.spec.ts
pnpm playwright test tests/e2e/dashboard-chat-sync.spec.ts
pnpm playwright test tests/e2e/dashboard-card-failure-isolation.spec.ts

# Backend — non modifié, mais s'assurer que F32 passe toujours
cd ../backend && source .venv/bin/activate
pytest tests/dashboard/ -v
```

## Validation des success criteria

| SC | Comment valider |
|----|-----------------|
| SC-001 | Lighthouse mobile sur `/dashboard` avec compte plein → LCP < 1,5 s sur 4G simulé. |
| SC-002 | Test utilisateur : 5 personnes naïves doivent citer les 4 indicateurs en < 5 s. |
| SC-003 | Métrique posthog/analytics (post-MVP) : taux de clic dashboard → page détail > 60 %. |
| SC-004 | Compteur conversion (post-MVP) : nouveaux comptes ayant fait le 1er diagnostic ≤ 7 j > 50 %. |
| SC-005 | Mesure perf E2E : timestamp clic export → début download < 5 s. |
| SC-006 | Mesure perf E2E : timestamp clic checkbox → étape suivante affichée < 1 s. |
| SC-007 | Vérification manuelle / E2E `dashboard-empty-account.spec.ts` : aucune carte vide ne montre "0" sec. |
| SC-008 | Test manuel mobile + Lighthouse mobile fluide. |
| SC-009 | Métrique analytics post-MVP. |
| SC-010 | E2E `dashboard-card-failure-isolation.spec.ts`. |

## Diagnostic rapide

| Symptôme | Vérifier |
|---------|----------|
| Cartes vides en boucle | `GET /me/dashboard/summary` répond-il ? Token valide ? `account_id` non null ? |
| Carte plan d'action ne se rafraîchit pas après check | `PATCH /me/action-plan/steps/{id}` → 200 ? `store.invalidate('next_actions')` est-il appelé ? |
| Sync chat ne fonctionne pas | `useChatEventBus` est-il bien instancié comme singleton ? L'event est-il dans la map R5 ? |
| Export télécharge un fichier vide | `GET /me/data/export` → 200 ? Le `Blob` est-il bien construit avec le bon `Content-Type` ? |
| LCP > 1,5 s | Vérifier que les squelettes sont rendus en SSR ; le polling ne doit pas être déclenché côté serveur. |
