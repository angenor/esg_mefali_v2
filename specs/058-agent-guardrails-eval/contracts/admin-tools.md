# Contract: Admin Tools Kill-Switch (FR-007 — US4)

## POST `/admin/agent/tools/{tool_name}/disable`

**Auth**: `require_admin` (Bearer JWT, role = `Admin`).
**Path params**: `tool_name` — VARCHAR(100), nom canonique du tool.

**Request body**:
```json
{
  "reason": "consume too many tokens, suspected loop"
}
```
- `reason` : str, 5–500 caractères, requis.

**Response 200**:
```json
{
  "tool_name": "generate_dossier",
  "enabled": false,
  "disabled_at": "2026-05-06T21:30:00Z",
  "disabled_by": "uuid-admin",
  "reason": "consume too many tokens, suspected loop"
}
```

**Response 404** (non-admin ou tool inconnu — convention P2).

**Side effects** :
- INSERT/UPDATE dans `agent_tool_status`.
- INSERT dans `audit_log` (`source_of_change = 'admin'`).
- Cache TTL 30s côté `select_tools` invalidé au prochain expire (au plus 30s plus tard).

## POST `/admin/agent/tools/{tool_name}/enable`

**Auth**: `require_admin`.

**Request body**: vide.

**Response 200**:
```json
{
  "tool_name": "generate_dossier",
  "enabled": true,
  "disabled_at": null,
  "disabled_by": null,
  "reason": null
}
```

**Side effects** : UPDATE `agent_tool_status SET enabled=true, disabled_at=NULL` ; audit log ; cache invalidé.

## GET `/admin/agent/tools`

**Auth**: `require_admin`.

**Query params** : aucun.

**Response 200**:
```json
{
  "tools": [
    {
      "tool_name": "create_project",
      "enabled": true,
      "disabled_at": null,
      "disabled_by": null,
      "reason": null
    },
    {
      "tool_name": "generate_dossier",
      "enabled": false,
      "disabled_at": "2026-05-06T21:30:00Z",
      "disabled_by": "uuid-admin",
      "reason": "consume too many tokens"
    }
    // ... tous les tools du registry, hydratés avec status DB ou défaut enabled=true
  ],
  "count": 17
}
```

**Note** : la liste fusionne le registry des tools (source de vérité noms) avec
les rangs de `agent_tool_status` (état). Tools sans rangé sont retournés avec
`enabled = true` (défaut).

## Pydantic schemas (FastAPI)

```python
class DisableToolRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Field(min_length=5, max_length=500)

class ToolStatusResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool_name: str
    enabled: bool
    disabled_at: datetime | None
    disabled_by: UUID | None
    reason: str | None

class ToolStatusListResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tools: list[ToolStatusResponse]
    count: int
```

## Tests E2E associés

- `tests/e2e/test_agent_e2e_kill_switch.py` :
  - Scenario: admin disable `generate_dossier` → 5 PME tours en moins d'1 min → tool absent du `available_tools` retourné par `select_tools` node → admin enable → tool revient.
  - Vérifie aussi : non-admin reçoit 404 sur les 3 endpoints.
