# Phase 0 — Research : F05 Data Privacy & Consents

**Date** : 2026-04-29
**Branche** : `005-data-privacy-consents`

## R1 — Ordonnanceur de jobs (purge, refresh fx, alerte)

- **Décision** : APScheduler `BackgroundScheduler` (mode async) embarqué dans le process FastAPI au démarrage, avec table `scheduled_job_run (job_name, run_date, status, message, started_at, finished_at, UNIQUE(job_name, run_date))` pour idempotence et observabilité. Wrapping de chaque job dans une fonction `run_idempotent(job_name, fn)` qui pose la ligne en `running`, exécute, met à jour en `success` ou `failed`.
- **Rationale** : pas de service externe, déploiement simple, suffisant pour 1 job/jour. Idempotence par contrainte d'unicité résiste aux redémarrages multiples.
- **Alternatives** :
  - `pg_cron` rejeté car non garanti sur Postgres managé (Scaleway, OVH AVDC).
  - Celery + Redis rejeté pour MVP (overkill pour 3 jobs, ajoute un service).
  - Cron système rejeté car couplage à l'OS et duplication CLI.

## R2 — Pseudonymisation déterministe pour RTBF

- **Décision** : `anon_<HMAC-SHA256(account_id_uuid_bytes, server_pepper).hexdigest()[:16]>`. Pepper stocké en variable d'env `PURGE_PSEUDONYM_PEPPER` (32 bytes random hex), distinct du `JWT_SECRET`. Implémentation `app/core/pseudonymize.py::pseudonymize(account_id) -> str`.
- **Rationale** : déterministe par compte (deux purges du même compte donnent le même pseudonyme), irréversible sans le pepper, longueur fixe 21 chars (`anon_` + 16 hex), compatible colonne `audit_log.user_id VARCHAR/UUID-as-text` après cast.
- **Alternatives** :
  - SHA-256 simple rejeté (vulnérable à attaque dictionnaire si pepper absent).
  - UUIDv5 rejeté (espace de noms public, non poivré).
  - Suppression pure rejetée car casse l'append-only F04.

## R3 — Extension du trigger F04 `snapshot_immutable` pour la purge

- **Décision** : modifier la fonction trigger pour autoriser l'`UPDATE` exclusivement sur la colonne `user_id` lorsque `current_setting('app.purge_context', true) = 'on'`. Le contexte est posé par le job `purge_pending_deletions` via `SET LOCAL app.purge_context = 'on'` au sein d'une seule transaction, et automatiquement réinitialisé en fin de transaction.
- **Rationale** : préserve l'append-only en règle générale tout en autorisant la pseudonymisation contrôlée requise par RGPD art. 17. Granularité au niveau colonne et au niveau session.
- **Alternatives** :
  - Table d'audit séparée pour purges rejetée (complexifie la requête historique).
  - Suppression de la ligne d'audit rejetée (perte de la preuve d'événement, viole P3).

## R4 — Source du peg FCFA-EUR

