# Contract — Hook post-mutation `update_entity_memory`

## Localisation

`backend/app/agent/memory/entity_memory.py` (NEW). Enregistre un hook auprès du dispatcher F55 (`app.agent.dispatcher`).

## Signature

```python
# app/agent/memory/entity_memory.py

async def update_entity_memory(
    account_id: UUID,
    entity_type: str,           # 'Entreprise' | 'Projet' | 'Candidature' | 'Indicateur'
    entity_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Rafraîchit (ou crée, ou supprime) l'entrée agent_entity_memory pour cette entité.

    Cas d'usage :
      - Mutation succeeded (UPSERT entity_memory).
      - Mutation DELETE (purge entity_memory si l'entité business est supprimée).

    Implémentation :
      1. Vérifie si l'entité business existe encore (SELECT 1 FROM <table> WHERE id = :entity_id AND account_id = :account_id).
         - Si NOT EXISTS: DELETE FROM agent_entity_memory WHERE (account_id, entity_type, entity_id) → return.
      2. Charge :
           - Le summary actuel (si exists)
           - Les 5 derniers chat_message du compte mentionnant cette entity_id (entity_refs JSONB contains)
           - L'état DB courant de l'entité (clés sourcées : secteur, effectif, score, etc.)
      3. LLM call (minimax-m2.7) avec prompt système strict :
           "Tu es un assistant qui rédige un fait stable sur cette entité (max 800 tokens).
            Reste factuel, cite les source_id, jamais d'anecdote personnelle.
            Format : 5-15 bullet points en français."
      4. UPSERT agent_entity_memory ON CONFLICT (account_id, entity_type, entity_id)
            DO UPDATE SET summary=:new_summary, sources_used=:sources, last_updated_at=now(), version=version+1.
      5. Write audit_log entry.
    """
```

## Hook enregistrement

```python
# app/agent/memory/__init__.py (NEW)
from app.agent.dispatcher import register_post_mutation_hook
from app.agent.memory.entity_memory import update_entity_memory


def _hook(ctx: MutationCtx) -> None:
    """Sync wrapper enqueuing BackgroundTask."""
    if ctx.status == "ok" and ctx.entity_type and ctx.entity_id:
        ctx.background_tasks.add_task(
            update_entity_memory,
            account_id=ctx.account_id,
            entity_type=ctx.entity_type,
            entity_id=ctx.entity_id,
            db=ctx.db,  # nouveau session, async wrapper interne
        )


register_post_mutation_hook(_hook)
```

## Comportement async

- `BackgroundTasks.add_task` est exécuté APRÈS la réponse HTTP du tour (FastAPI native).
- L'utilisateur ne paye pas la latence LLM du summary (cohérent NFR-002).
- En cas d'erreur dans le hook (LLM down, DB error), la mutation business reste valide ; le hook log warning, retry au prochain trigger.

## Test cases

| ID | Given | When | Then |
|---|---|---|---|
| EM-001 | Entreprise existante, pas d'entity_memory | dispatcher exécute update_company_profile, hook enqueué, BackgroundTask exécutée | nouvelle ligne agent_entity_memory créée, version=1, audit_log écrit |
| EM-002 | Entreprise + entity_memory existants | mutation update_company_profile | summary remplacé, version++ |
| EM-003 | Projet supprimé (delete_project) | dispatcher exécute, hook enqueué | DELETE FROM agent_entity_memory WHERE (account_id, 'Projet', :id) |
| EM-004 | Cross-tenant : compte A trigger mutation sur entité X qui appartient à compte B | hook execution avec account_id=A | RLS (current_setting=A) ne trouve pas l'entité B → DELETE entity_memory inchangée + log warning |
| EM-005 | LLM down pendant update_entity_memory | hook execution | log warning, retry au prochain trigger, mutation business intacte |
| EM-006 | 30 s après update_company_profile(secteur="C10.71") | poll agent_entity_memory | summary mentionne le nouveau secteur (SC-006) |

## Privacy / sécurité

- Le prompt système restreint à des faits sourcés (`sources_used` JSONB est rempli).
- Pas de PII free-form (pas de noms, anecdotes) — eval golden veille à ce que les summaries ne contiennent pas de données sensibles non sourcées.
- RLS appliqué : la lookup business utilise le `account_id` GUC.

## Performance

- update_entity_memory s'exécute en background, pas dans le critical path utilisateur.
- p95 < 5 s (1 LLM call avec contexte ≤ 2K tokens).
- Si débordement (file BackgroundTasks > 100), log warning et skip (post-MVP : queue persistante).
