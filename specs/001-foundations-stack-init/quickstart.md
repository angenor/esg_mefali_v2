# Quickstart — F01 Foundations Stack Init

> Démarrer la stack ESG Mefali en local en moins de 10 minutes.

## Pré-requis

- Python 3.12+
- Node 20+
- pnpm (`npm i -g pnpm`)
- Docker + docker compose

## 1. Cloner et configurer

```bash
git clone <repo-url> esg_mefali_v2
cd esg_mefali_v2
cp .env.example .env
# Éditer .env et au minimum définir DB_PASSWORD
```

## 2. Démarrer PostgreSQL (seul service Docker)

```bash
docker compose up -d
docker compose ps   # vérifier que postgres est healthy
```

Le service expose Postgres sur `localhost:${POSTGRES_PORT:-5432}`.

## 3. Backend FastAPI dans .venv

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head           # Applique la migration initiale
uvicorn app.main:app --reload --port 8000
```

Vérification :

```bash
curl -s http://localhost:8000/health
# {"status":"ok","db":"ok"}
```

## 4. Frontend Nuxt 4

Dans un autre terminal :

```bash
cd frontend
pnpm install
pnpm dev
```

Ouvrir http://localhost:3000 — la page d'accueil affiche le statut du backend.

## 5. Tests

```bash
# Backend
cd backend && source .venv/bin/activate
pytest -q

# Frontend
cd frontend && pnpm test
```

## 6. Reset complet de l'environnement

```bash
docker compose down -v          # supprime le volume Postgres
docker compose up -d
cd backend && source .venv/bin/activate
alembic upgrade head            # ré-applique la migration sur DB vierge
```

## Vérification des Success Criteria

- **SC-001** : ces 4 étapes prennent < 10 minutes sur poste vierge.
- **SC-002** : `time alembic upgrade head` < 30 s.
- **SC-003** : `curl /health` répond 200 quand Postgres tourne, 503 sinon (`docker compose stop postgres`).
- **SC-004** : `pnpm dev` lance Nuxt sans erreur, page d'accueil affiche statut.
- **SC-005** : la séquence du § 6 reproduit l'environnement.

## Variables d'environnement (`.env`)

| Variable | Obligatoire | Description |
|----------|------------|-------------|
| DB_PASSWORD | OUI | Mot de passe utilisateur Postgres |
| POSTGRES_PORT | non (défaut 5432) | Port exposé par Docker |
| LLM_BASE_URL | OUI (sans appel en F01) | https://openrouter.ai/api/v1 |
| LLM_API_KEY | OUI (sans appel en F01) | Clé OpenRouter |
| LLM_MODEL | OUI | ex. minimax/minimax-m2.7 |
| APP_URL | OUI | URL identifiant l'app (OpenRouter HTTP-Referer) |
| JWT_SECRET | OUI (utilisé en F02) | Secret signature JWT |
| VOYAGE_API_KEY | OUI (sans appel en F01) | Clé Voyage AI |
| REPLICATE_API_TOKEN | OUI (utilisé en F22) | Token Replicate |

## Hébergement production

Production déployée **uniquement** en Europe ou Afrique de l'Ouest (RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450). Fournisseurs candidats : OVH, Scaleway, Africa Data Centres, AWS Cape Town.

## Dépannage

- **Port 5432 occupé** : définir `POSTGRES_PORT=5433` dans `.env`, redémarrer `docker compose`.
- **`alembic` ne trouve pas la base** : vérifier que `.env` est lu par `alembic/env.py` et que `DB_PASSWORD` correspond bien à celui du `docker-compose.yml`.
- **`/health` retourne 503** : `docker compose ps` pour vérifier le healthcheck Postgres.
- **Frontend affiche "backend indisponible"** : vérifier que uvicorn tourne sur 8000 et que CORS autorise localhost:3000.
