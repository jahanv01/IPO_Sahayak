"""Unit tests for app/retrieval.py's embed -> fetch -> rerank orchestration.

Embedding, the DB, and the reranker are all mocked out — this only tests that retrieve()
wires them together correctly, not fastembed's models or a real database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.db import RetrievedChunk
from app.retrieval import retrieve


def make_chunk(chunk_id: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        company="Acme Ltd",
        section="Risk Factors",
        page_number=1,
        content=content,
        distance=0.1,
    )


@patch("app.retrieval.rerank")
@patch("app.retrieval.db")
@patch("app.retrieval.embed_query")
def test_retrieve_reranks_candidates_into_final_order(mock_embed_query, mock_db, mock_rerank):
    mock_embed_query.return_value = [0.1, 0.2, 0.3]
    candidates = [make_chunk(1, "first"), make_chunk(2, "second"), make_chunk(3, "third")]
    mock_db.fetch_candidates.return_value = candidates
    mock_rerank.return_value = [2, 0]

    conn = MagicMock()
    result = retrieve(conn, "Acme", "What are the risks?", fetch_k=3, top_k=2)

    assert result == [candidates[2], candidates[0]]
    mock_embed_query.assert_called_once_with("What are the risks?")
    mock_db.fetch_candidates.assert_called_once_with(conn, "Acme", [0.1, 0.2, 0.3], 3)
    mock_rerank.assert_called_once_with(
        "What are the risks?", ["first", "second", "third"], 2
    )


@patch("app.retrieval.rerank")
@patch("app.retrieval.db")
@patch("app.retrieval.embed_query")
def test_retrieve_returns_empty_without_calling_rerank_when_no_candidates(
    mock_embed_query, mock_db, mock_rerank
):
    mock_embed_query.return_value = [0.1, 0.2, 0.3]
    mock_db.fetch_candidates.return_value = []

    result = retrieve(MagicMock(), "Acme", "What are the risks?")

    assert result == []
    mock_rerank.assert_not_called()
