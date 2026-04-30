# Quickstart — F30 Attestation Vérifiable

## 1. Pré-requis

- Postgres en route (docker compose up -d).
- Backend `.venv` activé : `source backend/.venv/bin/activate`.
- Migrations à jour : `cd backend && alembic upgrade head`.

## 2. Générer la paire de clés Ed25519

```bash
cd backend
python -m app.scripts.generate_attestation_keys
```

Le script affiche `ATTESTATION_PRIVATE_KEY_HEX=...` ; le copier dans `backend/.env`.
La clé publique correspondante (et son fingerprint sha256) est exposée par `/verify/_pubkey`.

> NE PAS COMMITTER la clé privée. Elle reste dans `.env` (gitignored).

## 3. Tests

```bash
cd backend
pytest tests/attestations -q --cov=app/attestations --cov-report=term-missing
```

Couverture cible : ≥ 80 % sur `app/attestations/crypto.py` et `app/attestations/service.py`.

## 4. Smoke test manuel

```bash
uvicorn app.main:app --reload

TOKEN=...

curl -X POST http://localhost:8000/me/attestations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scores_to_include":["solvability"], "valid_for_months":6}'

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me/attestations

curl http://localhost:8000/verify/<public_id>
curl http://localhost:8000/verify/<public_id>/json
curl http://localhost:8000/verify/_pubkey

curl -X POST http://localhost:8000/me/attestations/<id>/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Erreur de saisie"}'
```

## 5. Vérification externe (script tiers)

```python
import json, hashlib, requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

base = "http://localhost:8000"
public_id = "<uuid>"

doc = requests.get(f"{base}/verify/{public_id}/json").json()
pub = bytes.fromhex(requests.get(f"{base}/verify/_pubkey").json()["pubkey_hex"])

canonical = {
    "entreprise_name": doc["entreprise_name"],
    "generated_at": doc["generated_at"],
    "public_id": doc["public_id"],
    "referentiels_versions": doc["referentiels_versions"],
    "schema_version": "v1",
    "scores": doc["scores"],
    "valid_until": doc["valid_until"],
}
payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

assert hashlib.sha256(payload).hexdigest() == doc["hash_document"], "hash mismatch"

Ed25519PublicKey.from_public_bytes(pub).verify(bytes.fromhex(doc["signature_ed25519"]), payload)
print("Signature OK")
```

## 6. Job d'expiration

```bash
python -m app.attestations.jobs expire
```
