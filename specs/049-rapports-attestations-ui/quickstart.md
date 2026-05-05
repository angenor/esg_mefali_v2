# Quickstart — F49 (UI rapports & verify)

## Prérequis

- Branche `049-rapports-attestations-ui` checked out.
- F24 (rapports backend) et F30 (attestations backend) sont mergées et migrées.
- Postgres dockerisé démarré, backend FastAPI lancé sur `:8010`, frontend Nuxt sur `:3001` (cf. `CLAUDE.md`).

## Lancer l'environnement

```bash
# Terminal 1
make db-up

# Terminal 2
make backend  # uvicorn :8010

# Terminal 3
make frontend # nuxt :3001
```

## Données de test

Avant de tester l'UI, peupler l'environnement :

```bash
cd backend && source .venv/bin/activate
python -m app.scripts.seed_demo_pme --account demo
python -m app.scripts.seed_demo_rapports --account demo --count 5
python -m app.scripts.seed_demo_attestations --account demo --count 3 --include-revoked 1
```

> Les scripts `seed_demo_*` peuvent ne pas exister encore ; à défaut, créer manuellement via les endpoints `/me/rapports/generate` et `/me/attestations` ou via psql.

## Parcours manuel — `/rapports`

1. Ouvrir `http://localhost:3001/login` → s'authentifier en tant que PME `demo`.
2. Naviguer vers `http://localhost:3001/rapports`.
3. **US1** : vérifier deux tables (rapports, attestations), 5 rapports listés, 3 attestations dont 1 révoquée.
4. **US2** : cliquer sur une ligne de rapport → drawer s'ouvre avec aperçu PDF + métadonnées. Vérifier que l'URL d'iframe contient `t=…&sig=…` et qu'elle expire (recharger après 6 min → 401).
5. **US3** : cliquer « Nouveau rapport » → modale → choisir type `conformite`, période, valider. Observer la barre de progression SSE puis le lien « Télécharger ».
6. **US3 rattrapage** : pendant la génération, recharger la page → la génération est récupérée et la progression continue.
7. **US5** : sur une attestation active, cliquer « Partager » → modale avec URL copiable + bouton « Télécharger QR ». Scanner le QR avec un téléphone → ouvre `/verify/{id}`.
8. **US6** : cliquer « Révoquer » sur une attestation active → confirmer, sélectionner motif `erreur_emission` → la table met à jour le statut en « révoquée ».

## Parcours manuel — `/verify/{id}`

1. Ouvrir un onglet de navigation privée (sans cookie de session).
2. Coller l'URL `/verify/<public_id_actif>` → vérifier badge ✓ vert, raison sociale, type, dates, KPI lisibles avec repères de source.
3. Coller l'URL `/verify/<public_id_revoque>` → bandeau rouge above-the-fold avec date et motif.
4. Coller l'URL `/verify/inconnu_xxx` → page 404 sobre.
5. Cliquer le sélecteur EN → libellés statiques + énumérations basculent ; raison sociale et valeurs numériques restent inchangées.
6. Recharger avec JavaScript désactivé (DevTools → Network conditions → JS off) → vérifier que verdict, identité, dates et KPI sont visibles.

## Vérifications automatisées

```bash
# Frontend tests
cd frontend
pnpm vitest run path/to/F49-tests
pnpm playwright test e2e/rapports-generation.spec.ts e2e/verify-public.spec.ts

# Lighthouse mobile sur /verify
pnpm dlx @lhci/cli@0.13.x autorun --collect.url=http://localhost:3001/verify/<public_id_actif> --collect.settings.preset=mobile
# attendu : Performance ≥ 95, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95
```

## Critères de succès vérifiables (extraits SC-001 → SC-009)

| Critère | Comment vérifier |
|---|---|
| SC-001 (≤ 2 clics pour télécharger) | Compter clics depuis arrivée sur `/rapports` → bouton « Télécharger » ligne. |
| SC-002 (95 % génération aboutie) | Lancer 20 générations consécutives en script, mesurer succès. |
| SC-003 (LCP < 1,2 s) | Lighthouse mobile sur `/verify/<id_actif>`. |
| SC-004 (révocation above-the-fold sur 320×568) | DevTools → device 320×568 → rafraîchir une URL révoquée. |
| SC-005 (Lighthouse 95+) | Voir commande Lighthouse ci-dessus. |
| SC-006 (QR scannable) | Tester scan sur 5 téléphones différents à 30 cm. |
| SC-007 (no leak multi-tenant) | Forger un `public_id` d'un autre tenant → 404 attendu. |
| SC-008 (no-JS fallback) | Désactiver JS, vérifier visibilité du verdict + identité + dates + KPI. |
| SC-009 (révocation propagée < 60 s) | Révoquer → recharger `/verify/{id}` en navigation privée après 60 s → bandeau visible. |

## Dépannage

| Symptôme | Solution |
|---|---|
| Drawer aperçu PDF vide | Vérifier que `GET /me/rapports/{id}/preview-url` est livré côté backend. Sinon fallback bouton « Télécharger ». |
| Génération bloquée à 0 % | Vérifier que l'endpoint SSE existe ; sinon le composable doit basculer en polling 1 s automatiquement. |
| QR non scannable | Augmenter le `errorCorrectionLevel` à `H` (déjà par défaut), vérifier la taille rendue (≥ 200 px). |
| `/verify/{id}` lent | Vérifier `Cache-Control` sur la réponse, vérifier que le CDN est actif en prod. |
| Bascule EN n'a pas d'effet sur un libellé | Le code n'est pas dans `i18n/verify/*.json` ou le backend n'expose pas `label_en` (cf. R6). |
