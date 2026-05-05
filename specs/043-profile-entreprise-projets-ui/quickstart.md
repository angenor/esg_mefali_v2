# Quickstart — F43 (Profil entreprise & projets UI)

## 1. Pré-requis

- Backend F11 + F12-profile + F22 déployés (déjà sur `main`).
- Postgres dockerisée up (`make db-up`).
- Backend en local (`make backend`) sur port 8010.
- Frontend en local (`make frontend`) sur port 3001.

## 2. Comptes de test

```bash
# Crée un compte PME via l'inscription, puis seed un projet brouillon en SQL si besoin.
curl -X POST http://localhost:8010/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"pme43@test.local","password":"Test#0000-Mefali","raison_sociale":"PME F43 Test","accept_cgu":true}'
```

## 3. Parcours manuel (US par US)

1. **US 1 — Profil entreprise** : se connecter, ouvrir `/profil/entreprise`.
   - Vérifier les 5 sections affichées (Identité, Taille, Localisation, Gouvernance, Pratiques).
   - Cliquer sur Identité, saisir « Raison sociale = `Test SARL` ». Attendre ~800 ms : toast « Enregistré ».
   - Recharger la page → la valeur persiste.
   - Vérifier la barre de complétion en haut (passe de 0 % à >0 %).
2. **US 2 — Money typé** : aller dans Taille, saisir CA = `50000000` XOF. Vérifier l'affichage formaté `50 000 000 FCFA` et la conversion `≈ 76 224,91 €`.
3. **US 3 — Liste projets** : aller dans `/profil/projets`. Vérifier l'empty state. Cliquer « Créez votre premier projet », parcourir les 4 étapes du wizard, soumettre. Le projet apparaît dans la liste avec son badge statut « Brouillon » et son score ESG (0 par défaut → badge rouge).
4. **US 4 — Sync chat ↔ profil** : ouvrir `/chat` dans un autre onglet, demander « mets ma raison sociale à `Sync Test SAS` ». Revenir sur l'onglet `/profil/entreprise` → flash « Mis à jour par le chat » en moins de 2 s, valeur reflétée.
5. **US 5 — Documents et soft delete** : ouvrir un projet, téléverser un PDF de test (< 25 Mo). L'aperçu apparaît. Tester un `.txt` → message d'erreur. Cliquer « Supprimer » → confirmer → la carte disparaît de la liste active.
6. **US 6 — Historique (P2)** : cliquer « Historique » sur la section Identité → drawer s'ouvre avec les modifications listées (auteur + ts + source).

## 4. Tests automatisés

```bash
# Frontend unit + composants
cd frontend && pnpm vitest run app/composables/__tests__/useEntrepriseProfile.test.ts
pnpm vitest run app/composables/__tests__/useProjet.test.ts
pnpm vitest run tests/components/profil

# E2E (Playwright)
pnpm playwright test tests/e2e/profil-entreprise-autosave.spec.ts
pnpm playwright test tests/e2e/profil-projets-wizard.spec.ts
pnpm playwright test tests/e2e/profil-conflict-chat-sync.spec.ts
```

## 5. Critères de succès vérifiables

| SC      | Vérification quickstart                                                          |
|---------|----------------------------------------------------------------------------------|
| SC-001  | DevTools Performance / Lighthouse → LCP < 1 s sur `/profil/entreprise`.          |
| SC-002  | Tester saisie + reload immédiat avant 2 s : aucune perte. (test e2e dédié)       |
| SC-003  | Mesurer délai event chat → flash UI dans la console (perf marker).               |
| SC-004  | Compléter 5 champs → vérifier complétion 30 % → 80 %.                             |
| SC-005  | Chronomètre wizard → < 3 min.                                                    |
| SC-006  | Saisir un CA décimal `12345.67`, recharger → valeur exacte.                      |
| SC-007  | Tenter de saisir un pays inexistant → refus.                                     |
| SC-008  | Reproduire le conflit US 4 + édition locale → dialogue 3 choix.                  |
| SC-009  | Supprimer puis demander à un admin de restaurer dans 30 j (manuel).              |
| SC-010  | `pnpm vitest run --coverage` → > 80 % sur `app/components/profil` et `app/composables/useEntrepriseProfile|useProjet|useProjetWizard|useDecimal`. |

## 6. Dépannage rapide

| Symptôme                                              | Piste                                                                 |
|-------------------------------------------------------|-----------------------------------------------------------------------|
| Toast `Modifications non sauvegardées` persistant     | Vérifier `make backend` actif et `NUXT_PUBLIC_API_BASE` correct.      |
| Conflict dialog ouvert sans raison                    | Une seconde session est-elle ouverte ? Le compte test est unique.     |
| Devises non affichées                                 | Vérifier `useDecimal.PEG_XOF_EUR === '655.957'`.                       |
| Pays introuvables                                     | Charger `app/data/countries-iso2.ts` (liste locale).                  |
