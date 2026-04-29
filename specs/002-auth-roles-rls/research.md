# Research — F02 Authentification & Rôles PME/Admin (RLS)

**Date**: 2026-04-29
**Feature**: 002-auth-roles-rls

Toutes les NEEDS CLARIFICATION ont été résolues lors de la phase /speckit-clarify (cf. spec.md § Clarifications). Ce document consolide les décisions techniques de support.

## D-001 — Algorithme de hachage de mot de passe

**Décision** : `bcrypt` via `passlib[bcrypt]`, cost factor 12.

**Rationale** : Adaptatif, éprouvé, supporté nativement par passlib qui prend déjà en charge la rotation transparente de cost. Cost 12 ≈ 250 ms/hash sur matériel cible — acceptable pour un endpoint de login non chaud, et suffisamment lent pour ralentir une attaque par force brute.

**Alternatives considérées** :
- `argon2id` (gagnant PHC) : préférable à long terme mais ajoute la dépendance C `argon2-cffi` ; bcrypt reste excellent et plus simple en MVP.
- `scrypt` : moins répandu, moins de retours d'expérience FastAPI.

## D-002 — Format et signature JWT

**Décision** : JWT `HS256` (secret partagé `JWT_SECRET`), claims `{sub: user_id, account_id, role, iat, exp, jti}`. TTL access token 24 h. Émission via `python-jose`.

**Rationale** : MVP mono-service, pas de besoin asymétrique. HS256 est plus simple à opérer ; rotation via une seconde clé `JWT_SECRET_PREVIOUS` (post-MVP) déjà anticipée dans le brouillon F02. `jti` ajouté pour révocation côté serveur si besoin futur.

**Alternatives considérées** :
- `RS256` (clé asymétrique) : utile si plusieurs services consomment le JWT. Surdimensionné pour MVP.
- Sessions serveur opaques : exige stockage backend pour chaque requête, complique le scaling.

## D-003 — Transport du JWT côté navigateur

**Décision** : Cookie `httpOnly` + `Secure` + `SameSite=Strict`, nom `mefali_at`. Le frontend ne lit jamais le jeton ; un second cookie `mefali_csrf` (lisible) contient un jeton CSRF anti-double-submit, exigé en en-tête `X-CSRF-Token` sur toute opération non GET.

**Rationale** : Élimine la classe d'attaques XSS-vol-de-token. SameSite=Strict bloque la majorité des CSRF inter-sites. Le double-submit complète la défense pour les sous-domaines de confiance. Aligné avec le choix de clarification Q1.

**Alternatives considérées** :
- `localStorage` + `Authorization: Bearer` : standard mais vulnérable à XSS persistant.
- Cookie `SameSite=Lax` : compromis moyen, rejeté pour rester strict en MVP fermé.

## D-004 — Refresh token : génération, stockage, rotation, détection de vol

**Décision** :
- Génération : 32 octets aléatoires URL-safe (`secrets.token_urlsafe(32)`).
- Stockage : seul le hash SHA-256 du token est stocké en base (`refresh_tokens.token_hash`). Le client conserve le token clair dans un cookie httpOnly distinct (`mefali_rt`).
- TTL : 30 jours, glissants à chaque rotation (Q2 clarification).
- Rotation : à chaque `/auth/refresh`, l'ancien token est marqué `used_at = now()` et un nouveau est créé avec `parent_id` pointant vers l'ancien.
- Détection de vol : si un token déjà `used_at IS NOT NULL` est présenté → toute la chaîne (récursivement par `parent_id`) est révoquée et l'utilisateur est forcé à se reconnecter. Événement audit `refresh_chain_revoked`.

**Rationale** : Pattern standard OAuth refresh token rotation, aligné OWASP.

**Alternatives considérées** :
- Refresh token sans rotation : vulnérable au vol persistant.
- Rotation sans détection de chaîne : ne protège pas contre le vol simultané.

## D-005 — Politique de Row-Level Security PostgreSQL

**Décision** :
- Deux rôles SQL : `app_user` (RLS appliquée) et `migrator` (BYPASS RLS via `ALTER ROLE migrator BYPASSRLS`).
- L'application se connecte exclusivement avec `app_user`. Alembic se connecte avec `migrator`.
- Sur chaque table métier portant `account_id NOT NULL` :
  ```sql
  ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
  ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation ON <t>
    USING (
      current_setting('app.is_admin', true)::bool IS TRUE
      OR account_id = current_setting('app.current_account_id', true)::uuid
    );
  ```
- Le middleware FastAPI exécute, en début de chaque transaction authentifiée :
  ```sql
  SET LOCAL app.current_account_id = '<uuid>';
  -- et pour un Admin :
  SET LOCAL app.is_admin = 'true';
  ```
- Si aucun setting n'est positionné, la politique renvoie 0 ligne (le second `current_setting('...', true)` retourne `NULL`, le test booléen échoue, et l'égalité UUID échoue). Comportement validé par `tests/security/test_rls_isolation.py::test_no_context_returns_zero_rows`.

**Rationale** : `FORCE` empêche le propriétaire de table de bypasser RLS par accident. Le second argument `true` à `current_setting` rend l'absence de setting non fatale (retourne NULL au lieu d'erreur). Pattern recommandé du brouillon F02.

