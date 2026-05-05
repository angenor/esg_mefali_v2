# Quickstart — Plan d'action ESG UI (F45)

Comment tester la feature localement de bout en bout, sans l'attendre en production.

## Prérequis

- Stack démarrée selon `CLAUDE.md` (3 terminaux : `make db-up`, `make backend`, `make frontend`).
- Une PME seedée avec :
  - Un compte authentifié (`role=PME`).
  - Un profil entreprise au moins 50 % complété (sinon redirection EmptyStateLanding F42).
  - Un `ScoreCalculation` récent (sinon US7 empty state).
  - Au moins un gap exploitable (sinon US8 empty state).

## 1. Seed minimal manuel

```bash
# Terminal backend
cd backend && source .venv/bin/activate

# Créer un compte PME via le helper de tests existant
python -m app.scripts.seed_pme --email demo@pme.local --password demo1234

# Lancer un scoring (dépend de l'état du référentiel seedé)
curl -X POST http://localhost:8010/me/scoring/calculate \
  -H "Authorization: Bearer $(./scripts/token-for.sh demo@pme.local)" \
  -H "Content-Type: application/json"

# Générer le plan d'action initial (12 mois)
curl -X POST "http://localhost:8010/me/action-plan/generate?horizon=12" \
  -H "Authorization: Bearer $(./scripts/token-for.sh demo@pme.local)"
```

> Adapter les chemins de scripts selon ce qui existe (cf. F31 helpers de test si présents). Les commandes ci-dessus sont indicatives — la voie officielle reste les tests E2E.

## 2. Smoke test manuel

1. Ouvrir `http://localhost:3001/login`, se connecter (`demo@pme.local` / `demo1234`).
2. Naviguer vers `http://localhost:3001/plan-action`.
3. **US1** : la timeline s'affiche en moins de 2 s, segmentée par horizon. Survoler un jalon → tooltip avec titre.
4. **US2** : cliquer sur un filtre « Priorité = Haute ». Vérifier l'URL (`?priority=haute`) et la liste filtrée.
5. **US3** : cocher une checkbox sur une carte `todo` → bascule à `done` instantanément. Recharger la page → persistance OK.
6. **US3 bottom sheet** : cliquer « Modifier statut » → bottom sheet ouvert avec champs statut + responsable. Valider → card mise à jour.
7. **US4** : la barre de progression et le KPI `X/Y` reflètent le changement après chaque coche.
8. **US5** : cliquer « Régénérer mon plan » → modale → confirmer avec horizon = 6 mois. Vérifier que la version passe de v1 à v2 et que les étapes sont nouvelles.
9. **US6** : basculer le toggle horizon entre 6 / 12 / 24 → la timeline + liste se restreint au sous-ensemble.
10. **US7** : se connecter avec un compte PME sans scoring → `/plan-action` affiche l'empty state avec CTA `/scoring`.
11. **US8** : seed un compte avec scoring complet sans gaps → message de célébration.
12. **US9** : ouvrir `/plan-action` dans un onglet, déclencher une mutation via le chat (autre onglet) → la card du premier onglet se rafraîchit dans la seconde.

## 3. Test E2E automatisé

```bash
# Depuis la racine
cd frontend
pnpm playwright test tests/e2e/plan-action-*.spec.ts
```

La suite couvre les 12 user stories + edge cases (filtres invalides, double-clic régénération, rollback échec PATCH, `prefers-reduced-motion`, mobile vertical layout).

## 4. Test responsive

- Desktop (1366×768) : timeline horizontale + liste 2 colonnes.
- Tablette (768×1024) : timeline horizontale compacte + liste 1 colonne.
- Mobile (390×844) : timeline **verticale**, liste 1 colonne.

Test rapide via DevTools responsive ; test E2E via `playwright.devices['iPhone 13']`.

## 5. Test `prefers-reduced-motion`

Dans Chrome DevTools → Rendering → « Emulate CSS media feature `prefers-reduced-motion: reduce` ». Recharger `/plan-action` → vérifier l'absence d'animation stagger sur les jalons et que le bottom sheet apparaît sans transition.

## 6. Vérifier la sync chat ↔ plan-action

```bash
# Dans la console du navigateur sur /plan-action
window.__chatBus.emit('entity_updated', { entity_type: 'action_step', entity_id: '<uuid d\'une step>' });
```

→ Observer la card cible se rafraîchir (re-fetch ciblé visible dans l'onglet Network).

## 7. Vérifier le multi-tenant (P2)

Se connecter avec un compte PME du tenant A, copier l'UUID d'une de ses étapes. Se déconnecter, se connecter avec une PME du tenant B. Tenter `PATCH /me/action-plan/steps/<uuid_de_A>` → doit retourner **404**, jamais 403, jamais le contenu de A.

## 8. Lint + tests unitaires

```bash
make test           # backend + frontend
make lint           # ruff + eslint
```

Les tests vitest doivent passer avec coverage ≥ 80 % sur les fichiers nouveaux (`useActionPlan*`, `actionPlan` store, `mapPlanToTimelineBuckets`).
