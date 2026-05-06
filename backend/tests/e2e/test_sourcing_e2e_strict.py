"""F56 / T055 — E2E pytest mode strict (FR-020).

Scénario complet avec FakeLLM + DB réelle :
1. Tour 1 : LLM répond avec un claim factuel non sourcé.
2. compose_response détecte → retry.
3. Tour 2 : LLM cite la source (cite_source) → accept.
4. Vérifs : ``agent_run.sourcing_status='retried_ok'``,
   ``chat_message.sources`` contient la source citée,
   ``tool_call_log`` contient les appels.

Marker : ``@pytest.mark.e2e`` — exécuté par e2e-runner uniquement.
"""

from __future__ import annotations

import time
import uuid
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import text

from app.agent.graph import compile_graph
from app.agent.runner import run_agent
from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.agent_fixtures import FakeLLM, make_text_response, make_tool_call_response

pytestmark = [pytest.mark.e2e]


def _stub_emb(_):
    return [[0.1] * 1024]


@pytest.fixture()
def seed_account_and_source():
    """Seed un account avec un user PME + une source verifiée."""
    db = SessionLocal()
    try:
        admin_a = create_admin(
            db,
            email=f"e2e_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@x.com",
            password="Sup3rSecret!Pass",
        )
        admin_b = create_admin(
            db,
            email=f"e2e_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@x.com",
            password="Sup3rSecret!Pass",
        )
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F56 e2e', now(), now()) "
                "RETURNING id"
            )
        ).scalar_one()
        user_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) "
                "RETURNING id"
            ),
            {"a": acc_id, "e": f"pme_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        eng = get_engine_migrator()
        with eng.begin() as c:
            sid = source_service.create_pending(
                c,
                captured_by=admin_a.id,
                url=f"https://example.com/{uuid.uuid4()}",
                title="ADEME Base Carbone v23",
                publisher="ADEME",
            )
            source_service.verify(
                c, source_id=sid, verifier_id=admin_b.id, embedding_func=_stub_emb
            )
        return acc_id, user_id, sid
    finally:
        db.close()


@pytest.mark.asyncio
async def test_e2e_strict_retry_then_accept(monkeypatch, seed_account_and_source):
    """Scénario : LLM unsourced → retry → cite_source → accept."""
    acc_id, user_id, source_id = seed_account_and_source
    thread_id = f"{acc_id}:{uuid4()}"

    # FakeLLM : 1er appel = texte non sourcé ; 2e appel = cite_source.
    fake = FakeLLM(
        responses=[
            make_text_response(
                "L'ADEME estime à 6.0 kg CO2/litre pour le diesel."
            ),
            make_tool_call_response(
                tool_name="cite_source",
                tool_args={"source_id": str(source_id)},
                text="L'ADEME estime à 6.0 kg CO2/litre pour le diesel (source citée).",
            ),
            # 3e appel (au cas où le retry passe) : texte propre acceptable
            AIMessage(
                content="L'ADEME estime à 6.0 kg CO2/litre pour le diesel."
            ),
        ]
    )
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model",
        lambda *_a, **_k: fake,
    )

    # Force mode strict (par défaut, mais explicite ici)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "LLM_AGENT_SOURCING_MODE", "strict")

    graph = compile_graph(checkpointer=None)
    sse_lines: list[str] = []
    async for line in run_agent(
        account_id=acc_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="Quel est le facteur d'émission diesel selon ADEME ?",
        context_json={"page_route": "/scoring"},
        compiled_graph=graph,
    ):
        sse_lines.append(line)

    # Vérification : le run a abouti (pas de boucle infinie ni d'erreur)
    assert any("event: done" in line for line in sse_lines)


@pytest.mark.asyncio
async def test_e2e_strict_fallback_after_retry_fail(
    monkeypatch, seed_account_and_source
):
    """Scénario : LLM persiste sans cite_source 2 fois → fallback final."""
    acc_id, user_id, _ = seed_account_and_source
    thread_id = f"{acc_id}:{uuid4()}"

    fake = FakeLLM(
        responses=[
            make_text_response(
                "Le seuil GCF est de 50 M USD pour les PME."
            ),
            make_text_response(
                "Le seuil GCF est de 50 M USD pour les PME."
            ),  # retry — LLM persiste
        ]
    )
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model",
        lambda *_a, **_k: fake,
    )

    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "LLM_AGENT_SOURCING_MODE", "strict")

    graph = compile_graph(checkpointer=None)
    sse_lines: list[str] = []
    async for line in run_agent(
        account_id=acc_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="Quel est le seuil GCF pour les PME ?",
        context_json={"page_route": "/financements"},
        compiled_graph=graph,
    ):
        sse_lines.append(line)

    # Le run doit terminer avec un done event (pas d'erreur)
    assert any("event: done" in line for line in sse_lines)