- **Décision** : créer une `Source` (table F03) au démarrage des migrations 005, type `legal_decree`, URL pointant vers le décret de fixation de la parité (BCEAO ou JO Côte d'Ivoire), statut `verified` après double-validation admin. Le peg `655.957` est inséré dans `fx_rate` avec `peg_source_id` FK NOT NULL pour cette ligne uniquement.
- **Rationale** : conformité P1 (sourçage anti-hallucination). La constante reste en code (`app/core/currencies.py::PEG_FCFA_EUR = Decimal('655.957')`) pour usage immédiat sans round-trip DB, et est validée à l'insertion par un test qui compare la constante à la ligne `fx_rate` source.
- **Alternatives** :
  - Constante seule sans entrée fx_rate rejetée (impossible à versionner en cas de modification BCEAO).
  - Lecture DB pour chaque conversion rejetée (latence > 200 ms).

## R5 — Format de l'archive d'export

- **Décision** : ZIP streamé via `zipstream-ng`, contenant à la racine :
  - `manifest.json` : `{generated_at, account_id, files: [{name, sha256, size_bytes, count}]}`
  - `entities/{entity_type}.json` (un fichier par catégorie)
  - `files/{document_id}__{filename}` (pièces jointes physiques)
  Hash SHA-256 calculé pendant streaming par fichier.
- **Rationale** : streaming respecte SC-001 (≤ 30 s) sans charger tout en RAM. Manifest permet vérification d'intégrité côté utilisateur.
- **Alternatives** :
  - JSON unique massif rejeté (chargement RAM, parsing client coûteux).
  - Tar.gz rejeté (Windows compatibility moindre).

## R6 — exchangerate-api.com — fiabilité et fallback

- **Décision** : un appel/jour à `https://v6.exchangerate-api.com/v6/{API_KEY}/latest/EUR` (devise pivot), parse le JSON, écrit une ligne `fx_rate` par couple (EUR, target) target ∈ {USD, GHS, NGN, MAD, GBP}. Sur erreur HTTP ou timeout (15 s), aucune écriture, ligne `scheduled_job_run.status='failed'`, log d'incident. Service `FxService.get_rate(from, to)` lit la dernière ligne valide. Alerte admin si `consecutive_failed_days >= 7`.
- **Rationale** : tier gratuit limité à 1500 req/mois (≥ 30 fois supérieur aux besoins). Pivot EUR évite N appels.
- **Alternatives** :
  - Open Exchange Rates rejeté (free tier exige carte de crédit).
  - ECB XML rejeté (devises africaines absentes).

## R7 — Versioning de la politique de confidentialité

- **Décision** : table `privacy_policy_version (id, version, published_at, is_major BOOL, content_md TEXT, created_by_admin_id, source_id NULL)`. Création via helper F04 `publish_new_version`. Lecture publique par `version='current'` (vue ou ORDER BY published_at DESC LIMIT 1). Table `consent_acceptance (account_id, policy_version_id, accepted_at)` PK composite. Middleware Nuxt global `policy-acceptance.global.ts` redirige vers `/me/policy-reaccept` si `latest_major_version > last_accepted_major_for(account)`.
- **Rationale** : réutilise mécanique F04 sans réinventer.
- **Alternatives** :
  - Fichier Markdown statique versionné par git rejeté car bloque la ré-acceptation conditionnelle programmable.

## R8 — RLS pour `fx_rate` et `privacy_policy_version`

- **Décision** : `fx_rate` ENABLE RLS, policy SELECT `USING (true)` pour role authenticated, INSERT/UPDATE réservé via fonction SECURITY DEFINER `admin_insert_fx_rate(...)`. `privacy_policy_version` même schéma, plus une policy SELECT publique anon role pour `/politique-confidentialite` non authentifié.
- **Rationale** : préserve P2 (pas de rôle utilisateur écrivant ces tables) tout en permettant la lecture publique.
- **Alternatives** : ne pas activer RLS rejeté (risque écriture par PME via injection).

## R9 — Décorateur `@requires_consent(kind)`

- **Décision** : décorateur FastAPI vérifiant via `Depends(get_current_account)` puis `consent_service.is_active(account_id, kind)`. Si inactif, lève `HTTPException(403, detail={'error':'consent_required','kind':kind})`. Disponible aussi comme dépendance déclarative `Depends(RequiresConsent('mobile_money'))`.
- **Rationale** : forme déclarative testable + introspection OpenAPI.
- **Alternatives** : middleware générique rejeté (perd la granularité par endpoint).

## R10 — Bottom sheets (P10)

- **Décision** : composant Vue `<BottomSheet>` réutilisable basé sur gsap `Flip`/`y` animation, instancié par `ConsentToggleSheet`, `DeletionConfirmSheet`, `PolicyReacceptSheet`. Focus trap, escape close, scroll lock body. Pas de bouton « Répondre librement » car flux non conversationnel — la convention du Module 0 ne s'applique qu'aux interactions LLM.
- **Rationale** : conforme P10 ; isolement pour testabilité E2E.
- **Alternatives** : modal centré rejeté car contraire à l'invariant Module 0.

## Résolution des `NEEDS CLARIFICATION`

Aucun marqueur `NEEDS CLARIFICATION` ne subsiste : les 5 ambiguïtés détectées par `/speckit-clarify` ont été résolues dans `spec.md`, et les 10 décisions ci-dessus couvrent les détails techniques restants.
