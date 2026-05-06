# Contract: Guardrails Python API (Internal)

Modules sous `backend/app/agent/guardrails/`. Toutes les fonctions sont **pures**
(pas d'effet de bord I/O sauf logging) et **synchrones** sauf indication contraire.

## anti_injection.py — FR-001, FR-002

```python
def detect(message: str) -> InjectionFinding | None:
    """Détecte un pattern d'injection dans le message utilisateur.

    Returns None si aucun pattern matché, sinon un InjectionFinding
    décrivant le motif, sa catégorie et sa sévérité.

    Latence cible : < 5 ms p99 (regex compilées au démarrage).

    use when : appelé par node `route` avant build_context.
    don't use when : sur les messages système ou les tool outputs (déjà trustés).
    """
    ...

def wrap_user_message(message: str, finding: InjectionFinding | None) -> str:
    """Encadre le message dans une enveloppe explicite si une injection est détectée.

    Si finding est None : retourne message inchangé.
    Sinon : retourne `[USER MESSAGE — UTILISATEUR PEUT TENTER UNE INJECTION...]\n{message}\n[/USER MESSAGE]`.

    Ne mute jamais le message original (immuable).
    """
    ...
```

## pii_detector.py — FR-003, FR-004

```python
@dataclass(frozen=True)
class PiiPattern:
    name: Literal['mobile_money_ci', 'mobile_money_sn', 'mobile_money_bj',
                  'mobile_money_tg', 'mobile_money_bf',
                  'cni_uemoa', 'iban', 'card_luhn', 'email_personal']
    regex: re.Pattern
    mask_template: str  # ex. "+225 ** ** ** ** **"
    requires_luhn_check: bool = False

DEFAULT_PII_PATTERNS: list[PiiPattern] = [...]  # défini en constante module

def mask_pii(text: str, patterns: list[PiiPattern] = DEFAULT_PII_PATTERNS) -> tuple[str, int]:
    """Retourne une COPIE masquée du texte + le nombre de PII masquées.

    Ne mute jamais le texte original.
    Pour `card_luhn`, vérifie la validité Luhn avant masquage (évite faux positifs sur chiffres aléatoires).
    Pour `email_personal`, applique heuristique : domaine grand public connu (gmail/yahoo/hotmail/outlook).

    Returns:
        (masked_text, count) où count = nombre d'occurrences masquées.

    Latence cible : < 10 ms p99 sur texte 1 KB.
    """
    ...
```

## lang_check.py — FR-005, FR-006

```python
def detect_language(text: str) -> str:
    """Retourne ISO 639-1 ('fr', 'en', 'es', 'ar', 'wo', 'bm', 'unknown').

    Utilise `langdetect`. Fallback 'unknown' si texte < 30 chars (trop court).

    Latence cible : < 5 ms p99.
    """
    ...

def needs_french_retry(detected_lang: str, user_lang_pref: str, offer_accepted_langs: list[str] | None) -> bool:
    """Décide si un retry FR doit être déclenché.

    True si :
    - user_lang_pref == 'fr'
    - detected_lang in {'en', 'es', 'ar'}
    - offer_accepted_langs ne contient pas detected_lang (sinon politique offre prime)

    False sinon.
    """
    ...
```

## circuit_breaker.py — FR-010, FR-011

```python
class CircuitBreaker:
    """In-memory per-worker circuit breaker.

    State machine: closed → open (3 errors in 60s) → half_open (after 5 min) → closed (1 success) | open.
    """
    def __init__(self, error_threshold: int = 3, time_window_s: int = 60, open_duration_s: int = 300):
        ...

    def is_open(self, service: str) -> bool:
        """Returns True si le circuit est ouvert (ou half_open en cours de test)."""
        ...

    def record_success(self, service: str) -> None:
        """Notifie un succès. Ferme le circuit s'il était half_open."""
        ...

    def record_error(self, service: str, status_code: int | None = None) -> None:
        """Notifie une erreur HTTP. Ouvre le circuit si seuil atteint dans la fenêtre."""
        ...

# Singleton module-level
LLM_CIRCUIT_BREAKER = CircuitBreaker()

FALLBACK_MESSAGE = "Le service IA est temporairement indisponible — merci de réessayer dans quelques minutes."
```

## budget.py — FR-013, FR-014, FR-015

```python
def check_budget(
    db: Session,
    account_id: UUID,
    requested_tokens: int,
    flow: Literal['conversation', 'ocr_analysis']
) -> BudgetResult:
    """Vérifie si une requête peut consommer requested_tokens.

    - Lit account.daily_*_quota.
    - Calcule remaining via agrégation SQL `agent_run_step` (cache 60s in-memory).
    - Vérifie aussi limite par tour : requested_tokens <= 8000.

    Returns BudgetResult(allowed=True, reason=None) ou (allowed=False, reason=FR text).
    """
    ...

def cap_completion_tokens(requested: int, max_per_turn: int = 8000) -> int:
    """Renvoie min(requested, max_per_turn). Utilisé pour le paramètre max_tokens de l'appel LLM."""
    ...
```

## tool_status.py — FR-007, FR-008, FR-009

```python
def get_disabled_tools(db: Session) -> set[str]:
    """Retourne l'ensemble des tool_name disabled actuellement.

    Cache TTL 30s in-memory pour éviter une query par tour.
    """
    ...

def disable_tool(db: Session, tool_name: str, admin_user_id: UUID, reason: str) -> AgentToolStatus:
    """Marque un tool comme disabled. Journalise dans audit_log. Invalide le cache."""
    ...

def enable_tool(db: Session, tool_name: str, admin_user_id: UUID) -> AgentToolStatus:
    """Réactive un tool. Journalise dans audit_log. Invalide le cache."""
    ...

def list_all_tools_status(db: Session, registry: ToolRegistry) -> list[AgentToolStatus]:
    """Fusionne le registry (tous les tool_name connus) avec la table DB. Hydrate manquants à enabled=true."""
    ...
```

## loop_detector.py — FR-016

```python
def detect_loop(
    history: list[ToolCall],
    new_call: ToolCall,
    max_consecutive_identical: int = 3,
    max_per_turn: int = 10
) -> LoopDetectionResult:
    """Détecte une boucle d'agent.

    Boucle = même tool_name + même hash(args) répété max_consecutive_identical fois.
    Ou : len(history) + 1 > max_per_turn → forcer compose_response.
    """
    ...

def args_hash(args: dict) -> str:
    """SHA256(json.dumps(args, sort_keys=True, default=str))."""
    ...
```

## Garanties transversales

- **Immutabilité** : aucune fonction ne modifie ses paramètres ; toutes retournent
  des copies/nouveaux objets.
- **Latence** : NFR-001 → la composition (`detect` + `mask_pii` + `detect_language`)
  doit rester < 30 ms p95 mesurée par benchmark dans `tests/perf/`.
- **Coverage** : NFR-007 → ≥ 85 % sur le sous-package, gate via `pytest --cov-fail-under=85`.
- **Pure functions où possible** : `detect`, `mask_pii`, `detect_language`,
  `args_hash`, `cap_completion_tokens`, `wrap_user_message`. Les fonctions à état
  (`CircuitBreaker`, cache `tool_status`) sont encapsulées.
