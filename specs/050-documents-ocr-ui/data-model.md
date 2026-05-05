# Phase 1 — Data Model: F50 Documents upload + OCR viewer UI

**Date** : 2026-05-05
**Branch** : `050-documents-ocr-ui`

F50 ne crée **pas** de nouveau domaine documentaire ; il étend les tables existantes `document_entreprise` (F22) et `document_projet` (F12) et ajoute une table de liens M:N (Q1).

## 1. Extensions de `document_entreprise`

| Colonne | Type | Null | Défaut | Notes |
|---------|------|------|--------|-------|
| `content_sha256` | `bytea` (32 octets) | OUI | — | Empreinte SHA-256 calculée côté serveur sur le flux uploadé. Renseigné par le service d'upload (existant + extension). |
| `extraction_payload` | `jsonb` | OUI | `'{}'::jsonb` | Champs structurés (raison sociale, effectifs, CA, etc.) produits par le pipeline d'extraction. Forme : `{ "fields": [{ "key": "raison_sociale", "value": "...", "confidence": 0.92 }, ...] }`. |
| `extraction_validated_at` | `timestamptz` | OUI | NULL | Horodatage de validation utilisateur (FR-014/FR-015). |
| `extraction_validated_by` | `uuid` | OUI | NULL | FK `users.id`. |
| `extraction_validation_payload` | `jsonb` | OUI | NULL | Snapshot immuable des valeurs validées (pré-corrections appliquées). |
| `purge_scheduled_at` | `timestamptz` | OUI | NULL | Renseigné lors du soft-delete = `deleted_at + interval '30 days'` (Q2). |

**Index nouveaux** :

- `CREATE UNIQUE INDEX uq_document_entreprise_account_sha ON document_entreprise(account_id, content_sha256) WHERE deleted_at IS NULL AND content_sha256 IS NOT NULL;` — permet la requête de dédoublonnage par compte sans contrainte stricte (les doublons supprimés ou anciens sans empreinte ne bloquent pas).
- `CREATE INDEX idx_document_entreprise_purge_scheduled ON document_entreprise(purge_scheduled_at) WHERE deleted_at IS NOT NULL;` — accélère la tâche de purge.

**Statuts OCR** (déjà F22) : `pending | processing | done | error`. F50 introduit côté UI 6 libellés affichables — un mapping est documenté dans `contracts/documents_ui_contracts.md`. La transition « validé » est portée par `extraction_validated_at IS NOT NULL`.

## 2. Nouvelle table `document_link_projet` (M:N — Q1)

Permet de **partager** un `document_entreprise` avec 0..N projets sans dupliquer le fichier. Les uploads originellement attachés à un projet continuent de vivre dans `document_projet` (F12) ; F50 unifie l'affichage de la grille projet en faisant l'union des deux sources.

```sql
CREATE TABLE document_link_projet (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL,
    document_id     UUID NOT NULL REFERENCES document_entreprise(id) ON DELETE CASCADE,
    projet_id       UUID NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (document_id, projet_id)
);

ALTER TABLE document_link_projet ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON document_link_projet
    USING (account_id = current_setting('app.current_account_id')::uuid);

CREATE INDEX idx_document_link_projet_projet ON document_link_projet(projet_id, account_id);
CREATE INDEX idx_document_link_projet_document ON document_link_projet(document_id);
```

**Règles métier** :

- Insertion possible uniquement si `document_entreprise.deleted_at IS NULL` ET `account_id` cohérent entre document et projet (vérification applicative + RLS).
- Suppression d'un lien (FR-009) ne supprime jamais le document sous-jacent.
- Le hard-delete (`ON DELETE CASCADE`) supprime les liens lorsqu'un document ou un projet est définitivement purgé.

## 3. Modèle conceptuel des entités spec

