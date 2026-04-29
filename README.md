# ESG Mefali v2

Plateforme ESG &amp; financement pour PME ouest-africaines.

> **Statut** : F01 — Foundations Stack Init (en cours).
> Hébergement production : **Europe ou Afrique de l'Ouest uniquement** (RGPD,
> UEMOA 20/2010, loi ivoirienne 2013-450).

## Pré-requis

- Python **3.12+** (testé jusqu'à 3.14)
- Node **20+**
- pnpm (`npm i -g pnpm`)
- Docker + Docker Compose

## Setup en 5 commandes

```bash
cp .env.example .env                # remplir DB_PASSWORD au minimum
docker compose up -d postgres       # démarre Postgres + pgvector
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
alembic upgrade head                # crée le schéma initial (18 tables)
uvicorn app.main:app --reload --port 8000
```

Puis dans un autre terminal :

```bash
cd frontend && pnpm install && pnpm dev
```

Ouvrez http://localhost:3000 — la page affiche le statut du backend.

## Structure du repo

```
.
├── docker-compose.yml      # SEUL service docker : postgres (pgvector/pgvector:pg16)
├── .env.example            # variables documentées (versionnées)
├── Makefile                # raccourcis dev (make help)
├── backend/                # FastAPI (Python, .venv local)
│   ├── app/                # config, db, llm_client, embeddings_client, main
│   ├── alembic/            # migrations (0001 = schéma initial)
│   └── tests/              # pytest (>80% couverture)
├── frontend/               # Nuxt 4 + TailwindCSS v4 + Pinia
│   ├── app/
│   │   ├── pages/          # routes Vue
│   │   ├── composables/    # useHealth(), …
│   │   └── assets/css/     # main.css (@import tailwindcss)
│   └── tests/              # vitest
└── specs/                  # specs Spec Kit (par feature)
```

## Tests

```bash
# Backend (pytest + couverture)
cd backend && source .venv/bin/activate && pytest --cov

# Frontend (vitest)
cd frontend && pnpm test
```

Couverture cible : **≥ 80 %**.

## Premier démarrage — checklist (chronométrer < 10 min)

- [ ] `cp .env.example .env` puis renseigner `DB_PASSWORD`, `LLM_*`, `JWT_SECRET`, `VOYAGE_API_KEY`, `REPLICATE_API_TOKEN`
- [ ] `docker compose up -d postgres` — `docker compose ps` confirme `healthy`
- [ ] `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- [ ] `alembic upgrade head` — chronométrer (< 30 s attendu, SC-002)
- [ ] `uvicorn app.main:app --reload --port 8000`
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","db":"ok"}`
- [ ] `cd frontend && pnpm install && pnpm dev`
- [ ] http://localhost:3000 → "Backend OK" affiché en < 3 s (SC-004)

## Reset complet de l'environnement

```bash
docker compose down -v          # supprime le volume (données effacées)
docker compose up -d postgres
cd backend && source .venv/bin/activate && alembic upgrade head
```

## Dépannage

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| `Port 5432 already in use` | Postgres système ou autre container | Définir `POSTGRES_PORT=5433` dans `.env`, redémarrer compose |
| `/health` → 503 | Postgres down ou mauvais mot de passe | `docker compose ps`, vérifier `DB_PASSWORD` dans `.env` |
| Frontend "Backend indisponible" | uvicorn pas démarré ou CORS | Vérifier uvicorn sur :8000 ; `NUXT_PUBLIC_API_BASE` correct |
| `alembic` ne trouve pas la base | `.env` non lu | `cd backend` puis `alembic upgrade head` (lit `../.env`) |
| `psycopg-binary` ne s'installe pas | Python &lt; 3.10 ou &gt; 3.14 | Utiliser une version supportée |

## Liens

- Quickstart détaillé : [`specs/001-foundations-stack-init/quickstart.md`](specs/001-foundations-stack-init/quickstart.md)
- Spec F01 : [`specs/001-foundations-stack-init/spec.md`](specs/001-foundations-stack-init/spec.md)
- Constitution : [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
