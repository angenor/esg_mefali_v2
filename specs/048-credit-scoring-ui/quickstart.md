# Quickstart — F48 Credit scoring UI

## Prérequis

- Repo cloné, `make setup` exécuté, `.env` renseigné (`DB_PASSWORD`, `JWT_SECRET`, etc.).
- F29 backend opérationnel (`make migrate` à jour).
- Node 22 + pnpm 9 installés (frontend), Python 3.12 + venv (backend).

## Démarrer les serveurs

```bash
# Terminal 1 — Postgres
make db-up
docker compose ps   # vérifier "healthy"

# Terminal 2 — Backend FastAPI
make backend
curl http://localhost:8010/health   # → {"status":"ok","db":"ok"}

# Terminal 3 — Frontend Nuxt
make frontend
# → http://localhost:3001
```

## Smoke test manuel

1. Aller sur `http://localhost:3001/credit-score`.
2. **Si compte sans score** : un wizard 4 étapes s'ouvre. Le compléter avec des montants en XOF (CA 12 500 000, EBE 850 000, dette 3 200 000, fonds propres 5 400 000) puis valider l'ESG/Gouvernance.
3. À la fin : la page bascule sur la vue synthèse, gauge animée vers le score calculé.
4. Vérifier :
   - Gauge affiche un score 0-100 et la classification correspondante (≥80 Excellent, 60-79 Bon, 40-59 À améliorer, <40 Insuffisant).
   - 4 cartes sous-scores (ou état « non calculé » si données partielles).
   - 3 badges éligibilité (BOAD-vert, SUNREF, Ecobank Green Lending) avec leur statut + raison principale.
   - 3-5 recommandations avec impact estimé `+N points` et mention « estimation ».
   - Historique : 1 point « Premier calcul » (puis plusieurs après recalculs successifs).
5. Cliquer « Mettre à jour mes données financières » → bottom sheet 4 étapes → modifier le CA → soumettre → la gauge **anime** vers le nouveau score, toast « +X points ».
6. Cliquer un badge non éligible → modal détail avec critères exhaustifs.
7. Cliquer une recommandation → bascule vers `/plan-action#step-{id}`.

## Tests automatisés

```bash
# Backend
cd backend && source .venv/bin/activate
pytest tests/credit/ -v

# Frontend unit
cd frontend && pnpm vitest run app/composables/__tests__/useCredit*.test.ts \
                                app/stores/__tests__/creditScore.test.ts \
                                app/lib/__tests__/classifyCreditScore.test.ts

# Frontend E2E (Playwright)
cd frontend && pnpm playwright test tests/e2e/credit-score-*.spec.ts
```

## Fixture de test

Pour avoir un score de test rapide :

```bash
cd backend && source .venv/bin/activate
python -c "
from app.db import SessionLocal
from app.credit.service import submit_credit_data, recompute_score
from app.credit.schemas import CreditDataKind
import uuid

db = SessionLocal()
account_id = uuid.UUID('00000000-0000-0000-0000-000000000001')   # mettre l'UUID du tenant de dev
entreprise_id = uuid.UUID('00000000-0000-0000-0000-000000000002')

submit_credit_data(db, account_id=account_id, entreprise_id=entreprise_id, user_id=None,
                   kind=CreditDataKind.DECLARATIF,
                   payload={
                       'chiffre_affaires': {'amount': '12500000', 'currency': 'XOF'},
                       'ebe': {'amount': '850000', 'currency': 'XOF'},
                       'dette': {'amount': '3200000', 'currency': 'XOF'},
                       'fonds_propres': {'amount': '5400000', 'currency': 'XOF'},
                   },
                   valid_until=None)
result = recompute_score(db, account_id=account_id, entreprise_id=entreprise_id, user_id=None)
print(result)
"
```

## Vérifier un endpoint backend manuellement

```bash
TOKEN="<votre JWT PME>"
BASE="http://localhost:8010"

# Score courant (avec subscores extension F48)
curl -H "Authorization: Bearer $TOKEN" "$BASE/me/credit-score" | jq

# Historique
curl -H "Authorization: Bearer $TOKEN" "$BASE/me/credit-score/history?limit=6" | jq

# Éligibilité
curl -H "Authorization: Bearer $TOKEN" "$BASE/me/credit-score/eligibility" | jq

# Recommandations
curl -H "Authorization: Bearer $TOKEN" "$BASE/me/credit-score/recommendations?limit=5" | jq
```

## Critères d'acceptation à la livraison

Cf. `spec.md` Success Criteria SC-001 à SC-010. En particulier :

- LCP `/credit-score` < 1.5 s p95 (Lighthouse mobile 4G simulé).
- Animation gauge fluide 60 fps (DevTools Performance).
- Aucune devise sans `currency` n'est acceptée par le bottom sheet.
- Edge case « recalcul échoué » : la gauge ne reste jamais dans un état intermédiaire.
- E2E daltonien : la classification reste identifiable par texte seul.
