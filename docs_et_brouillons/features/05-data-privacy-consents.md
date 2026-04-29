# F05 — Conformité Données Personnelles, Consentements & Devises

**Phase** : 0 — Fondations transversales
**Modules brainstorm** : 0.3 (Conformité Données Personnelles), 0.6 (Devises et Taux de Change)
**Dépendances** : F02, F04
**Estimation** : 1.5–2 jours

## Contexte et objectif

Deux blocs distincts mais qui relèvent tous deux de la conformité légale et financière :

1. **Conformité données personnelles** (RGPD européen + loi ivoirienne 2013-450 + règlement UEMOA 20/2010) : page "Mes données" (voir, exporter, supprimer), consentements granulaires par usage, politique de confidentialité publiée. Chiffrement TLS 1.3 in-transit + at-rest natif Postgres.
2. **Devises et taux de change** : type `Money = {amount, currency}` (déjà défini en F01), peg fixe FCFA-EUR (655,957), API gratuite pour USD et autres, snapshot quotidien.

Sans ces fondations, on ne peut ni accepter une PME légalement, ni afficher un montant correct, ni passer une revue compliance.

## User Stories

### US1 — Page "Mes données" pour la PME (P1)
**En tant que** PME,
**je veux** une page dédiée où je peux :
- voir un résumé de **toutes** mes données stockées (entreprise, projets, candidatures, scores, attestations, documents, conversations, audit log),
- les exporter en JSON,
- demander la suppression complète de mon compte (avec délai de grâce de 30 jours).

**afin de** exercer mes droits d'accès, portabilité et effacement (RGPD art. 15, 20, 17 ; UEMOA art. équivalents).

