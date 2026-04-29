# Contrats LLM Tools (function-calling OpenRouter)

Tous les schémas Pydantic v2 utilisent `model_config = ConfigDict(extra='forbid')` (P9).

## `cite_source`

**Use when** : tu vas affirmer un chiffre, seuil, critère, formule, facteur d'émission, document requis ou citer un référentiel ; tu dois prouver la source.
**Don't use when** : tu écris un texte générique sans donnée chiffrée ESG/financière ni référence normative.

```python
class CiteSourceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: UUID

class CiteSourceOutput(BaseModel):  # = Source verifiée ou ToolError
    model_config = ConfigDict(extra='forbid')
    source: Source | None = None
    error: Literal['not_verified','not_found'] | None = None
```

Exemple positif : `cite_source(source_id="b3...e1")` → renvoie la Source GCF Investment Criteria v3.
Exemple négatif : `cite_source` appelé pour une phrase d'introduction sans aucun chiffre ni norme.

## `search_source`

**Use when** : tu ne connais pas l'`id` d'une source ; tu cherches la meilleure source `verified` qui couvre une notion donnée.
**Don't use when** : tu connais déjà l'`id` (utilise `cite_source`).

```python
class SearchSourceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=256)
    publisher: str | None = Field(default=None, max_length=100)
    k: int = Field(default=10, ge=1, le=50)

class SearchSourceOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[Source]
```

Exemple positif : `search_source(query="critères GCF investissement adaptation", publisher="GCF", k=5)`.
Exemple négatif : `search_source(query="bonjour")` — requête sans valeur.

## `flag_unsourced`

**Use when** : aucune source `verified` ne couvre une affirmation que l'utilisateur réclame ; tu choisis de répondre "Je ne dispose pas de source vérifiée".
**Don't use when** : tu n'as simplement pas cherché.

```python
class FlagUnsourcedInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim: str = Field(min_length=1, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)

class FlagUnsourcedOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
```

Exemple positif : `flag_unsourced(claim="seuil GCF intensité carbone secteur agriculture 2024", context={"intent":"score_gcf"})`.

## Format des `tool_calls` analysé par le middleware

Le middleware lit la sortie LLM au format OpenAI `chat.completions` et n'accepte qu'un `cite_source` matérialisé comme :

```json
{
  "tool_calls": [
    {"id":"call_x","type":"function","function":{"name":"cite_source","arguments":"{\"source_id\":\"<uuid>\"}"}}
  ]
}
```

Tout `cite_source` vers une source non `verified` ou inexistante est rejeté.
