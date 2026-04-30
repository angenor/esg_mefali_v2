# Extension Chrome ESG Mefali (F33 - MVP squelette)

## Installation locale (mode unpacked)

1. Lancer le backend FastAPI (`uvicorn app.main:app --reload`) - URL par defaut `http://localhost:8000`.
2. Ouvrir `chrome://extensions`, activer "Mode developpeur".
3. Cliquer "Charger l'extension non empaquetee", selectionner ce dossier.
4. Cliquer l'icone de l'extension > popup s'ouvre > saisir email/mot de passe d'un compte PME ESG Mefali.

## Backend URL

Par defaut `http://localhost:8000`. Pour changer, editer la constante `BACKEND` dans
`popup.js`, `background.js`, `content.js` (et le `host_permissions` du manifest).

## Limites MVP

- Pas de pipeline de build : JS vanilla, pas de bundler.
- Aucun test JS automatise. Tests manuels documentes dans
  `.cc-runtime/logs/manual-tests-33.md`.
- US4 (form-fill) et US5 (suggest sur champ) non finalises cote content script -
  endpoints backend prets pour US4/US5 (`/extension/profile-summary`,
  `/extension/suggest-field`, `/extension/field-mappings`).

## Endpoints utilises

- `POST /auth/login`
- `GET /extension/profile-summary`
- `GET /extension/url-patterns`
- `GET /extension/field-mappings`
- `POST /extension/suggest-field`
