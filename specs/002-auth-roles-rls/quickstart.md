# Quickstart — F02 Authentification & RLS

**Pour développeurs** — comment tester localement la feature après implémentation.

## Pré-requis

- F01 livrée (backend FastAPI, frontend Nuxt 4, Postgres dockerisé).
- `.env` backend complété avec :
  ```
  DATABASE_URL=postgresql+asyncpg://app_user:<pwd>@localhost:5432/mefali
  MIGRATOR_DATABASE_URL=postgresql+asyncpg://migrator:<pwd>@localhost:5432/mefali
  JWT_SECRET=<32+ chars random>
  CSRF_SECRET=<32+ chars random>
  COOKIE_DOMAIN=localhost
  COOKIE_SECURE=false   # dev only
  EMAIL_BACKEND=console # dev
  ```

## 1. Migration Alembic

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=$MIGRATOR_DATABASE_URL alembic upgrade head
```

Crée les tables `refresh_tokens`, `password_reset_tokens`, modifie `account_users` (ajout `role`, `last_login_at`), crée les rôles `app_user` et `migrator`, et active RLS sur toutes les tables `account_id NOT NULL`.

## 2. Création d'un Admin

```bash
python -m app.scripts.seed_admin --email admin@mefali.io --password 'Adm1nVeryStrong!'
```

## 3. Démarrer le backend

```bash
uvicorn app.main:app --reload --port 8000
```

## 4. Démarrer le frontend

```bash
cd ../frontend
pnpm dev
```

## 5. Scénarios manuels

### Inscription PME
1. Aller sur `http://localhost:3000/register`.
2. Saisir email + mot de passe (≥ 12 chars, maj/min/chiffre).
3. Soumettre → redirection vers `/` connecté en tant que PME.

### Connexion
1. `http://localhost:3000/login`.
2. Saisir identifiants → redirigé vers la page d'origine ou `/`.

### Connexion Admin
1. `http://localhost:3000/login` avec les identifiants admin créés en étape 2.
2. Accéder à `/admin/...` → autorisé.

### Vérification d'isolation
```bash
# Côté serveur, ouvrir psql avec app_user et lancer une requête sans setting :
psql "postgresql://app_user:<pwd>@localhost:5432/mefali" -c "SELECT count(*) FROM entreprises;"
# → doit retourner 0 (RLS bloque sans contexte).
```

## 6. Tests automatisés

```bash
cd backend
pytest tests/unit -v
pytest tests/integration -v
pytest tests/security -v   # RLS isolation : ≥ 5 scénarios doivent tous passer
```

```bash
cd frontend
pnpm test                  # vitest
pnpm test:e2e              # playwright (login + admin access)
```

Cible globale : 80 % couverture, suite RLS 100 % verte.

## 7. Critères d'acceptation à valider manuellement

- [ ] SC-001 : 2 PME créées, l'une ne voit pas les ressources de l'autre.
- [ ] SC-002 : login → /me → /auth/refresh → /me avec nouveau jeton, tout passe.
- [ ] SC-003 : `grep` des routes FastAPI confirme qu'aucun endpoint métier n'expose de données sans dépendance d'auth.
- [ ] SC-004 : seed_admin réussit en une commande.
- [ ] SC-005 : login email inconnu et login mot de passe erroné renvoient strictement la même réponse.
- [ ] SC-006 : aucun mot de passe ni token complet n'apparaît dans les logs (vérifier `tail -n 1000 logs/app.log | grep -E '(password|Bearer )'`).
- [ ] SC-007 : suite `tests/security` ≥ 5 scénarios verts.
- [ ] SC-008 : flux login → refresh → /me en < 3 s.
- [ ] SC-009 : reset password en < 2 min (hors latence email).