**Test indépendant** : un utilisateur PME visite `/me/donnees`, voit le résumé, télécharge un export JSON valide qui contient toutes ses entités (anonymisation des FK vers d'autres comptes), et peut déclencher une demande de suppression (job différé).

### US2 — Consentements granulaires par usage (P1)
**En tant que** PME,
**je veux** donner ou retirer mon consentement séparément pour :
- analyse des flux Mobile Money (Module 5.1),
- traitement de photos de mon exploitation (Module 5.1),
- génération automatique d'attestation publique (Module 5.3),
- stockage d'historique de conversation au-delà de 90 jours.

**afin de** contrôler finement ce qui est fait avec mes données.

**Scénarios** :
1. Première inscription → seuls les consentements "essentiels" (contractuels) sont actifs ; les autres sont à activer au cas par cas dans `/me/consentements`.
2. Une feature qui requiert un consentement non donné (ex : F29 Mobile Money) bloque l'action et affiche un toast "Consentement Mobile Money requis — activer ici".
3. Retrait d'un consentement → les traitements en cours s'arrêtent, les données déjà collectées sont marquées "à supprimer" et purgées dans les 30 jours.

### US3 — Politique de confidentialité publiée (P1)
**En tant que** PME ou auditeur,
**je veux** une page publique `/politique-confidentialite` (accessible sans login) qui détaille :
- finalités de traitement,
- bases légales,
- catégories de données,
- destinataires (équipe ESG Mefali, hébergeur, intermédiaires uniquement via dossiers transmis par la PME),
- durées de conservation,
- droits de la personne concernée,
- email de contact (`privacy@esg-mefali.com`),
- coordonnées du DPO (post-MVP, mais l'email contact suffit en MVP).

**afin de** respecter l'obligation d'information.

### US4 — Type Money utilisable de bout en bout (P1)
**En tant que** dev backend & frontend,
**je veux** un type `Money` (Pydantic + composable Vue) avec :
- `{amount: Decimal, currency: 'XOF'|'EUR'|'USD'|'GHS'|'NGN'|...}`,
- helper `convert(money, target_currency)` côté backend,
- composant `<MoneyDisplay :money :as-of?>` côté frontend qui affiche montant + symbole.

**afin de** ne jamais stocker ni afficher un montant sans devise.

### US5 — Taux de change snapshot quotidien (P1)
**En tant que** dev backend,
**je veux** :
- peg fixe FCFA-EUR codé en constante (`655.957`, jamais modifié sans intervention humaine — mais la valeur est sourcée Module 0.1),
- snapshot quotidien des taux USD, GBP, NGN, GHS, MAD, etc. via `exchangerate-api.com` (tier gratuit) stocké en table `fx_rate (currency_from, currency_to, rate, captured_at)`,
- en cas d'échec API, on continue avec la dernière valeur connue + log d'incident.

**afin de** afficher des montants équivalents PME (FCFA) ↔ fonds (EUR/USD) sans dépendance hard à un service externe.

### US6 — Affichage parallèle PME / fonds (P2)
**En tant que** PME consultant une offre,
**je veux** voir le montant en FCFA (ma devise) ET en EUR ou USD (devise du fonds),
**afin de** comprendre clairement le pouvoir d'achat réel.

Le composant `<MoneyDisplay>` accepte une option `:show-conversion="'XOF'"` pour rendre les deux valeurs.

### US7 — Audit log des consentements et des suppressions (P2)
**En tant que** compliance,
**je veux** que chaque modification de consentement et chaque demande de suppression soient journalisées dans `audit_log` (F04) avec `source_of_change='manual'` et un champ `consent_kind`,
**afin de** prouver le consentement à un instant T et tracer le RTBF (right to be forgotten).

## Exigences fonctionnelles

- **FR-001** : Endpoint `GET /me/donnees/summary` → liste agrégée par type d'entité (nombre, dernière modif).
- **FR-002** : Endpoint `GET /me/donnees/export?format=json` → ZIP JSON contenant toutes les données du compte.
- **FR-003** : Endpoint `POST /me/donnees/delete` → demande de suppression différée (statut `pending_deletion`, deletable à `now() + 30 days`). L'utilisateur peut annuler dans la fenêtre.
- **FR-004** : Job batch `purge_pending_deletions` (cron quotidien — réutilise le mécanisme de F31) qui supprime les comptes flaggés.
- **FR-005** : Table `consent` : `id, account_id, consent_kind ENUM('mobile_money','exploitation_photos','public_attestation','long_history','marketing','...'), given BOOL, given_at, withdrawn_at NULL, source_of_change`.
- **FR-006** : Endpoint `GET /me/consentements` + `POST /me/consentements/{kind}` (toggle) + UI `/me/consentements`.
- **FR-007** : Décorateur backend `@requires_consent(kind)` qui bloque un endpoint avec 403 + body `{error:'consent_required', kind:'mobile_money'}` si consentement absent.
- **FR-008** : Page `/politique-confidentialite` (Markdown rendu via toast-ui ou statique). Versionnée — chaque mise à jour majeure invalide les consentements requérant ré-acceptation.
- **FR-009** : Type Pydantic `Money` (avec `amount: Decimal`, `currency: Currency` enum), validators (currency parmi liste fermée, amount ≥ 0 sauf cas spéciaux), serializer JSON `{amount: "1234.56", currency: "XOF"}`.
- **FR-010** : Service backend `FxService` :
  - `get_rate(from, to, at?) -> Decimal`,
  - `convert(money, to, at?) -> Money`,
  - peg FCFA-EUR codé en constante avec source liée (Module 0.1),
  - cache des taux en table `fx_rate`.
- **FR-011** : Job cron quotidien `refresh_fx_rates` qui appelle exchangerate-api.com et met à jour `fx_rate`. Idempotent.
- **FR-012** : Composable Nuxt `useMoney()` + composant `<MoneyDisplay>` avec props `:money`, `:show-conversion?`, `:as-of?`.
- **FR-013** : Variables d'env `EXCHANGERATE_API_KEY` (gratuite) et `FX_DEFAULT_DISPLAY_CURRENCY=XOF`.

## Exigences non-fonctionnelles

- **NFR-001** : TLS 1.3 obligatoire en prod (configuration reverse proxy / Nuxt server). HSTS activé.
- **NFR-002** : Chiffrement at-rest : utiliser le chiffrement natif du fournisseur Postgres managé (Scaleway / OVH / Africa Data Centres). Documenté dans le README ops.
- **NFR-003** : Le ZIP d'export ne contient pas le password_hash, jamais. Les FK vers `Source` / `Referentiel` (catalogue partagé) sont incluses comme références (id + url) mais pas dupliquées.
- **NFR-004** : Suppression réelle = `DELETE` SQL en cascade contrôlée + suppression des fichiers physiques + révocation des attestations actives + invalidation des refresh tokens. Auditable par script de vérification post-purge.
- **NFR-005** : Coordonnées `privacy@esg-mefali.com` doivent réellement aboutir (alias mail à configurer côté ops, en dehors du scope code).

## Entités clés

- **Consent** (FR-005).
- **FxRate** (FR-010).
- **Money** (Pydantic — pas une table mais un type partout).
- **DeletionRequest** (peut être un champ `account.deletion_requested_at` plutôt qu'une table — choix d'implémentation).

## Success Criteria

- **SC-001** : Un utilisateur PME exporte ses données et obtient un JSON valide contenant toutes ses entités en < 30 secondes.
- **SC-002** : Demande de suppression → 30 jours plus tard, 0 ligne reste dans la base avec `account_id = X`. Audité par script.
- **SC-003** : Toggle consentement Mobile Money OFF → l'endpoint F29 retourne 403 avec body structuré, et le frontend affiche l'invitation à activer.
- **SC-004** : `convert(Money(1000, XOF), EUR)` donne ~1.524 EUR (avec peg fixe). `convert(Money(1000, XOF), USD)` donne une valeur cohérente avec exchangerate-api.com du jour.
- **SC-005** : Page politique de confidentialité accessible sans login, listée dans `robots.txt` indexable.

## Hors-scope MVP (post-MVP)

- DPO formalisé (nomination, registre des traitements complet).
- Purge automatique granulaire fine (par catégorie de données, par âge).
- Intégration des Standard Contractual Clauses pour transfert hors UE.
- Bandeau cookies (la plateforme ne tracke pas en MVP — pas de cookies tiers).
- API publique d'export pour intégration tiers.
- Multi-currency display avancé (devise préférée par utilisateur enregistrée).

## Risques et points de vigilance

- **Suppression réelle vs masquage** : choix tranché ici → suppression réelle après 30 jours. Nécessite que TOUTES les FK soient `ON DELETE CASCADE` ou gérées par script. À auditer feature par feature.
- **Audit log et RTBF** : conflit potentiel — l'audit log conserve `user_id` même après suppression. Solution : remplacer `user_id` par un identifiant pseudonymisé au moment de la purge (`anonymized_user_<hash>`).
- **Peg FCFA-EUR** : si la BCEAO/UEMOA modifie le peg (très rare mais possible), la constante doit pouvoir être versionnée comme un référentiel — anticiper en stockant aussi le peg dans `fx_rate` avec `valid_from/valid_to`.
- **API externe** (exchangerate-api.com) : tier gratuit limité. Prévoir fallback gracieux et alerte admin si N jours sans refresh.
- **Page politique de confidentialité** : doit être validée par un juriste **avant** mise en prod. Le contenu en MVP peut être un draft mais le mécanisme d'affichage est livré.