**Alternatives considérées** :
- Filtrage applicatif uniquement : rejeté — un endpoint compromis ou un bug de WHERE clause pourrait fuiter. RLS est défense en profondeur.
- Un rôle Postgres par tenant : non scalable pour des centaines de PME.

## D-006 — Politique de mot de passe et validation

**Décision** : Validation Pydantic v2 custom :
- Longueur ≥ 12.
- Au moins 1 majuscule, 1 minuscule, 1 chiffre.
- Pas de blocklist de mots communs en MVP (NFR-001).

**Rationale** : Conforme NFR-001 du spec. Implémentation triviale via regex + checks discrets.

## D-007 — Rate limiting

**Décision** : `slowapi` (équivalent FastAPI de Flask-Limiter), backend mémoire en MVP (à migrer vers Redis post-MVP) :
- `/auth/login` : 5/min/IP.
- `/auth/forgot-password` : 5/min/IP.
- `/auth/register` : 10/heure/IP.
- `/auth/refresh` : 30/min/IP (légitime sur SPA actives).
Réponse 429 avec corps générique. Aucun message ne doit suggérer l'existence d'un compte particulier.

**Rationale** : Aligné Q3 clarification. Mémoire en MVP suffit pour 1 instance ; production multi-instance exigera un store partagé.

## D-008 — Réinitialisation de mot de passe

**Décision** :
- `/auth/forgot-password` accepte un email. Indépendamment de l'existence du compte, retourne 202 Accepted avec un corps neutre.
- Si le compte existe : génère un token (32 octets URL-safe), stocke son hash SHA-256 dans `password_reset_tokens` avec `expires_at = now() + 30 minutes`, envoie un email contenant le token clair dans une URL `https://app.mefali/reset-password?token=...`.
- `/auth/reset-password` accepte `{token, new_password}`. Vérifie : token connu (par hash), `expires_at > now()`, `consumed_at IS NULL`. Si OK : met à jour `account_users.password_hash`, marque `consumed_at = now()`, révoque tous les refresh tokens actifs de l'utilisateur (force re-login partout), audit log.
- Service email : abstraction `EmailSender` avec implémentation `ConsoleEmailSender` en dev/test, `SMTPEmailSender` en prod. Détails de configuration SMTP délégués à l'opérations / variables d'env.

**Rationale** : Aligné Q4 (TTL 30 min, usage unique). Pas de fuite d'existence de compte.

## D-009 — Audit log

**Décision** : Réutilise la table `audit_log_entries` créée en F01. Champs minimaux loggés :
- `actor_user_id` (NULL si anonyme/inconnu)
- `actor_account_id` (NULL si admin ou anonyme)
- `event_type` ∈ {`auth.register`, `auth.login.success`, `auth.login.failure`, `auth.logout`, `auth.refresh.success`, `auth.refresh.reuse_detected`, `auth.password_reset.requested`, `auth.password_reset.consumed`, `admin.created`}
- `source_of_change` : `manual` pour utilisateurs, `admin` pour seed admin.
- `payload_json` : métadonnées non sensibles (IP, user-agent tronqué). JAMAIS les jetons/mots de passe.

**Rationale** : Constitution P3 + traçabilité requise pour conformité RGPD/UEMOA.

## D-010 — Frontend : middleware d'auth Nuxt 4

**Décision** :
- `auth.global.ts` : sur chaque navigation, si pas d'état utilisateur côté client, appelle `/me` (via cookie automatique). Si 401 → redirect `/login?next=<path>`. Sinon, hydrate le store Pinia.
- `admin.ts` (middleware nommé, appliqué via `definePageMeta({ middleware: ['admin'] })` sur les pages admin) : vérifie `auth.user.role === 'admin'`, sinon 404 (cohérent avec FR-015).

**Rationale** : Cookie httpOnly = pas de lecture JS du JWT, donc l'autorité de vérité côté front est `/me`. Middleware global garantit qu'aucune page ne s'affiche sans auth valide.

## D-011 — Tests d'isolation RLS

**Décision** : Suite dédiée `tests/security/test_rls_isolation.py` avec ≥ 5 scénarios indépendants :
1. SELECT par id de la PME B depuis contexte A → 0 ligne.
2. LIST de toutes les ressources depuis contexte A → uniquement A.
3. UPDATE par id de la PME B depuis contexte A → 0 ligne affectée.
4. DELETE par id de la PME B depuis contexte A → 0 ligne affectée.
5. Requête sans aucun `SET LOCAL` → 0 ligne (politique stricte).
6. (bonus) INSERT avec `account_id` mismatch depuis contexte A → erreur RLS / refusée.
7. (bonus) Admin avec `app.is_admin=true` voit toutes les PME.

**Rationale** : SC-007 exige ≥ 5 scénarios. Garantit qu'aucune feature future ne casse silencieusement l'isolation.

## D-012 — Seed admin

**Décision** : Script `python -m app.scripts.seed_admin --email <e> --password <p>` :
- Vérifie que `--password` respecte la politique.
- Crée un `AccountUser(role='admin', account_id=NULL)`.
- Audit log `admin.created` avec `source_of_change='admin'`.
- Idempotent : si l'email existe déjà avec rôle admin, refuse poliment ; sinon refuse pour éviter promotion accidentelle.

**Rationale** : SC-004. Pas d'inscription publique d'admin (FR-012).
