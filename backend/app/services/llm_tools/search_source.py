"""F03 US2 — Tool ``search_source`` (full-text + vectoriel hybride).

Use when : tu ne connais pas l'``id`` d'une source ; tu cherches la meilleure
source ``verified`` qui couvre une notion donnée.

Don't use when : tu connais déjà l'``id`` (utilise ``cite_source``).

Stratégie hybride (R1) :
    score = 0.5 * rank_text + 0.5 * (1 - cos_distance)
Seules les sources ``verified`` sont renvoyées.
"""

from __future__ import annotations

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app import embeddings_client
from app.schemas.source import (
    SearchSourceInput,
    SearchSourceOutput,
    SourceRead,
)


def handle_search_source(
    db: Session,
    payload: SearchSourceInput,
    *,
    embedding_func=None,
) -> SearchSourceOutput:
    """Recherche hybride full-text + vectoriel sur sources ``verified``."""
    embedding_func = embedding_func or embeddings_client.embed
    try:
        emb = embedding_func([payload.query])[0]
    except Exception:  # noqa: BLE001
        # Fallback : full-text seul si embedding indisponible
        emb = None

    publisher_clause = ""
    params: dict = {"q": payload.query, "k": payload.k}
    if payload.publisher:
        publisher_clause = "AND publisher = :pub"
        params["pub"] = payload.publisher

    if emb is not None:
        sql = text(
            f"""
            SELECT id, url, title, publisher, version, date_publi, page, section,
                   captured_at, verified_at, verification_status, notes,
                   (
                     0.5 * ts_rank(tsv, plainto_tsquery('french', :q))
                     + 0.5 * (1 - (embedding <=> CAST(:emb AS vector(1024))))
                   ) AS score
            FROM source
            WHERE verification_status = 'verified'
              {publisher_clause}
              AND (tsv @@ plainto_tsquery('french', :q) OR embedding IS NOT NULL)
            ORDER BY score DESC
            LIMIT :k
            """
        ).bindparams(bindparam("emb", expanding=False))
        params["emb"] = emb
    else:
        sql = text(
            f"""
            SELECT id, url, title, publisher, version, date_publi, page, section,
                   captured_at, verified_at, verification_status, notes,
                   ts_rank(tsv, plainto_tsquery('french', :q)) AS score
            FROM source
            WHERE verification_status = 'verified'
              AND tsv @@ plainto_tsquery('french', :q)
              {publisher_clause}
            ORDER BY score DESC
            LIMIT :k
            """
        )

    rows = db.execute(sql, params).mappings().all()
    items = [SourceRead.model_validate({k: v for k, v in r.items() if k != "score"}) for r in rows]
    return SearchSourceOutput(items=items)
