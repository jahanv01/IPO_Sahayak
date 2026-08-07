"""Given a question, find the best-matching DRHP chunks for one company.

Two-stage retrieval: pgvector's cosine search pulls a wider candidate set cheaply, then
a cross-encoder re-ranks that small set for better relevance ordering before it's sent
to the model — better input, less work for the model to sift through.
"""

from __future__ import annotations

import psycopg

from app import db
from app.embeddings import embed_query
from app.reranker import rerank

FETCH_K = 10
TOP_K = 5


def retrieve(
    conn: psycopg.Connection,
    company: str,
    question: str,
    fetch_k: int = FETCH_K,
    top_k: int = TOP_K,
) -> list[db.RetrievedChunk]:
    query_embedding = embed_query(question)
    candidates = db.fetch_candidates(conn, company, query_embedding, fetch_k)
    if not candidates:
        return []

    order = rerank(question, [c.content for c in candidates], top_k)
    return [candidates[i] for i in order]
