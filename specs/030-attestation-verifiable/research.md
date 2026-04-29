# Phase 0 Research — F30 Attestation Vérifiable

## Décision 1 — Bibliothèque Ed25519

**Décision** : utiliser `cryptography` (PyCA, mature, maintenu).

**Rationale** :
- API stable `Ed25519PrivateKey.from_private_bytes(seed)` / `sign(data)` / `verify(sig, data)`.
- Vérification croisée Node.js triviale via le module `crypto` natif (Ed25519 supporté depuis
  Node 12).
- Probablement déjà transitivement disponible.

**Alternatives** : `pynacl` (libsodium) — rejeté ; `cryptography` suffit largement.

## Décision 2 — Canonicalisation JSON

**Décision** : sérialisation déterministe via `json.dumps(obj, sort_keys=True, separators=(',',
':'), ensure_ascii=False)` puis encodage UTF-8.

**Rationale** :
- Reproductible côté Python et Node sans lib supplémentaire.
- Périmètre d'objets signés borné (clés ASCII, valeurs scalaires + arrays) : tri lexicographique
  simple suffit.

**Alternatives** : RFC 8785 (JCS) — rejeté pour MVP.

## Décision 3 — Génération PDF

**Décision** : `reportlab` + `qrcode[pil]`.

**Rationale** :
- `reportlab` est déjà utilisé par F24 (`app/rapports/pdf_builder.py`).
- `qrcode[pil]` rend une image PNG en mémoire, embarquable via `Image.drawInlineImage`.

**Alternatives** : `weasyprint` (HTML→PDF) — rejeté MVP (dépendances natives Pango/Cairo).

## Décision 4 — Stockage du PDF

**Décision** : `app.storage.local.LocalStorage` sous racine configurable, chemin relatif
`<yyyy>/<mm>/<public_id>.pdf`.

**Rationale** : alignement F22/F24/F26 ; path traversal déjà géré par la classe.

## Décision 5 — Page publique `/verify/{public_id}`

**Décision** : endpoint FastAPI servant un HTML rendu via `Jinja2Templates`, plus endpoint frère
`GET /verify/{public_id}/json` pour usage tiers.

**Rationale** : limiter le scope frontend ; rendu HTML minimaliste (titre, statut, dates, scores,
lien PDF) ; aucune dépendance Nuxt en MVP.

## Décision 6 — Rate limiting

**Décision** : middleware FastAPI léger basé sur compteur en mémoire keyed par IP (60
req/min/IP). Pas de Redis. Si `slowapi` est déjà installé, l'utiliser.

**Rationale** : MVP sans infra externe ; cohérent avec la directive « pas de Redis ».

## Décision 7 — Gestion de la clé privée

**Décision** : variable d'environnement `ATTESTATION_PRIVATE_KEY_HEX` (64 chars hex = 32 bytes
seed). Lecture lazy à la première génération. Si absente, l'app démarre mais lève
`KeyNotConfiguredError` (HTTP 503) sur génération.

**Procédure** : script `backend/app/scripts/generate_attestation_keys.py` produit la paire,
affiche le hex à mettre dans `.env` ; jamais committé.

## Décision 8 — Statut calculé à la lecture

**Décision** : statut `active`/`expired`/`revoked` calculé en Python à la lecture (pas de colonne
matérialisée). Comparaison `valid_until` vs `now()` UTC + lookup `revoked_at`.

**Rationale** : simplifie la migration et évite tâche cron critique. Le job `expire_attestations`
est purement informationnel pour les notifications futures (post-MVP).

## Décision 9 — Audit log

**Décision** : émettre via `record_audit` (F04) :
- génération : `attestation.generated`, `source_of_change='manual'`.
- révocation PME : `attestation.revoked`, `source_of_change='manual'`.
- révocation admin : `attestation.revoked`, `source_of_change='admin'`.

Snapshot avant/après inclus (avant = `revoked_*` à null ; après = renseignées).

## Décision 10 — Tests

**Décision** : pytest avec fixtures
- `attestation_keypair` : paire éphémère générée pour les tests, monkeypatch de la conf.
- `pme_account` / `admin_account` factories existantes.

Smoke test PDF : bytes non vides + round-trip sign/verify OK.