| Entité spec | Table physique | Notes |
|-------------|----------------|-------|
| Document | `document_entreprise` (canonique pour F50) ou `document_projet` (legacy F12 affiché dans la grille projet via union) | Un seul fichier physique ; nom assaini, MIME, taille, identifiant interne. |
| Extraction OCR | `document_entreprise.extraction_payload` | Stockée dans la même ligne pour cohérence transactionnelle. |
| Validation | `document_entreprise.extraction_validated_at/_by/_payload` + événement d'audit | Snapshot immuable conservé dans `extraction_validation_payload`. |
| Tag | déjà F22 (table `document_entreprise_tag` existante) | Aucune extension côté F50 sauf l'événement d'audit pour modification. |
| Lien projet | `document_link_projet` | Relation M:N, RLS, audit. |
| Événement d'audit | `audit_log` (existant) | `source_of_change ∈ {manual, system}` ; `'system'` réservé à la purge automatique. |

## 4. Transitions d'état (machine)

```
                +---------+   upload OK    +-----------+
   (vide)  ──▶  | pending |  ───────────▶ | processing |
                +---------+               +-----------+
                                                │
                       extraction OK ◀──────────┼──────────▶ extraction error
                       │                                              │
                       ▼                                              ▼
                  +-------+                                       +-------+
                  | done  |                                       | error |
                  +-------+                                       +-------+
                       │
       user click « Vérifier » → fiche ouverte
                       │
                       ▼
                  validation utilisateur (FR-014)
                       │
                       ▼
       extraction_validated_at = now() (transition logique « Validé »)
                       │
       user « Re-corriger » ou « Relancer extraction »
                       │
                       ▼
       extraction_validated_at ← NULL ; processing recommencé
```

Le statut UI « Délai dépassé » est dérivé côté client lorsque le polling cumule 60 s sans changement d'état terminal — il n'est **pas** persisté en base.

## 5. RLS (rappel)

- Toutes les tables touchées (existantes ou nouvelles) imposent `account_id = current_setting('app.current_account_id')::uuid`.
- Tout accès cross-tenant retourne 404 (jamais 403) — cohérent avec la convention F22.
- Le job de purge tourne avec une connexion admin (settings `app.role = 'admin'`) qui contourne RLS uniquement pour la purge dure.

## 6. Audit (P3)

| Mutation | `entity_type` | `action` | `source_of_change` | Champs |
|----------|---------------|----------|--------------------|--------|
| Upload | `document_entreprise` | `create` | `manual` | filename, mime, size, sha256 |
| Validation extraction | `document_entreprise` | `validate_extraction` | `manual` | snapshot validation payload |
| Correction de champ post-extraction | `entreprise` ou `projet` | `update` | `manual` | per-field old/new |
| Lien projet | `document_link_projet` | `create` | `manual` | document_id, projet_id |
| Délien projet | `document_link_projet` | `delete` | `manual` | document_id, projet_id |
| Soft-delete document | `document_entreprise` | `soft_delete` | `manual` | purge_scheduled_at |
| Purge automatique 30 j | `document_entreprise` | `hard_purge` | `system` | soft_deleted_at, purged_at |
| Relance OCR | `document_entreprise` | `relaunch_ocr` | `manual` | invalidates_validation: bool |

## 7. Empreinte de contenu (Q4)

- Calcul client : `crypto.subtle.digest('SHA-256', file.arrayBuffer())` dans `useFileFingerprint`.
- Pre-flight : `GET /me/documents/by-fingerprint?sha256=<hex>` → 200 OK avec le document existant ou 404.
- Recalcul serveur : pendant l'upload (stream) ; en cas d'écart entre empreinte annoncée et empreinte calculée, le serveur **ne rejette pas** mais persiste l'empreinte serveur (l'empreinte client est purement indicative pour le pre-flight).

## 8. Compatibilité ascendante

- Documents F22 antérieurs : `content_sha256 IS NULL`. Une migration paresseuse re-calcule l'empreinte au prochain upload identique (les pré-existants ne participent pas au pre-flight tant qu'ils n'ont pas d'empreinte).
- Documents F12 (`document_projet`) : restent affichés dans la grille projet via union ; non éligibles au M:N (un document `document_projet` reste lié à 1 projet).
