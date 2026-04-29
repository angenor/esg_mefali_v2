# F14 — Manual tests checklist

À jouer manuellement après implémentation effective (Phase B partielle livrée).

## MVP livré (2026-04-29) — tests manuels exécutables maintenant

### TM-A1 — Registry des 5 tools fictifs

```bash
cd backend && source .venv/bin/activate
python -c "
from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.tool_registry import TOOL_REGISTRY
register_fixture_tools()
for name, td in TOOL_REGISTRY.items():
    print(name, '→', td.description)
"
```
**Attendu** : 5 tools listés (`show_summary_card`, `ask_qcu`, `ask_yes_no`, `update_demo_profile`, `search_demo_source`).

### TM-A2 — Validateur strict (extra fields refusés)

```bash
python -c "
from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.payload_validator import validate
register_fixture_tools()
ok, errs = validate('ask_yes_no', {'question':'OK ?', 'rogue':1})
print('ok=', ok, 'errors=', len(errs))
"
```
**Attendu** : `ok=False`, ≥ 1 erreur.

### TM-A3 — Retry policy

```bash
python -c "
from app.orchestrator.retry_policy import decide, MAX_RETRIES
print(decide(0), decide(1), decide(MAX_RETRIES))
"
```
**Attendu** : `retry retry fallback`.

### TM-A4 — Classifier rule-based (7 intentions)

```bash
python -c "
from app.orchestrator.intent_classifier import classify
for m in ['Ajoute un projet','Compare ESG','Aide','Oui','Va à profil','Mon profil','blah']:
    print(repr(m), '→', classify(m))
"
```
**Attendu** : `mutation analyse aide question_fermee navigation profilage autre`.

### TM-A5 — Tool selector + whitelist Skills

```bash
python -c "
from app.orchestrator.fixtures_tools import register_fixture_tools
from app.orchestrator.tool_selector import select
register_fixture_tools()
print(select('mutation'))
print(select('mutation', skill_whitelist=('ask_qcu',)))
"
```
**Attendu** : set ≤ 10, whitelist filtre à `['ask_qcu']`.

### TM-A6 — Couverture & lint

```bash
pytest -q --cov=app/orchestrator --cov-report=term-missing tests/orchestrator/
ruff check app/orchestrator tests/orchestrator
```
**Attendu** : 39 passed, ≥ 80 % (effectif 98.31 %), `All checks passed!`.

---

## Reportés [DEFERRED] — section originale Phase B planifiée

## Pré-requis

- Postgres dockerisé tournant.
- `alembic upgrade head` exécuté (table `tool_call_log` présente).
- `LLM_STUB=1` ou `LLM_API_KEY=...` configuré.
- `F14_PIPELINE_ENABLED=1`.
- Backend en cours d'exécution (`uvicorn app.main:app --reload --port 8000`).
- Utilisatrice PME authentifiée.

## Tests SSE bout-en-bout

1. **Tour simple — mode stub** : `curl -N -H "Accept: text/event-stream" -d '{"content":"ajoute un projet"}' /chat/messages` → événements `thinking(classifying)` → `selecting_tools` → `calling_llm` → `validating` → `tool_call_started` → `tool_call_completed` → `text_delta` → `message_done`.
2. **Retry réussi** : LLM mocké invalide×1 puis valide → `thinking(retrying)` apparaît, `tool_call_completed.retries == 1`.
3. **Fallback texte (3 invalides)** : LLM mocké toujours invalide → `text_delta` = "Je n'arrive pas à formaliser cette action — peux-tu reformuler ?", aucun `tool_call_started`, ligne `tool_call_log.status='validation_error'` `retries=2`.
4. **F13 inchangé si désactivé** : `F14_PIPELINE_ENABLED=0` → aucun `thinking`/`tool_call_*`.

## Tests admin endpoint

5. **Lecture logs admin** : `GET /admin/tool-call-logs?thread_id=<UUID>&status=ok&limit=10` → 200 + JSON paginé.
6. **Isolation tenant** : compte A insère 1 log → compte B (admin tenant B) ne voit rien.
7. **Non-admin → 403** : utilisateur PME standard sur cet endpoint → 403.

## Sérialisation

8. **Concurrents même fil** : 2 curl simultanés même `thread_id` → ordre `created_at` strict (T2 ≥ T1).
9. **Concurrents fils distincts** : 2 curl sur threads différents → exécution parallèle.

## Budget tokens

10. **System prompt > 4 000 tokens** : forcer 10 tools verbeux → log warning `system prompt over budget` + prompt tronqué.

## Cache classifier

11. **Pas de reclassification** : 2 messages identiques même fil < 10 min → un seul appel LLM léger.

## Append-only

12. **Convention append-only** : tester en code que `repository.update(ToolCallLog)` n'existe pas. La verrouillage DB par trigger est out of MVP.

## Régression F13

13. `pytest backend/tests/chat/ -q` (avec `F14_PIPELINE_ENABLED=0`) doit rester vert.
