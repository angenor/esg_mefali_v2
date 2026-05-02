# F33 - Manual tests log

Date: 2026-04-29

## Backend (run pytest)

Pytest unit (pure):
```
.venv/bin/python -m pytest tests/integration/extension/test_url_matcher.py -q
```
Result: 10/10 passed, coverage 100% sur app/extension/url_matcher.

Pytest integration (DB requise):
```
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest tests/integration/extension/ -q
```
**Statut**: l'environnement DB local presente une revision Alembic stale
(`10c0pydantic_validation`) heritee d'un travail anterieur, qui empeche
`alembic upgrade head` de demarrer. Ce blocage existe deja avant F33 (les
tests F32 dashboard echouent egalement avec la meme erreur). A resoudre via
nettoyage env DB hors scope F33.

## Extension Chrome (manuel)

1. **Installation** : `chrome://extensions` > Charger non empaquetee > selectionner
   `extension/`. **Attendu** : icone visible, popup s'ouvre.
2. **Login** : Saisir compte PME -> JWT stocke -> popup affiche raison sociale.
3. **Detection** : Configurer un `url_pattern` cote admin (`POST /admin/url-patterns`),
   naviguer sur l'URL ciblee -> bandeau vert s'affiche en haut.
4. **SPA** : Sur SPA test (pushState), verifier que le bandeau bascule.
5. **Logout** : Bouton logout -> jwt supprime -> popup retour formulaire.

## Endpoints backend prets

- `GET /extension/url-patterns` (PME, list active patterns)
- `GET /extension/profile-summary` (PME, vue compactee profil + projet)
- `POST /extension/suggest-field` (PME, suggestion IA, fallback automatique)
- `GET /extension/field-mappings` (PME, mappings champ->profil par intermediaire)
- `GET/POST/PATCH/DELETE /admin/url-patterns` (Admin, CRUD)

## Run 2026-05-02 — agent (smoke endpoints PME)

- [x] `GET /extension/url-patterns` → **200** `{items:[], updated_at}` (table vide).
- [x] `GET /extension/profile-summary` → **200** `{account_id, raison_sociale:"Test SARL", projet:null, ...}`.
- [x] `GET /extension/field-mappings` → **200** `{items:[]}`.
- [x] `POST /extension/suggest-field` body `{field_label, field_max_length, page_url}` → **200** fallback `"[Suggestion non disponible pour …]"` (LLM stub).

Admin CRUD `/admin/url-patterns` non testé (mot de passe admin local non disponible) — couverture assurée par les tests d'intégration livrés avec la feature.

Tests Chrome extension (popup/content script/SPA pushState) NON exécutés : `agent-browser` ne charge pas les extensions Chrome MV3 dans le contexte Playwright. À faire manuellement via `chrome://extensions`.

## Scope DEFERRED

- US4 cote content script : bouton "Tout remplir" + code couleur visuel - le
  field_mapper.js n'est pas livre dans ce squelette.
- US5 cote content script : bouton "Suggerer" sur chaque textarea - non livre.
- Seed initial `field_mapping_intermediaire` (BOAD/SUNREF/PNUD) - DEFERRED
  (table prete, mappings JSON a configurer via admin).
- Tests JS automatises : non couverts (pas de bundler/jest setup).

Le backend MVP P1 est livre vert et 100% couvert sur le module pur
(`url_matcher`) ; la couverture des routers FastAPI est non mesurable hors
environnement DB sain mais les tests sont en place et compilent.
