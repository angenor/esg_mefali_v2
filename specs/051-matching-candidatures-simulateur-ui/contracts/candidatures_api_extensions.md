# Contracts — Candidatures API extensions (F51)

Ces contrats étendent F26/F34. Tous les schémas Pydantic v2 ont `extra='forbid'`.

## 1. `GET /me/candidatures` (existant — F34, rappel)

Liste table principale. Auth : PME.

```jsonc
// 200 OK — liste de CandidatureRowOut
[
  {
    "id": "uuid",
    "offre_nom": "Ligne verte BICC 2024",
    "projet_titre": "Ferme solaire 200 kWc",
    "statut": "brouillon",
    "step_courant": 3,
    "progression_pct": 60,
    "updated_at": "ts",
    "submitted_at": null
  }
]
```

## 2. `POST /me/projets/{projet_id}/candidatures` (existant — F25, rappel)

Création candidature à partir d'une offre. Body : `{offre_id}`. 201. Pré-remplit `step_courant=1, progression_pct=20` (étape 1 atteinte par défaut puisque offre+projet sont déjà choisis).

## 3. `GET /me/candidatures/{candidature_id}` (NOUVEAU)

Détail complet incluant draft + timeline. Auth : PME.

Response :

```jsonc
{
  "id": "uuid",
  "offre": {
    "id": "uuid", "nom": "...", "intermediaire_nom": "BICC", "type": "credit",
    "montant_min": { "amount": "10000", "currency": "EUR" },
    "montant_max": { "amount": "500000", "currency": "EUR" },
    "documents_requis": [{ "key": "k_kbis", "label": "Kbis", "format": "pdf" }]
  },
  "projet": { "id": "uuid", "titre": "...", "description": "..." },
  "statut": "brouillon",
  "step_courant": 3,
  "progression_pct": 60,
  "draft_snapshot_json": { /* voir data-model.md §1 */ },
  "submitted_at": null,
  "submitted_snapshot_json": null,
  "timeline": [
    { "ts": "...", "event": "created", "by": "PME", "comment": null },
    { "ts": "...", "event": "step_changed", "field": "step_courant", "from": 1, "to": 2 }
  ],
  "documents_lies": [
    { "document_id": "uuid", "checklist_key": "k_kbis", "filename": "kbis_2026.pdf", "uploaded_at": "ts" }
  ],
  "version": 4
}
```

Erreurs : 404 si candidature inexistante OU appartenant à un autre tenant (P2).

## 4. `PATCH /me/candidatures/{candidature_id}/draft` (NOUVEAU)

Autosave d'un brouillon. Auth : PME.

Body :

```jsonc
{
  "step_courant": 3,                      // optionnel — si présent, transition d'étape (audit)
  "draft_snapshot_json": { ... },         // payload partiel, fusionné côté serveur (deep merge top-level keys step1..step5)
  "expected_version": 4                   // optimistic lock
}
```

Comportement :

- `expected_version` mismatch → 409 `version_conflict` avec body `{current_version, current_draft}`. Le client doit fusionner et retenter.
- `submitted_at IS NOT NULL` → 422 `already_submitted`.
- `step_courant` change → audit `record_audit(field='step_courant', source='manual')`. Sinon, pas d'audit (research §2).
- `progression_pct` recalculé côté serveur selon les règles `data-model.md §3`.

Response 200 :

```jsonc
{
  "id": "uuid",
  "step_courant": 3,
  "progression_pct": 60,
  "draft_snapshot_json": { /* version fusionnée */ },
  "version": 5,
  "updated_at": "ts"
}
```

## 5. `POST /me/candidatures/{candidature_id}/submit` (NOUVEAU)

Soumission avec snapshot intangible. Auth : PME.

Body :

```jsonc
{
  "confirmed": true,                       // doit être true (double confirmation côté serveur)
  "expected_version": 5,
  "user_acknowledged_intangible": true     // checkbox UI obligatoire
}
```

Comportement :

- `confirmed != true` ou `user_acknowledged_intangible != true` → 422 `confirmation_required`.
- `expected_version` mismatch → 409.
- `submitted_at IS NOT NULL` → 422 `already_submitted` (idempotence).
- Vérifie que `step_courant == 5` ET `progression_pct == 100`. Sinon 422 `incomplete_dossier` avec liste des items manquants (documents requis non joints, réponses libres non fournies).
- Construit `submitted_snapshot_json` (research §8) en lisant l'état figé.
- UPDATE atomique → `submitted_at=now(), submitted_snapshot_json=:snap, statut='soumise'`.
- Audit `record_audit(field='submitted_at', source='manual')`.

Response 200 :

```jsonc
{
  "id": "uuid",
  "statut": "soumise",
  "submitted_at": "ts",
  "snapshot_schema_version": "1",
  "version": 6
}
```

## 6. `PATCH /me/candidatures/{candidature_id}/status` (existant — F34)

Inchangé. Reste réservé aux transitions admin/PME légales (`brouillon` → `soumise` est faite par `submit`, pas par cet endpoint).

---

## 7. Liens documents wizard

Réutilise les endpoints F50 :

- `POST /me/documents/{document_id}/link-projet` avec body étendu `{ projet_id, candidature_checklist_key?: "k_kbis" }` — la `checklist_key` enrichit le lien et alimente `draft_snapshot_json.step3.documents_links`.
- `DELETE /me/documents/{document_id}/link-projet/{projet_id}` — retrait de la checklist met à jour `progression_pct`.

Pas de nouvel endpoint ; F51 consomme F50 tel quel.

---

## Erreurs communes

| Code HTTP | `code` | Cas |
|---|---|---|
| 401 | (default) | Pas de JWT |
| 403 | `no_account` | User sans account |
| 404 | `candidature_not_found` | inexistante / cross-tenant (P2) |
| 409 | `version_conflict` | optimistic lock mismatch |
| 422 | `already_submitted` | tentative mutation post-submit |
| 422 | `confirmation_required` | flags double-confirm absents |
| 422 | `incomplete_dossier` | submit avant 100 % |
