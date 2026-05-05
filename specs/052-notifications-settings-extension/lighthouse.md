# Lighthouse — F52 / `/notifications`

**Cible NFR-001** : LCP ≤ 1 000 ms sur `/notifications` en environnement
chargé (50 notifications, filtres actifs, drawer fermé).

## Méthodologie

Run en local sur Chrome stable, throttling **Mobile / Slow 4G simulé** par
défaut Lighthouse, mode `desktop` également exécuté.

```bash
# 1) Démarrer la stack
make db-up
make backend          # http://localhost:8010
make frontend         # http://localhost:3001

# 2) Seeder un compte avec ≥ 50 notifications
cd backend && source .venv/bin/activate
python -m app.notifications.cli seed --user <user_id> --n 50

# 3) Lancer Lighthouse (CLI)
npx -y lighthouse http://localhost:3001/notifications \
    --preset=desktop \
    --quiet --chrome-flags="--headless=new" \
    --output=html --output-path=specs/052-notifications-settings-extension/lighthouse-desktop.html

npx -y lighthouse http://localhost:3001/notifications \
    --form-factor=mobile \
    --quiet --chrome-flags="--headless=new" \
    --output=html --output-path=specs/052-notifications-settings-extension/lighthouse-mobile.html
```

> Le compte doit être pré-authentifié (cookie copié dans l'URL via une session
> existante) ou utiliser le flag `--extra-headers` pour passer le cookie. À
> défaut, Lighthouse mesure le redirect `/login`, ce qui n'est pas pertinent.

## Résultats attendus (gate)

| Métrique | Cible | Notes |
|---|---|---|
| LCP | ≤ 1 000 ms (NFR-001) | Liste paginée 20 lignes — keyset cursor côté store. |
| FCP | ≤ 800 ms | SSR Nuxt + cache HTTP `Cache-Control: private, max-age=15`. |
| TBT | ≤ 200 ms | Aucun gros bundle JS hors chunk shell. |
| CLS | ≤ 0.05 | Skeleton fixe 56 px par ligne. |
| Score Performance (desktop) | ≥ 95 | |
| Score Performance (mobile) | ≥ 85 | |

## Observations (run du jour J)

> À remplir lors du run réel — utiliser les chiffres extraits de Lighthouse
> (`audits.largest-contentful-paint.numericValue` etc.).

| Run | Date | LCP (ms) | FCP (ms) | TBT (ms) | CLS | Score |
|---|---|---|---|---|---|---|
| desktop | _à compléter_ | _–_ | _–_ | _–_ | _–_ | _–_ |
| mobile  | _à compléter_ | _–_ | _–_ | _–_ | _–_ | _–_ |

## Pistes d'optimisation déjà appliquées

- Listing keyset (cursor-based) — pas de `OFFSET`.
- Drawer ouvert en `lazy-hydrate` (pas dans la première peinture).
- Filtres réactifs en mémoire (sans round-trip serveur tant que les paramètres
  ne mutent pas).
- SSE n'incrémente que `unread_count` côté store — la liste n'est pas
  re-rendue intégralement.

## Pistes restantes (post-MVP si besoin)

- Image avatars en `loading="lazy"`.
- Préfetch du drawer (`<link rel="prefetch">`) en hover sur une ligne.
- Migrer le rendu du badge cloche en CSS-only quand le compteur est nul.
