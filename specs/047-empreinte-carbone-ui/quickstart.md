# Quickstart — F47 Empreinte carbone UI

**Audience** : développeur reprenant la feature ou démo après merge.
**Pré-requis** : avoir lancé une fois `make setup` et `make migrate`.

## 1. Démarrer la stack (3 terminaux)

```bash
# Terminal 1 — Postgres
make db-up
docker compose ps    # vérifier "healthy"

# Terminal 2 — Backend FastAPI
make backend         # uvicorn :8010
curl http://localhost:8010/health    # → {"status":"ok","db":"ok"}

# Terminal 3 — Frontend Nuxt
make frontend        # nuxt dev :3001
```

Ouvrir [http://localhost:3001](http://localhost:3001) et se connecter (ou créer un compte PME via `/login`).

## 2. Vérifier les nouveaux endpoints backend (F47)

```bash
# (depuis backend/ avec .venv activé)
TOKEN=...   # JWT PME

# 2.1 — Index multi-année (vide à la création)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8010/me/carbon
# → { "entries": [] }

# 2.2 — Créer une empreinte initiale (POST compute existant F28)
curl -X POST http://localhost:8010/me/carbon/compute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"year": 2026, "source_data": [
        {"code": "electricite", "quantity": "50000", "country": "CI", "source_id": "<UUID-source-verified>"}
      ]}'
# → { "id": "...", "total_tco2e": "...", ... }

# 2.3 — Index après création
curl -H "Authorization: Bearer $TOKEN" http://localhost:8010/me/carbon
# → { "entries": [{ "year": 2026, "total_tco2e": "...", ... }] }

# 2.4 — Recalcul global
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8010/me/carbon/2026/recompute
# → { "id": "<nouveau>", "previous_footprint_id": "<précédent>", ... }

# 2.5 — Édition d'une ligne
curl -X POST http://localhost:8010/me/carbon/2026/edit-line \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"electricite","quantity":"45000","country":"CI","source_id":"<UUID-source-verified>"}'
# → { "id": "<encore-nouveau>", "previous_footprint_id": "...", "edited_line_code": "electricite", ... }
```

## 3. Parcours UI bout-en-bout

### 3.1 Compte vide → wizard

1. Aller sur `/carbone` avec un compte sans empreinte.
2. **Attendu** : la page présente le `<EmptyStateWizard>` (3 cartes énergie/déplacements/achats).
3. Cliquer « Commencer ». Le bottom sheet s'ouvre en mode `show_form`, étape 1/3 (énergie : `electricite kWh` + source).
4. Compléter les 3 étapes. Au pas 3 → `POST /me/carbon/compute` est émis avec le source_data agrégé.
5. **Attendu** : le wizard se ferme, la synthèse apparaît avec KPI total + donut + courbe (1 point seulement = année courante).
6. Recharger la page → l'empreinte est persistée, le wizard ne s'affiche plus.

### 3.2 Édition d'une ligne

1. Sur `/carbone` (avec empreinte), déplier `<ScopeAccordion scope="2">`.
2. Cliquer « Modifier » sur la ligne `electricite`.
3. **Attendu** : bottom sheet `ask_form` ouvert avec `quantity` pré-rempli, `country`, `source_id` (sélecteur sur les sources `verified` du tenant).
4. Modifier la quantité, choisir une source `verified`, valider.
5. **Attendu** : la ligne se met à jour, KPI total recalculé, delta visible, toast « Empreinte mise à jour ».
6. Vérifier dans `audit_event` : `entity = "carbon_footprint"`, `field = "edit-line"`, `source_of_change = "manual"`.

### 3.3 Tentative édition sans source

1. Même parcours qu'en 3.2 mais ne renseigner aucune source.
2. **Attendu** : bouton « Valider » désactivé OU message d'erreur français explicite après tentative (« Source obligatoire pour toute donnée carbone »).

### 3.4 Recalcul global

1. Sur `/carbone`, cliquer le bouton « Recalculer » dans `<RecalcStrip>`.
2. **Attendu** : spinner global, bouton désactivé, retour < 2 s, horodatage « Dernier calcul » mis à jour.
3. Si les facteurs ont été révisés en base entre temps (ex. SQL `UPDATE facteur_emission ... SET valid_to = ...` puis insertion d'une nouvelle version), le total change → vérifié.

### 3.5 Couverture < 60 %

1. Démarrer avec une seule ligne `electricite` (1 poste sur 12 attendus = ~8 %).
2. **Attendu** : `<LowCoverageBanner>` visible avec CTA « Compléter ».

### 3.6 Sync chat

1. Ouvrir `/carbone` dans onglet A et `/chat` dans onglet B.
2. Onglet B : poser à l'IA « ajoute 8 000 km de déplacements professionnels avec la facture #2026-03 ». Le tool LLM `update_carbon_data` (F28) doit appeler `POST /me/carbon/{year}/edit-line` (ou équivalent) puis émettre `entity_updated{carbon_footprint}` sur l'EventBus.
3. **Attendu sur onglet A** : la ligne `deplacements` apparaît, KPI total recalculé, < 1 s, sans rechargement.

### 3.7 Switch facteurs (P2 désactivé)

1. Sur `/carbone`, vérifier la présence de `<FactorReferentielSwitch>` avec badge « Estimation, pas référence officielle » et infobulle « Comparateur IPCC à venir ».
2. Le switch est `disabled` au MVP.

## 4. Tests automatisés

```bash
# Backend (depuis backend/ avec .venv activé)
pytest tests/carbon/test_index_endpoint.py -v
pytest tests/carbon/test_recompute_endpoint.py -v
pytest tests/carbon/test_edit_line_endpoint.py -v
pytest tests/carbon/test_carbon_source_item_source_id.py -v

# Frontend (depuis frontend/)
pnpm vitest run app/composables/__tests__/useCarbon.test.ts
pnpm vitest run app/composables/__tests__/useCarbonHistory.test.ts
pnpm vitest run app/composables/__tests__/useCarbonEdit.test.ts
pnpm vitest run app/composables/__tests__/useCarbonWizard.test.ts
pnpm vitest run app/lib/__tests__/groupCarbonByScope.test.ts
pnpm vitest run app/lib/__tests__/computeCarbonCoverage.test.ts
pnpm vitest run app/stores/__tests__/carbon.test.ts
pnpm vitest run app/components/carbone

# E2E (Playwright, depuis frontend/)
pnpm playwright test tests/e2e/carbone.spec.ts
```

## 5. Vérifier la coverage globale

```bash
make test     # backend pytest --cov + frontend vitest run
# fail_under = 80 (backend/pyproject.toml)
```

## 6. Points de contrôle constitutionnels (à valider en revue)

- [ ] **P1** : 100 % des lignes affichées exposent un facteur + un pin source. Aucune ligne créée par l'UI sans `source_id`.
- [ ] **P3** : `audit_event` contient une row par `edit-line` et par `recompute` (`source_of_change = manual`).
- [ ] **P4** : éditer une ligne ne réécrit jamais un `carbon_footprint` existant ; nouvelle row à chaque fois.
- [ ] **P5** : aucun `float` dans les payloads ni dans les sommes côté UI ; tous les `Decimal` passent par `decimal.js`.
- [ ] **P8** : édition manuelle émet `context_invalidated` ; mutation chat émet `entity_updated` ; les deux surfaces se synchronisent < 1 s.
- [ ] **P10** : aucune saisie inline. Wizard et édition passent toujours par `<ChatBottomSheet>`. Bouton « Répondre librement » présent dans le wizard.
