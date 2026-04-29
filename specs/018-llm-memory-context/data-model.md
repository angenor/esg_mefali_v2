# Data Model — F18 Mémoire Contextuelle LLM

**Date**: 2026-04-29

F18 n'introduit **aucune nouvelle table**. Elle consomme les tables existantes (F11 entreprise, F12 projets, F13 chat_thread / chat_message) et ajoute un **index vectoriel** sur `chat_message.embedding`.

## Entités (toutes existantes)

### chat_message (F13, table existante)

Champs utilisés par F18 :

| Colonne | Type | Notes F18 |
|---------|------|-----------|
| `id` | UUID PK | identifiant message |
| `account_id` | UUID NOT NULL | clé RLS, indispensable pour `recall_history` |
| `thread_id` | UUID NOT NULL | scope de la recherche `recall_history` |
| `role` | TEXT (`user` / `assistant` / `system`) | les rôles `system` sont exclus de la fenêtre récente |
| `content` | TEXT | texte du message (utilisé pour fenêtre + embedding) |
| `payload_json` | JSONB NULL | si présent, label/title extrait pour embedding |
| `created_at` | TIMESTAMPTZ | tri DESC pour fenêtre récente |
| `embedding` | VECTOR(1024) NULL | populé par BackgroundTask F13 |
| `deleted_at` | TIMESTAMPTZ NULL | les messages supprimés sont exclus |

**Index ajouté par F18 (migration `0013_f18_chat_message_embedding_index.py`) :**

```sql
CREATE INDEX IF NOT EXISTS idx_chat_message_embedding
  ON chat_message USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

(Note : pgvector ne supporte pas les WHERE prédicats sur les index ivfflat — l'exclusion `embedding IS NOT NULL` est garantie côté query par `WHERE embedding IS NOT NULL`.)

### chat_thread (F13, table existante)

Champs lus : `id`, `account_id`, `user_id`, `title`. Aucun changement.

### entreprise (F11, table existante)

Lecture en début de tour via le repository F11. Aucun changement de schéma.
Whitelist des champs exposés au LLM (FR-002, FR-014) — voir compactor.

### projet (F12, table existante)

Lecture en début de tour via le repository F12. Filtré sur statut actif. Aucun changement de schéma.
Whitelist des champs exposés au LLM (FR-003) — voir compactor.

## Entités éphémères (in-memory, non persistées)

### `ContextBundle` (`app/chat/memory/context_builder.py`)

```python
@dataclass(frozen=True)
class ContextBundle:
    profile_section: str | None       # markdown "# Profil entreprise" ou None si vide
    projects_section: str | None      # markdown "# Projets actifs" ou None si vide
    recent_messages: tuple[ChatMessageView, ...]  # 5 à 15 entrées, ordre chronologique
    estimated_tokens: int             # n_chars / 4 sur le rendu final
    expose_recall_history: bool       # True si total_messages_in_thread > 15

    def to_system_message(self) -> str:
        """Concatène les sections non-nulles + 'Conversation récente'."""
```

### `ChatMessageView`

```python
@dataclass(frozen=True)
class ChatMessageView:
    role: str                # "user" | "assistant"
    content: str             # texte affiché (tronqué si > 4 000 chars avec marker [...tronqué...])
    payload_label: str | None  # extrait du payload_json si présent
    created_at: datetime
```

### `RecallHit` (résultat du tool `recall_history`)

```python
class RecallHit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    thread_id: UUID
    role: Literal["user", "assistant"]
    snippet: str            # max 240 chars
    created_at: datetime
    similarity: float       # cosinus 0..1
```

## Whitelists champs (compactors.py)

### Profil entreprise (FR-002, FR-014)

Champs autorisés pour `compact_profile()` :
- `raison_sociale` (str)
- `forme_juridique` (str | None)
- `secteur_activite` (str | None)
- `pays` (str | None)
- `effectif_total` (int | None)
- `chiffre_affaires` (Money | None) — typé `{amount: Decimal, currency: str}`
- `description_activite` (str | None) — tronqué à 200 chars
- `indicateurs_esg_synthetiques` (dict | None) — sous-set d'indicateurs déjà calculés F11

Champs **exclus explicitement** (deny by default) :
- tokens, password, hash, jwt, refresh_token
- ids techniques internes (clés étrangères, version, audit metadata)
- email / téléphone du dirigeant (PII non nécessaire au scoring conversationnel)

### Projet (FR-003)

Champs autorisés pour `compact_projets()` :
- `id` (UUID — opaque, utile pour référence)
- `nom` (str)
- `statut` (str)
- `secteur` (str | None)
- `pays` (str | None)
- `montant_total` (Money | None)
- `description` (str | None) — tronquée par compaction (200/100/50)
- `date_debut`, `date_fin_prevue` (date | None)

Filtré sur `statut NOT IN ('cloture', 'annule')`. Limité à 10.
