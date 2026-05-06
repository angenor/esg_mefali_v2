# Contract: Ops Alerting (FR-022, FR-023)

## Module `app/utils/ops_alerting.py`

```python
async def send_alert(
    severity: Literal['info', 'warning', 'critical'],
    title: str,
    message: str,
    fields: dict[str, Any] | None = None,
) -> None:
    """Envoie une alerte ops via Slack webhook + log structuré.

    Behavior:
    - Si OPS_SLACK_WEBHOOK_URL configuré : POST httpx async (timeout 5s, 1 retry).
    - Si non configuré : log seulement (level WARN/ERROR selon severity).
    - Coalescence : max 1 alerte du même `title` par 5 min (cache in-memory).
    - Ne lève JAMAIS d'exception qui bloque le flux principal.
    """
    ...
```

## Slack payload (Block Kit)

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🚨 [CRITICAL] Circuit breaker LLM ouvert"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "Le service LLM OpenRouter retourne des erreurs HTTP consécutives. Fallback texte activé pour 5 minutes."}
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Service:*\nllm_openrouter"},
        {"type": "mrkdwn", "text": "*Erreurs:*\n3 en 60s"},
        {"type": "mrkdwn", "text": "*Ouverture:*\n2026-05-06T22:30:00Z"},
        {"type": "mrkdwn", "text": "*Récup auto:*\n2026-05-06T22:35:00Z"}
      ]
    }
  ],
  "attachments": [
    {"color": "#dc3545"}
  ]
}
```

| Severity | Couleur | Préfixe titre |
|---|---|---|
| `info` | `#36a64f` | `ℹ️ [INFO]` |
| `warning` | `#ffc107` | `⚠️ [WARN]` |
| `critical` | `#dc3545` | `🚨 [CRITICAL]` |

## Triggers (FR-023)

| Événement | Severity | Title |
|---|---|---|
| Circuit breaker LLM s'ouvre | `critical` | `Circuit breaker LLM ouvert` |
| Erreur rate > 10% sur 30 min | `warning` | `Taux erreur agent élevé` |
| Compliance sourcing < 70% sur 1 jour | `warning` | `Compliance sourcing dégradée` |
| Account quota tokens atteint | `info` | `Quota tokens atteint pour compte X` |

## Coalescence

```python
_LAST_ALERT_BY_TITLE: dict[str, datetime] = {}
COALESCENCE_WINDOW_S = 300  # 5 min

def _should_send(title: str) -> bool:
    last = _LAST_ALERT_BY_TITLE.get(title)
    now = datetime.now(UTC)
    if last is None or (now - last).total_seconds() > COALESCENCE_WINDOW_S:
        _LAST_ALERT_BY_TITLE[title] = now
        return True
    return False
```

## Tests intégration associés

- `tests/integration/utils/test_ops_alerting.py` :
  - Mock httpx, vérifier payload formé correctement.
  - Vérifier no-op quand env var absente (pas d'erreur).
  - Vérifier coalescence : 2 alertes même title en < 5 min → 1 seul POST.
  - Vérifier timeout/retry sans bloquer le flux principal.
